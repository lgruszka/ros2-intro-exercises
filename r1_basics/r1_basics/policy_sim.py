"""Symulacja fizyki R1 z wytrenowaną polityką chodu (bez ROS): MuJoCo (CPU) + ONNX Runtime.

Model i polityka pochodzą z treningu w unitree_rl_mjlab (zadanie Unitree-R1-Flat, warsztat W11):
  - model: scene/scene.xml zapisany przez `tools/export_sim.py` (Scene.write z mjlab: te same aktuatory
    pozycyjne, wzmocnienia i kolizje) + opcje fizyki z sim_meta.json (krok 5 ms, solver) albo plik .mjb,
  - polityka: policy.onnx z metadanymi mjlab (joint_names, default_joint_pos, action_scale, ...).

Wejście polityki (83 liczby, kolejność jak w treningu, „actor”):
  base_ang_vel(3, żyroskop IMU w ramie miednicy), projected_gravity(3), command(3: vx, vy, wz),
  phase(2: sin, cos fazy kroku o okresie 0.6 s; zera, gdy |komenda| < 0.1), joint_pos(24, względem pozy
  domyślnej), joint_vel(24), actions(24, poprzednia akcja).
Wyjście: 24 akcje; cel przegubu = default + action_scale * akcja, co 20 ms (4 kroki fizyki po 5 ms).
"""
import json
import math

import numpy as np

try:
    import mujoco
    import onnxruntime as ort
except ImportError as e:  # pragma: no cover - komunikat dla kursanta
    raise SystemExit(f'Brak pakietu: {e.name}. Zainstaluj: pip install mujoco onnxruntime') from e

# Sloty silników R1 w unitree_hg LowState (dds_wrapper r1/defines.h), po nazwach przegubów z R1.urdf.
SLOTS = {
    'left_hip_pitch_joint': 0, 'left_hip_roll_joint': 1, 'left_hip_yaw_joint': 2, 'left_knee_joint': 3,
    'left_ankle_pitch_joint': 4, 'left_ankle_roll_joint': 5,
    'right_hip_pitch_joint': 6, 'right_hip_roll_joint': 7, 'right_hip_yaw_joint': 8, 'right_knee_joint': 9,
    'right_ankle_pitch_joint': 10, 'right_ankle_roll_joint': 11,
    'waist_roll_joint': 12, 'waist_yaw_joint': 13,
    'left_shoulder_pitch_joint': 15, 'left_shoulder_roll_joint': 16, 'left_shoulder_yaw_joint': 17,
    'left_elbow_joint': 18, 'left_wrist_roll_joint': 19,
    'right_shoulder_pitch_joint': 22, 'right_shoulder_roll_joint': 23, 'right_shoulder_yaw_joint': 24,
    'right_elbow_joint': 25, 'right_wrist_roll_joint': 26,
}
PHASE_PERIOD = 0.6
STAND_THRESHOLD = 0.1


def _floats(s):
    return [float(x) for x in s.split(',')]


def quat_to_rpy(w, x, y, z):
    roll = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x))))
    yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    return roll, pitch, yaw


