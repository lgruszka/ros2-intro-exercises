"""Sterownik polityki chodu R1 bez ROS (W12): /lowstate -> cele przegubów dla /lowcmd.

Ten sam kod liczy cele w symulacji (r1_sim w trybie `lowcmd`) i na prawdziwym R1 (tryb debug Unitree),
więc między symulacją a robotem zmienia się tylko interfejs sieciowy. Budowa jak w oficjalnym kodzie
uruchomieniowym Unitree (unitree_rl_mjlab deploy/robots/r1): stany PASSIVE / FIXSTAND / WALK.

  PASSIVE   kp = 0, kd = 3 na wszystkich 27 slotach (tłumienie, jak State_Passive Unitree)
  FIXSTAND  liniowe przejście z bieżącej pozy do pozy domyślnej w 3 s, KP/KD jak FixStand Unitree
  WALK      polityka ONNX co 20 ms: cel = poza domyślna + skala * akcja, KP/KD z metadanych polityki

Pilot (lowstate.wireless_remote, układ ze strony R1 „Remote Control Data”): L2+B -> PASSIVE, L2+UP -> FIXSTAND,
R2+A -> WALK (z FIXSTAND). Uruchomienie na prawdziwym R1 WYŁĄCZNIE na szubienicy z robotem podwieszonym
i asekurowanym (W12).
"""
import math
import struct

import numpy as np

from r1_basics.policy_sim import SLOTS, quat_to_rpy

NUM_SLOTS = 27                      # sloty 0-26 jak w konfiguracji deploy/robots/r1 Unitree (27 wartości)
PASSIVE_KD = 3.0                    # State_Passive: kp 0, kd 3
# FixStand z deploy/robots/r1/config/config.yaml (kolejność slotów 0-26)
FIXSTAND_KP = [100, 100, 100, 150, 40, 40, 100, 100, 100, 150, 40, 40, 200, 200, 200,
               40, 40, 40, 40, 40, 100, 100, 40, 40, 40, 40, 40]
FIXSTAND_KD = [2, 2, 2, 4, 2, 2, 2, 2, 2, 4, 2, 2, 5, 5, 5,
               10, 10, 10, 10, 10, 4, 4, 10, 10, 10, 10, 10]
FIXSTAND_S = 3.0
PHASE_PERIOD = 0.6
STAND_THRESHOLD = 0.1
BAD_ORIENTATION_RAD = 1.0           # jak bad_orientation(env, 1.0) w State_RLBase Unitree -> PASSIVE

# bity przycisków (xKeySwitchUnion, uint16 little-endian w bajtach 2-3 wireless_remote)
BTN = {'R1': 0, 'L1': 1, 'start': 2, 'select': 3, 'R2': 4, 'L2': 5, 'F1': 6, 'F2': 7,
       'A': 8, 'B': 9, 'X': 10, 'Y': 11, 'up': 12, 'right': 13, 'down': 14, 'left': 15}


def remote_buttons(wireless_remote):
    """Zbiór wciśniętych przycisków z 40 bajtów lowstate.wireless_remote."""
    raw = bytes(bytearray(int(b) & 0xFF for b in wireless_remote[:4]))
    if len(raw) < 4:
        return set()
    value = struct.unpack_from('<H', raw, 2)[0]
    return {name for name, bit in BTN.items() if value & (1 << bit)}


def remote_bytes(buttons):
    """Odwrotność remote_buttons (do symulatora): 40 bajtów z ustawionymi bitami przycisków."""
    value = 0
    for name in buttons:
        value |= 1 << BTN[name]
    data = bytearray(40)
    struct.pack_into('<H', data, 2, value)
    return list(data)


def projected_gravity(w, x, y, z):
    """Wektor (0, 0, -1) w ramie miednicy (R^T g) z kwaternionu w, x, y, z."""
    # R^T * (0, 0, -1) = minus trzeci wiersz macierzy obrotu R (ciało -> świat)
    return np.array([-(2 * (x * z - w * y)), -(2 * (y * z + w * x)), -(1 - 2 * (x * x + y * y))])


def tilt(w, x, y, z):
    """Kąt odchylenia od pionu [rad]."""
    up_z = 1 - 2 * (x * x + y * y)
    return math.acos(max(-1.0, min(1.0, up_z)))


