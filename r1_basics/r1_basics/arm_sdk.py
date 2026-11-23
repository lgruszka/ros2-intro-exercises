"""arm_sdk R1: przeguby, limity, KP/KD, CRC wiadomości unitree_hg/LowCmd i plan ruchu (bez importów ROS).

Źródła (docs/r1_plan.md §5 i §10):
- kolejność przegubów jak `ArmSdk::JOINTS` w unitree_sdk2 `dds_wrapper/robots/r1/r1_pub.h`,
- limity [rad] z `R1.urdf` (unitree_ros), KP/KD z dokumentacji arm_control_routine,
- waga w `mode_pr` (0-100): `weight(coe) { mode_pr = clamp(int(coe*100), 0, 100) }` (r1_pub.h).
"""
from collections import namedtuple
import math
import struct

NUM_MOTORS = 35

JointSpec = namedtuple('JointSpec', 'slot name lower upper kp kd')

ARM_JOINTS = (
    JointSpec(15, 'left_shoulder_pitch_joint', -3.1416, 2.0944, 50.0, 2.0),
    JointSpec(16, 'left_shoulder_roll_joint', -0.22689, 2.4784, 50.0, 2.0),
    JointSpec(17, 'left_shoulder_yaw_joint', -1.9199, 1.9199, 40.0, 2.0),
    JointSpec(18, 'left_elbow_joint', -0.97564, 2.1852, 40.0, 2.0),
    JointSpec(19, 'left_wrist_roll_joint', -1.9199, 1.9199, 30.0, 2.0),
    JointSpec(22, 'right_shoulder_pitch_joint', -3.1416, 2.0944, 50.0, 2.0),
    JointSpec(23, 'right_shoulder_roll_joint', -2.47849, 0.2268, 50.0, 2.0),
    JointSpec(24, 'right_shoulder_yaw_joint', -1.9199, 1.9199, 40.0, 2.0),
    JointSpec(25, 'right_elbow_joint', -0.97564, 2.1852, 40.0, 2.0),
    JointSpec(26, 'right_wrist_roll_joint', -1.9199, 1.9199, 30.0, 2.0),
    JointSpec(13, 'waist_yaw_joint', -2.618, 2.618, 50.0, 3.0),
    JointSpec(29, 'head_pitch_joint', -0.62832, 0.62832, 15.0, 1.0),
    JointSpec(30, 'head_yaw_joint', -2.0071, 2.0071, 15.0, 1.0),
)
JOINT_INDEX = {j.name: i for i, j in enumerate(ARM_JOINTS)}
ARM_SLOTS = tuple(j.slot for j in ARM_JOINTS)

# Kurs: cele najwyżej do 70% zakresu URDF (liczone od zera, bo 0 leży w zakresie każdego przegubu).
SAFE_FRACTION = 0.7


def safe_limits(joint, fraction=SAFE_FRACTION):
    """Ostrożne limity celu [rad] dla przegubu: URDF przeskalowany do `fraction` zakresu."""
    return joint.lower * fraction, joint.upper * fraction


def weight_to_mode_pr(weight):
    """Waga arm_sdk 0.0-1.0 -> mode_pr 0-100 (jak ArmSdk::weight w r1_pub.h, int = obcięcie)."""
    return max(0, min(100, int(weight * 100.0 + 1e-6)))


# ---------------------------------------------------------------------------------------------
# CRC unitree_hg LowCmd - port `crc32_core` z unitree_sdk2 (dds_wrapper/common/crc.h) i
# unitree_ros2 (example/src/src/common/motor_crc_hg.cpp). Wiadomość pakowana bajt w bajt jak
# struktura C (wyrównanie 4 B, little-endian), dokładnie jak `__PackHGLowCmd` w
# unitree_sdk2py/utils/crc.py: mode_pr, mode_machine, 2 B wypełnienia, 35 x MotorCmd
# (mode + 3 B wypełnienia, q, dq, tau, kp, kd, reserve), reserve[4], crc -> 1004 B.
# CRC liczy się z 250 słów 32-bit (bez ostatniego, czyli samego pola crc).
# ---------------------------------------------------------------------------------------------
HG_LOWCMD_FMT = '<2B2x' + 'B3x5fI' * NUM_MOTORS + '4I' + 'I'
HG_LOWCMD_SIZE = struct.calcsize(HG_LOWCMD_FMT)   # 1004
_POLY = 0x04C11DB7


