#!/usr/bin/env python3
"""r1_sim - R1 w fizyce MuJoCo z polityką chodu wytrenowaną w W11 (zamiast makiety r1_mock).

Ten sam kontrakt co r1_mock (W9 działa bez zmian):
  /api/sport/request -> /api/sport/response: 7001 GetFsmId, 7101 SetFsmId, 7105 SetVelocity
    (prędkość działa w FSM 811 przez `duration` s od ostatniej komendy, potem polityka dostaje zero),
  /lowstate (unitree_hg/LowState): IMU miednicy z symulacji (kwaternion w,x,y,z, rpy, żyroskop,
    akcelerometr) + q/dq 24 przegubów w slotach R1, kurs przesunięty o `imu_yaw0` jak w prawdziwym IMU,
  /r1/mock/ground_truth (Odometry): prawdziwa poza miednicy w symulacji.
Różnice wobec robota: to NASZA polityka (nie wbudowany sterownik Unitree), więc prędkości, rozpędzanie
i reakcja na komendy są inne. FSM 0/1 wyłączają napęd (robot upada jak w dokumentacji). arm_sdk nie jest
obsługiwane: rękami steruje polityka.
Parametry: model (plik .mjb z export_sim.py), policy (policy.onnx), meta (sim_meta.json, opcjonalnie).
Restart po upadku: ros2 service call /r1/sim/reset std_srvs/srv/Trigger

Tryb interface:=lowcmd (W12, jak tryb debug na robocie): polityka NIE działa w symulatorze - steruje węzeł r1_policy
przez /lowcmd (unitree_hg/LowCmd: q, kp, kd na slotach 0-26, CRC). Usługa sport nie odpowiada (jak w trybie debug).
Krok fizyki 5 ms, /lowstate co krok (200 Hz) z polem wireless_remote. Dodatkowo:
  - szubienica (gantry:=true): lina zaczepiona na tułowiu; /r1/sim/gantry (std_msgs/Float64) = wysokość napięcia liny
    względem zaczepienia stojącego robota [m]: +0.12 robot wisi (stopy w powietrzu), 0 stopy dotykają, -0.15 lina luźna
    (łapie dopiero przy upadku),
  - pilot: /r1/sim/remote (std_msgs/String, np. "L2+B") wciska przyciski w /lowstate.wireless_remote na 0.3 s,
  - zaburzenia: cmd_delay_ms (opóźnienie /lowcmd), kp_scale, friction_scale, extra_torso_mass.
"""
import collections
import time

import numpy as np

from nav_msgs.msg import Odometry
from r1_basics.arm_sdk import hg_lowcmd_crc
from r1_basics.params import declare_float
from r1_basics.policy_ctrl import remote_bytes
from r1_basics.policy_sim import R1PolicySim
from r1_basics.r1_mock import R1Mock
from r1_basics.sport_api import FSM_DAMP, FSM_WALK, FSM_ZERO_TORQUE
from r1_basics.util import wrap_angle, yaw_to_quat
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import Float64, String
from std_srvs.srv import Trigger
from unitree_hg.msg import LowCmd