class R1PolicySim:
    def __init__(self, model_path, policy_path, meta_path=None):
        extra = {}
        if meta_path:
            with open(meta_path, encoding='utf-8') as f:
                extra = json.load(f)
        if model_path.endswith('.mjb'):
            self.m = mujoco.MjModel.from_binary_path(model_path)
        else:
            self.m = mujoco.MjModel.from_xml_path(model_path)
            # mjlab ustawia opcje fizyki dopiero po kompilacji (MujocoCfg.apply) - odtwarzamy je z sim_meta.json
            for k, v in extra.get('opt', {}).items():
                if k == 'gravity':
                    self.m.opt.gravity[:] = v
                else:
                    setattr(self.m.opt, k, v)
        self.d = mujoco.MjData(self.m)
        self.sess = ort.InferenceSession(policy_path, providers=['CPUExecutionProvider'])
        self.inp = self.sess.get_inputs()[0].name
        meta = dict(self.sess.get_modelmeta().custom_metadata_map)
        self.joint_names = meta['joint_names'].split(',')
        self.default = np.array(_floats(meta['default_joint_pos']), dtype=np.float64)
        scale = meta['action_scale']
        self.scale = np.array(_floats(scale) if ',' in scale else [float(scale)] * len(self.joint_names))
        self.obs_names = meta.get('observation_names', '').split(',')
        self.decimation = int(extra.get('decimation', 4))
        self.step_dt = self.m.opt.timestep * self.decimation
        self.init_height = float(extra.get('init_height', 0.76))

        def find(objtype, name):
            for prefix in ('robot/', ''):
                i = mujoco.mj_name2id(self.m, objtype, prefix + name)
                if i >= 0:
                    return i
            raise KeyError(name)

        jids = [find(mujoco.mjtObj.mjOBJ_JOINT, n) for n in self.joint_names]
        self.qadr = np.array([self.m.jnt_qposadr[j] for j in jids])
        self.vadr = np.array([self.m.jnt_dofadr[j] for j in jids])
        act_of_joint = {int(self.m.actuator_trnid[a, 0]): a for a in range(self.m.nu)}
        self.act = np.array([act_of_joint[j] for j in jids])
        self.root_q = self.m.jnt_qposadr[find(mujoco.mjtObj.mjOBJ_JOINT, 'floating_base_joint')]
        self.root_v = self.m.jnt_dofadr[find(mujoco.mjtObj.mjOBJ_JOINT, 'floating_base_joint')]
        self.gyro = find(mujoco.mjtObj.mjOBJ_SENSOR, 'imu_ang_vel')
        self.acc = find(mujoco.mjtObj.mjOBJ_SENSOR, 'imu_lin_acc')
        self.gain0 = self.m.actuator_gainprm[:, 0].copy()
        self.bias0 = self.m.actuator_biasprm[:, :3].copy()
        self.mode = 'policy'
        self.reset()

    # ---- stan ---------------------------------------------------------------------------------
    def reset(self, x=0.0, y=0.0, yaw=0.0):
        mujoco.mj_resetData(self.m, self.d)
        q = self.d.qpos
        q[self.root_q:self.root_q + 3] = (x, y, self.init_height)
        q[self.root_q + 3:self.root_q + 7] = (math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2))
        q[self.qadr] = self.default
        self.d.ctrl[self.act] = self.default
        mujoco.mj_forward(self.m, self.d)
        self.last_action = np.zeros(len(self.joint_names))
        self.steps = 0
        self.set_mode('policy')

    def set_mode(self, mode):
        """'policy' (chód), 'damping' (kp=0, zostaje tłumienie), 'zero_torque' (bez momentów)."""
        self.mode = mode
        self.m.actuator_gainprm[:, 0] = self.gain0
        self.m.actuator_biasprm[:, :3] = self.bias0
        if mode in ('damping', 'zero_torque'):
            self.m.actuator_gainprm[:, 0] = 0.0
            self.m.actuator_biasprm[:, 1] = 0.0
            if mode == 'zero_torque':
                self.m.actuator_biasprm[:, 2] = 0.0

    def base_pose(self):
        x, y, z = self.d.qpos[self.root_q:self.root_q + 3]
        w, qx, qy, qz = self.d.qpos[self.root_q + 3:self.root_q + 7]
        return float(x), float(y), float(z), (float(w), float(qx), float(qy), float(qz))

    def fallen(self):
        w, x, y, z = self.d.qpos[self.root_q + 3:self.root_q + 7]
        up_z = 1 - 2 * (x * x + y * y)  # oś z miednicy w świecie (składowa pionowa)
        return self.d.qpos[self.root_q + 2] < 0.45 or up_z < math.cos(math.radians(70))

    # ---- polityka -----------------------------------------------------------------------------
    def observation(self, cmd):
        gyro = self.d.sensordata[self.m.sensor_adr[self.gyro]:self.m.sensor_adr[self.gyro] + 3]
        w, x, y, z = self.d.qpos[self.root_q + 3:self.root_q + 7]
        # grawitacja (0, 0, -1) w ramie miednicy: R^T * g
        R = np.zeros(9)
        mujoco.mju_quat2Mat(R, np.array([w, x, y, z]))
        g = R.reshape(3, 3).T @ np.array([0.0, 0.0, -1.0])
        cmd = np.asarray(cmd, dtype=np.float64)
        if np.linalg.norm(cmd) < STAND_THRESHOLD:
            phase = np.zeros(2)
        else:
            ph = (self.steps * self.step_dt) % PHASE_PERIOD / PHASE_PERIOD
            phase = np.array([math.sin(2 * math.pi * ph), math.cos(2 * math.pi * ph)])
        jp = self.d.qpos[self.qadr] - self.default
        jv = self.d.qvel[self.vadr]
        return np.concatenate([gyro, g, cmd, phase, jp, jv, self.last_action]).astype(np.float32)

    def step(self, cmd=(0.0, 0.0, 0.0)):
        """Jeden krok polityki (step_dt = 20 ms): obserwacja -> ONNX -> cele przegubów -> 4 kroki fizyki."""
        if self.mode == 'policy':
            obs = self.observation(cmd)
            action = self.sess.run(None, {self.inp: obs[None, :]})[0][0].astype(np.float64)
            self.last_action = action
            self.d.ctrl[self.act] = self.default + self.scale * action
        for _ in range(self.decimation):
            mujoco.mj_step(self.m, self.d)
        self.steps += 1

    # ---- odczyty dla /lowstate ----------------------------------------------------------------
    def imu(self):
        x, y, z, quat = self.base_pose()
        gyro = self.d.sensordata[self.m.sensor_adr[self.gyro]:self.m.sensor_adr[self.gyro] + 3]
        acc = self.d.sensordata[self.m.sensor_adr[self.acc]:self.m.sensor_adr[self.acc] + 3]
        return quat, quat_to_rpy(*quat), [float(v) for v in gyro], [float(v) for v in acc]

    def joints(self):
        """[(slot, q, dq)] dla 24 przegubów polityki."""
        q = self.d.qpos[self.qadr]
        dq = self.d.qvel[self.vadr]
        return [(SLOTS.get(n, -1), float(q[i]), float(dq[i])) for i, n in enumerate(self.joint_names)]

    def base_twist(self):
        """(vx, vy, wz) w ramie robota (z prędkości miednicy)."""
        v = self.d.qvel[self.root_v:self.root_v + 6]
        _, _, _, (w, x, y, z) = self.base_pose()
        yaw = quat_to_rpy(w, x, y, z)[2]
        c, s = math.cos(yaw), math.sin(yaw)
        return c * v[0] + s * v[1], -s * v[0] + c * v[1], float(v[5])