def hg_lowcmd_bytes(msg):
    """Bajty LowCmd w układzie struktury C (msg: unitree_hg/msg/LowCmd albo obiekt o tych polach)."""
    data = [int(msg.mode_pr), int(msg.mode_machine)]
    for i in range(NUM_MOTORS):
        m = msg.motor_cmd[i]
        data += [int(m.mode), float(m.q), float(m.dq), float(m.tau), float(m.kp), float(m.kd),
                 int(m.reserve)]
    data += [int(r) for r in msg.reserve]
    data.append(int(msg.crc))
    return struct.pack(HG_LOWCMD_FMT, *data)


def crc32_core_bitwise(words):
    """Dosłowny port crc32_core (bit po bicie) - wolny, służy jako wzorzec w testach."""
    crc = 0xFFFFFFFF
    for data in words:
        xbit = 1 << 31
        for _ in range(32):
            if crc & 0x80000000:
                crc = ((crc << 1) & 0xFFFFFFFF) ^ _POLY
            else:
                crc = (crc << 1) & 0xFFFFFFFF
            if data & xbit:
                crc ^= _POLY
            xbit >>= 1
    return crc


def _make_table():
    table = []
    for byte in range(256):
        crc = byte << 24
        for _ in range(8):
            crc = ((crc << 1) ^ _POLY) if crc & 0x80000000 else (crc << 1)
            crc &= 0xFFFFFFFF
        table.append(crc)
    return table


_TABLE = _make_table()


def crc32_core(words):
    """To samo co crc32_core_bitwise, ale tablicowo (bajt na krok) - wystarczająco szybkie na 100 Hz.

    crc32_core z Unitree to zwykłe CRC-32 MSB-first (wielomian 0x04C11DB7, start 0xFFFFFFFF, bez
    odbicia i bez końcowego XOR), podawane słowami 32-bit od najstarszego bitu - czyli bajty każdego
    słowa od najstarszego.
    """
    crc = 0xFFFFFFFF
    table = _TABLE
    for byte in struct.pack('>%dI' % len(words), *words):
        crc = ((crc << 8) & 0xFFFFFFFF) ^ table[((crc >> 24) ^ byte) & 0xFF]
    return crc


def hg_lowcmd_crc(msg):
    """CRC dla unitree_hg/LowCmd - wpisz wynik do msg.crc przed publikacją."""
    raw = hg_lowcmd_bytes(msg)
    n_words = len(raw) // 4 - 1
    return crc32_core(struct.unpack('<%dI' % n_words, raw[:4 * n_words]))


# ---------------------------------------------------------------------------------------------
# Plan ruchu arm_sequence: lista odcinków (nazwa, czas, funkcja s -> (cele 13 przegubów, waga)).
# ---------------------------------------------------------------------------------------------
Segment = namedtuple('Segment', 'name duration fn')


def pose(base, **joints):
    """Kopia pozy `base` (13 wartości) z podmienionymi przegubami (nazwa przegubu = wartość w rad)."""
    q = list(base)
    for name, value in joints.items():
        q[JOINT_INDEX[name]] = value
    return q


# Kierunki z R1.urdf (osie przegubów; w pozie zerowej ramię zwisa w dół):
#   łokieć: 0 = przedramię pod kątem prostym do ramienia (poziomo do przodu), +1.57 = ręka wyprostowana,
#           ujemny = mocniej zgięty (przedramię w górę),
#   shoulder_pitch ujemny = ręka do przodu, shoulder_roll: lewy dodatni / prawy ujemny = ręka w bok,
#   head_yaw i waist_yaw dodatni = w lewo, head_pitch dodatni = w dół.
# Uwaga: cel z oficjalnego r1_arm_sdk_dds_example.cpp (prawy łokieć -1.57) leży poza zakresem łokcia
# w URDF (-0.976 .. 2.185) - nie kopiuj go.

# Poza startowa: ręce wzdłuż ciała, łokcie lekko zgięte (ok. 20 st.), głowa i talia na wprost.
START_POSE = pose([0.0] * len(ARM_JOINTS), left_elbow_joint=1.2, right_elbow_joint=1.2)
# Prawa ręka do machania: ramię do przodu i w bok, łokieć zgięty pod kątem prostym (przedramię do przodu).
WAVE_POSE = pose(START_POSE, right_shoulder_pitch_joint=-0.6, right_shoulder_roll_joint=-1.0,
                 right_elbow_joint=0.0)