class R1Sim(R1Mock):
    def __init__(self):
        # parametry sim przed konstruktorem makiety (on tworzy timer i publikatory)
        self._sim = None
        super().__init__('r1_sim')
        model = self.declare_parameter('model', '').value
        policy = self.declare_parameter('policy', '').value
        meta = self.declare_parameter('meta', '').value or None
        self.realtime = declare_float(self, 'realtime_factor', 1.0)
        if not model or not policy:
            raise SystemExit('r1_sim: podaj parametry model:=... (.mjb) i policy:=... (policy.onnx)')
        self._sim = R1PolicySim(model, policy, meta)
        self.fell_logged = False
        self.create_service(Trigger, '/r1/sim/reset', self.on_reset)
        self.interface = str(self.declare_parameter('interface', 'sport').value)
        if self.interface == 'lowcmd':
            self.setup_lowcmd()
        self.get_logger().info(
            f'r1_sim: model {model}, polityka {policy} ({len(self._sim.joint_names)} przegubów), '
            f'krok polityki {self._sim.step_dt * 1000:.0f} ms. To NASZA polityka RL (W11/W12), nie sterownik Unitree.')

    # ---- tryb lowcmd (W12) ---------------------------------------------------------------------
    def setup_lowcmd(self):
        sim = self._sim
        self.delay_s = declare_float(self, 'cmd_delay_ms', 0.0) / 1000.0
        self.kp_scale = declare_float(self, 'kp_scale', 1.0)
        sim.perturb(friction_scale=declare_float(self, 'friction_scale', 1.0),
                    extra_torso_mass=declare_float(self, 'extra_torso_mass', 0.0))
        self.gantry = bool(self.declare_parameter('gantry', True).value)
        self.gantry_offset = declare_float(self, 'gantry_start', 0.12)
        self.lowcmd_queue = collections.deque()
        self.lowcmd_count = 0
        self.crc_warned = False
        self.remote_until = 0.0
        self.remote = [0] * 40
        self.rope_caught_logged = False
        self.create_subscription(LowCmd, '/lowcmd', self.on_lowcmd, qos_profile_sensor_data)
        self.create_subscription(Float64, '/r1/sim/gantry', self.on_gantry, 10)
        self.create_subscription(String, '/r1/sim/remote', self.on_remote, 10)
        self.reset_lowcmd()
        self.get_logger().warning(
            'r1_sim: tryb lowcmd (jak tryb debug na robocie): sterowanie tylko przez /lowcmd, usługa sport nie '
            f'odpowiada. Szubienica: {"tak, robot wisi" if self.gantry else "NIE"}. Opóźnienie /lowcmd '
            f'{self.delay_s * 1000:.0f} ms, kp x{self.kp_scale}.')

    def reset_lowcmd(self):
        sim = self._sim
        lift = self.gantry_offset if self.gantry else 0.0
        sim.reset(height=sim.init_height + max(lift, 0.0))
        sim.gantry_height = sim.attach_stand + self.gantry_offset if self.gantry else None
        n = len(sim.joint_names)
        # zanim przyjdzie pierwsze /lowcmd: napęd miękki (kp 0, kd 3), jak damping przed uruchomieniem sterownika
        sim.set_motor_cmd(sim.default, np.zeros(n), np.full(n, 3.0))
        self.lowcmd_queue.clear()

    def on_lowcmd(self, msg):
        if hg_lowcmd_crc(msg) != msg.crc and not self.crc_warned:
            self.get_logger().warning('/lowcmd: CRC niezgodne (prawdziwy robot może takiej komendy nie przyjąć)')
            self.crc_warned = True
        sim = self._sim
        q, kp, kd = [], [], []
        for slot, _, _ in sim.joints():
            c = msg.motor_cmd[slot]
            on = c.mode == 1
            q.append(c.q)
            kp.append(c.kp * self.kp_scale if on else 0.0)
            kd.append(c.kd if on else 0.0)
        self.lowcmd_queue.append((time.monotonic() + self.delay_s, q, kp, kd))
        self.lowcmd_count += 1

    def on_gantry(self, msg):
        if not self.gantry:
            self.get_logger().warning('szubienica wyłączona (gantry:=false)')
            return
        self._sim.gantry_height = self._sim.attach_stand + float(msg.data)
        self.get_logger().info(f'szubienica: lina napina się {float(msg.data):+.2f} m względem stojącego robota')

    def on_remote(self, msg):
        names = [b.strip() for b in msg.data.replace('UP', 'up').replace('DOWN', 'down').split('+')]
        self.remote = remote_bytes(names)
        self.remote_until = time.monotonic() + 0.3
        self.get_logger().info(f'pilot: {msg.data}')

    def step_lowcmd(self):
        sim = self._sim
        now = time.monotonic()
        cmd = None
        while self.lowcmd_queue and self.lowcmd_queue[0][0] <= now:
            cmd = self.lowcmd_queue.popleft()
        if cmd is not None:
            sim.set_motor_cmd(np.array(cmd[1]), np.array(cmd[2]), np.array(cmd[3]))
        sim.physics_step()
        if sim.rope_force > 30 and sim.gantry_height is not None and sim.gantry_height < sim.attach_stand - 0.05:
            if not self.rope_caught_logged:
                self.get_logger().error('ASEKURACJA: lina złapała robota (upadek przy luźnej linie)')
                self.rope_caught_logged = True
        if now > self.remote_until:
            self.remote = [0] * 40

    # ---- sport API: tryby napędu ----------------------------------------------------------------
    def on_request(self, req):
        if getattr(self, 'interface', 'sport') == 'lowcmd':
            self.get_logger().warning('tryb lowcmd (debug): usługa sport nie odpowiada', throttle_duration_sec=5.0)
            return
        super().on_request(req)

    def set_fsm(self, parameter):
        code = super().set_fsm(parameter)
        if code == 0 and self._sim is not None:
            if self.fsm == FSM_ZERO_TORQUE:
                self._sim.set_mode('zero_torque')
            elif self.fsm == FSM_DAMP:
                self._sim.set_mode('damping')
            else:
                self._sim.set_mode('policy')
        return code

    def on_arm_sdk(self, msg):
        self.get_logger().warning('r1_sim: arm_sdk nieobsługiwane (rękami steruje polityka chodu)',
                                  throttle_duration_sec=5.0)

    def on_reset(self, _req, resp):
        if getattr(self, 'interface', 'sport') == 'lowcmd':
            self.reset_lowcmd()
            self.rope_caught_logged = False
            self.fell_logged = False
            resp.success = True
            resp.message = 'R1 z powrotem na szubienicy (wisi), napęd miękki'
            self.get_logger().info(resp.message)
            return resp
        self._sim.reset()
        self.v_until = 0.0
        self.fell_logged = False
        self.fsm = FSM_WALK
        resp.success = True
        resp.message = 'R1 postawiony na starcie (0, 0), FSM 811'
        self.get_logger().info(resp.message)
        return resp

    # ---- symulacja (timer z R1Mock, rate_hz = 1 / krok polityki) --------------------------------
    def step(self):
        if self._sim is None:
            return
        if getattr(self, 'interface', 'sport') == 'lowcmd':
            self.step_lowcmd()
            self.tick_count += 1
            self.publish_lowstate()
            if self.tick_count % 4 == 0:
                self.publish_ground_truth()
            return
        now = time.monotonic()
        cmd = self.v_cmd if (self.fsm == FSM_WALK and now < self.v_until) else (0.0, 0.0, 0.0)
        self._sim.step(cmd)
        if self._sim.fallen() and not self.fell_logged:
            self.get_logger().error('R1 upadł w symulacji. Restart: ros2 service call /r1/sim/reset '
                                    'std_srvs/srv/Trigger')
            self.fell_logged = True
        self.tick_count += 1
        if not self.get_parameter('pause_lowstate').value:
            self.publish_lowstate()
        if self.tick_count % 2 == 0:
            self.publish_ground_truth()

    def publish_lowstate(self):
        st = self.state
        quat, (roll, pitch, yaw), gyro, acc = self._sim.imu()
        imu_yaw = wrap_angle(yaw + self.imu_yaw0)
        # kwaternion przesunięty o imu_yaw0 wokół pionu: q' = q_z(yaw0) * q
        zx, zy, zz, zw = yaw_to_quat(self.imu_yaw0)
        w, x, y, z = quat
        qw = zw * w - zz * z
        qx = zw * x - zz * y
        qy = zw * y + zz * x
        qz = zw * z + zz * w
        st.tick = (self.tick_count * (5 if getattr(self, 'interface', 'sport') == 'lowcmd' else 20)) & 0xFFFFFFFF
        if getattr(self, 'interface', 'sport') == 'lowcmd':
            st.wireless_remote = self.remote
        st.imu_state.rpy = [roll, pitch, imu_yaw]
        st.imu_state.quaternion = [qw, qx, qy, qz]
        st.imu_state.gyroscope = gyro
        st.imu_state.accelerometer = acc
        for slot, q, dq in self._sim.joints():
            if 0 <= slot < len(st.motor_state):
                st.motor_state[slot].q, st.motor_state[slot].dq = q, dq
                st.motor_state[slot].motorstate = 0
        self.state_pub.publish(st)

    def publish_ground_truth(self):
        x, y, z, (w, qx, qy, qz) = self._sim.base_pose()
        vx, vy, wz = self._sim.base_twist()
        odom = Odometry()
        odom.header.stamp = self.get_clock().now().to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        odom.pose.pose.position.x, odom.pose.pose.position.y, odom.pose.pose.position.z = x, y, z
        odom.pose.pose.orientation.w, odom.pose.pose.orientation.x = w, qx
        odom.pose.pose.orientation.y, odom.pose.pose.orientation.z = qy, qz
        odom.twist.twist.linear.x, odom.twist.twist.linear.y = vx, vy
        odom.twist.twist.angular.z = wz
        self.gt_pub.publish(odom)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = R1Sim()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