class R1PolicyController:
    def __init__(self, policy_path):
        import onnxruntime as ort
        self.sess = ort.InferenceSession(policy_path, providers=['CPUExecutionProvider'])
        self.inp = self.sess.get_inputs()[0].name
        meta = dict(self.sess.get_modelmeta().custom_metadata_map)
        fl = lambda s: [float(v) for v in s.split(',')]  # noqa: E731
        self.joint_names = meta['joint_names'].split(',')
        self.default = np.array(fl(meta['default_joint_pos']))
        scale = meta['action_scale']
        self.scale = np.array(fl(scale) if ',' in scale else [float(scale)] * len(self.joint_names))
        self.kp_walk = np.array(fl(meta['joint_stiffness']))
        self.kd_walk = np.array(fl(meta['joint_damping']))
        self.slots = np.array([SLOTS[n] for n in self.joint_names])
        self.step_dt = 0.02
        self.mode = 'PASSIVE'
        self.reset_policy()
        self.fix_t = 0.0
        self.fix_q0 = None

    def reset_policy(self):
        self.last_action = np.zeros(len(self.joint_names))
        self.steps = 0

    # ---- przejścia (zwracają komunikat do logu albo None) -----------------------------------------
    def request(self, mode, q_slots):
        if mode == self.mode:
            return None
        if mode == 'PASSIVE':
            self.mode = 'PASSIVE'
            return 'PASSIVE: kp 0, kd 3 (napęd miękki)'
        if mode == 'FIXSTAND':
            self.mode = 'FIXSTAND'
            self.fix_t = 0.0
            self.fix_q0 = np.array([q_slots[s] for s in range(NUM_SLOTS)])
            return f'FIXSTAND: przejście do pozy domyślnej w {FIXSTAND_S:.0f} s'
        if mode == 'WALK':
            if self.mode != 'FIXSTAND' or self.fix_t < FIXSTAND_S:
                return 'WALK odrzucone: najpierw FIXSTAND (pełne 3 s)'
            self.mode = 'WALK'
            self.reset_policy()
            return 'WALK: polityka steruje 24 przegubami co 20 ms'
        return f'nieznany tryb {mode}'

    def safety(self, quat):
        """PASSIVE przy przechyle > 1 rad (jak Unitree). Zwraca komunikat albo None."""
        if self.mode != 'PASSIVE' and tilt(*quat) > BAD_ORIENTATION_RAD:
            self.mode = 'PASSIVE'
            return f'przechył {math.degrees(tilt(*quat)):.0f} st. > {math.degrees(BAD_ORIENTATION_RAD):.0f} st.: PASSIVE'
        return None

    # ---- jeden krok sterownika -------------------------------------------------------------------
    def observation(self, gyro, quat, q24, dq24, cmd):
        cmd = np.asarray(cmd, dtype=np.float64)
        if np.linalg.norm(cmd) < STAND_THRESHOLD:
            phase = np.zeros(2)
        else:
            ph = (self.steps * self.step_dt) % PHASE_PERIOD / PHASE_PERIOD
            phase = np.array([math.sin(2 * math.pi * ph), math.cos(2 * math.pi * ph)])
        return np.concatenate([np.asarray(gyro, dtype=np.float64), projected_gravity(*quat), cmd, phase,
                               np.asarray(q24) - self.default, np.asarray(dq24), self.last_action]).astype(np.float32)

    def command(self, gyro, quat, q_slots, dq_slots, cmd, dt):
        """Zwraca (q, kp, kd) dla 27 slotów. q_slots/dq_slots: pomiary 35 (albo 27) slotów z /lowstate.
        Polityka liczona co step_dt (wołaj z tym okresem w trybie WALK)."""
        q = np.zeros(NUM_SLOTS)
        kp = np.zeros(NUM_SLOTS)
        kd = np.full(NUM_SLOTS, PASSIVE_KD)
        if self.mode == 'FIXSTAND':
            self.fix_t = min(self.fix_t + dt, FIXSTAND_S)
            a = self.fix_t / FIXSTAND_S
            target = self.fix_q0.copy()
            for i, s in enumerate(self.slots):
                target[s] = self.fix_q0[s] + (self.default[i] - self.fix_q0[s]) * a
            return target, np.array(FIXSTAND_KP, dtype=float), np.array(FIXSTAND_KD, dtype=float)
        if self.mode == 'WALK':
            q24 = np.array([q_slots[s] for s in self.slots])
            dq24 = np.array([dq_slots[s] for s in self.slots])
            obs = self.observation(gyro, quat, q24, dq24, cmd)
            action = self.sess.run(None, {self.inp: obs[None, :]})[0][0].astype(np.float64)
            self.last_action = action
            self.steps += 1
            q = np.array([q_slots[s] for s in range(NUM_SLOTS)])   # sloty spoza polityki: trzymaj pomiar
            q[self.slots] = self.default + self.scale * action
            kp[self.slots] = self.kp_walk
            kd[self.slots] = self.kd_walk
            return q, kp, kd
        return q, kp, kd   # PASSIVE


def rpy(quat):
    return quat_to_rpy(*quat)