WAVE_AMPLITUDE = 0.3          # [rad] łokieć macha między 0 a -0.6 (przedramię unosi się i opada)
WAVE_PERIOD = 2.0             # [s] jedno machnięcie (szczyt prędkości 0.94 rad/s)


def smooth(s, interp='cosine'):
    """Profil 0..1: 'cosine' (zerowa prędkość na końcach) albo 'linear'."""
    s = min(max(s, 0.0), 1.0)
    if interp == 'linear':
        return s
    return 0.5 - 0.5 * math.cos(math.pi * s)


def move_duration(q_from, q_to, min_duration, max_speed, interp='cosine'):
    """Czas przejazdu tak, żeby najszybszy przegub nie przekroczył max_speed [rad/s] (+5% zapasu)."""
    delta = max(abs(b - a) for a, b in zip(q_from, q_to))
    peak_factor = 1.0 if interp == 'linear' else math.pi / 2.0
    return max(min_duration, 1.05 * peak_factor * delta / max_speed)


def move_segment(name, q_from, q_to, min_duration, max_speed, interp='cosine'):
    q_from, q_to = list(q_from), list(q_to)
    duration = move_duration(q_from, q_to, min_duration, max_speed, interp)

    def fn(t):
        a = smooth(t / duration, interp)
        return [qa + (qb - qa) * a for qa, qb in zip(q_from, q_to)], 1.0
    return Segment(name, duration, fn)


def build_sequence(seed, ramp_s=1.0, move_s=2.0, max_speed=1.0, waves=3, interp='cosine'):
    """Cała sekwencja W10: rampa wagi -> poza startowa -> machanie -> głowa -> talia -> powrót -> oddanie."""
    seed = list(seed)
    elbow = JOINT_INDEX['right_elbow_joint']
    # okres machania wydłużony, jeśli max_speed jest niższe niż 1 rad/s
    period = max(WAVE_PERIOD, 2.0 * math.pi * WAVE_AMPLITUDE / (0.95 * max_speed))
    half = 0.5 * move_s

    def ramp_up(t):
        return seed, min(t / ramp_s, 1.0)

    def wave(t):
        q = list(WAVE_POSE)
        q[elbow] -= WAVE_AMPLITUDE * (1.0 - math.cos(2.0 * math.pi * t / period))
        return q, 1.0

    def ramp_down(t):
        return seed, max(1.0 - t / ramp_s, 0.0)

    look_left = pose(START_POSE, head_yaw_joint=0.5)
    look_right = pose(START_POSE, head_yaw_joint=-0.5)
    nod = pose(START_POSE, head_pitch_joint=0.3)
    waist_left = pose(START_POSE, waist_yaw_joint=0.3)
    waist_right = pose(START_POSE, waist_yaw_joint=-0.3)

    def mv(name, a, b, min_duration):
        return move_segment(name, a, b, min_duration, max_speed, interp)

    return [
        Segment('rampa wagi 0 -> 1 (trzymam zmierzoną pozę)', ramp_s, ramp_up),
        mv('do pozy startowej', seed, START_POSE, move_s),
        mv('prawa ręka w górę', START_POSE, WAVE_POSE, move_s),
        Segment('machanie x%d' % waves, waves * period, wave),
        mv('ręka w dół', WAVE_POSE, START_POSE, move_s),
        mv('głowa w lewo', START_POSE, look_left, half),
        mv('głowa w prawo', look_left, look_right, half),
        mv('głowa na wprost', look_right, START_POSE, half),
        mv('skinienie głową', START_POSE, nod, half),
        mv('głowa w górę', nod, START_POSE, half),
        mv('talia w lewo', START_POSE, waist_left, half),
        mv('talia w prawo', waist_left, waist_right, half),
        mv('talia na wprost', waist_right, START_POSE, half),
        mv('powrót do zmierzonej pozy', START_POSE, seed, move_s),
        Segment('oddanie: rampa wagi 1 -> 0', ramp_s, ramp_down),
    ]


def effective_limits(seed, fraction=SAFE_FRACTION):
    """Limity celu: ostrożne (70% URDF), poszerzone o zmierzoną pozę startową.

    Robot może stać z ręką poza 70% zakresu - wtedy trzymanie i powrót do tej pozy jest dozwolone,
    a przycięcie do 70% oznaczałoby szarpnięcie zaraz po przejęciu sterowania.
    """
    limits = []
    for joint, q0 in zip(ARM_JOINTS, seed):
        low, high = safe_limits(joint, fraction)
        limits.append((min(low, q0), max(high, q0)))
    return limits
