#!/usr/bin/env python3
"""r1_policy - polityka chodu R1 z W11 jako sterownik niskiego poziomu (W12): /cmd_vel + /lowstate -> /lowcmd.

!!! NA PRAWDZIWYM R1 TYLKO NA SZUBIENICY, Z ROBOTEM PODWIESZONYM I ASEKUROWANYM !!!
Na robocie wymaga trybu debug Unitree (L2+R2 w damping/zero torque): wbudowany sterownik równowagi jest wtedy
wyłączony i robot trzyma się wyłącznie na tej polityce. Każdy błąd = upadek 29-kilogramowego robota.

Ten sam węzeł działa z symulatorem (r1_sim interface:=lowcmd) i z robotem - zmienia się tylko sieć/DDS.
Stany (jak deploy/robots/r1 Unitree): PASSIVE (kp 0, kd 3) -> FIXSTAND (3 s do pozy domyślnej) -> WALK (polityka).
Przełączanie: pilot (z /lowstate: L2+B -> PASSIVE, L2+UP -> FIXSTAND, R2+A -> WALK) albo
  ros2 topic pub --once /r1/policy/mode std_msgs/msg/String "{data: FIXSTAND}"   (PASSIVE / FIXSTAND / WALK)
Zabezpieczenia: brak /lowstate > lowstate_timeout_s -> PASSIVE; przechył > 1 rad -> PASSIVE; /cmd_vel starszy
niż cmd_timeout_s -> komenda zero; komendy przycięte do max_vx / max_vy / max_wz.
"""
import time

import numpy as np

from r1_basics.arm_sdk import hg_lowcmd_crc
from r1_basics.params import declare_float
from r1_basics.policy_ctrl import NUM_SLOTS, R1PolicyController, remote_buttons
from r1_basics.util import clamp
from geometry_msgs.msg import Twist
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import String
from unitree_hg.msg import LowCmd, LowState

BANNER = ('r1_policy: NA PRAWDZIWYM R1 TYLKO NA SZUBIENICY Z PODWIESZONYM I ASEKUROWANYM ROBOTEM. '
          'Nasza polityka RL (W11/W12) nie jest sterownikiem Unitree; w trybie debug robot nie ma innego zabezpieczenia równowagi.')


class R1Policy(Node):
    def __init__(self):
        super().__init__('r1_policy')
        policy = self.declare_parameter('policy', '').value
        if not policy:
            raise SystemExit('r1_policy: podaj policy:=.../policy.onnx')
        self.max_vx = declare_float(self, 'max_vx', 0.3)
        self.max_vy = declare_float(self, 'max_vy', 0.2)
        self.max_wz = declare_float(self, 'max_wz', 0.5)
        self.cmd_timeout = declare_float(self, 'cmd_timeout_s', 0.5)
        self.state_timeout = declare_float(self, 'lowstate_timeout_s', 0.1)
        cmd_rate = declare_float(self, 'cmd_rate_hz', 500.0)
        self.ctrl = R1PolicyController(policy)
        self.get_logger().warning(BANNER)

        self.lowstate = None
        self.lowstate_t = None
        self.cmd = (0.0, 0.0, 0.0)
        self.cmd_t = None
        self.buttons = set()
        self.q_target = np.zeros(NUM_SLOTS)
        self.kp = np.zeros(NUM_SLOTS)
        self.kd = np.full(NUM_SLOTS, 3.0)
        self.msg = LowCmd()

        self.create_subscription(LowState, '/lowstate', self.on_lowstate, qos_profile_sensor_data)
        self.create_subscription(Twist, '/cmd_vel', self.on_cmd_vel, 10)
        self.create_subscription(String, '/r1/policy/mode', self.on_mode, 10)
        self.pub = self.create_publisher(LowCmd, '/lowcmd', qos_profile_sensor_data)
        self.state_pub = self.create_publisher(String, '/r1/policy/state', 10)
        self.create_timer(self.ctrl.step_dt, self.tick)            # sterownik i polityka: 50 Hz
        self.create_timer(1.0 / cmd_rate, self.publish_lowcmd)     # /lowcmd: ostatnie cele, cmd_rate_hz
        self.create_timer(0.5, lambda: self.state_pub.publish(String(data=self.ctrl.mode)))
        self.get_logger().info(f'r1_policy: {len(self.ctrl.joint_names)} przegubów, polityka co '
                               f'{self.ctrl.step_dt * 1000:.0f} ms, /lowcmd {cmd_rate:.0f} Hz, start: PASSIVE')

    # ---- wejścia -------------------------------------------------------------------------------------
    def on_lowstate(self, msg):
        self.lowstate = msg
        self.lowstate_t = time.monotonic()
        buttons = remote_buttons(msg.wireless_remote)
        if buttons != self.buttons:
            if {'L2', 'B'} <= buttons:
                self.switch('PASSIVE', 'pilot L2+B')
            elif {'L2', 'up'} <= buttons:
                self.switch('FIXSTAND', 'pilot L2+UP')
            elif {'R2', 'A'} <= buttons:
                self.switch('WALK', 'pilot R2+A')
            self.buttons = buttons

    def on_cmd_vel(self, msg):
        self.cmd = (clamp(msg.linear.x, -self.max_vx, self.max_vx), clamp(msg.linear.y, -self.max_vy, self.max_vy),
                    clamp(msg.angular.z, -self.max_wz, self.max_wz))
        self.cmd_t = time.monotonic()

    def on_mode(self, msg):
        self.switch(msg.data.strip().upper(), 'temat /r1/policy/mode')

    def switch(self, mode, why):
        if self.lowstate is None and mode != 'PASSIVE':
            self.get_logger().warning(f'{mode} odrzucone: brak /lowstate')
            return
        q = [m.q for m in self.lowstate.motor_state] if self.lowstate is not None else [0.0] * 35
        note = self.ctrl.request(mode, q)
        if note:
            self.get_logger().info(f'{note} ({why})')

    # ---- pętla 50 Hz -----------------------------------------------------------------------------------
    def tick(self):
        now = time.monotonic()
        if self.lowstate is None or now - self.lowstate_t > self.state_timeout:
            if self.ctrl.mode != 'PASSIVE':
                self.ctrl.mode = 'PASSIVE'
                self.get_logger().error('brak świeżego /lowstate: PASSIVE')
            self.q_target, self.kp, self.kd = self.ctrl.command(None, None, None, None, None, 0.0)
            return
        st = self.lowstate
        quat = tuple(float(v) for v in st.imu_state.quaternion)           # w, x, y, z (Unitree)
        msg = self.ctrl.safety(quat)
        if msg:
            self.get_logger().error(msg)
        cmd = self.cmd if (self.cmd_t is not None and now - self.cmd_t < self.cmd_timeout) else (0.0, 0.0, 0.0)
        q_s = [m.q for m in st.motor_state]
        dq_s = [m.dq for m in st.motor_state]
        self.q_target, self.kp, self.kd = self.ctrl.command(list(st.imu_state.gyroscope), quat, q_s, dq_s, cmd,
                                                            self.ctrl.step_dt)

    def publish_lowcmd(self):
        if self.lowstate is None:
            return
        m = self.msg
        m.mode_pr = 0                                   # 0 = PR (kostka pitch/roll jak w URDF), Unitree Mode::PR
        m.mode_machine = self.lowstate.mode_machine     # jak w przykładach Unitree: przepisany z /lowstate
        for s in range(NUM_SLOTS):
            c = m.motor_cmd[s]
            c.mode = 1
            c.q, c.dq, c.tau = float(self.q_target[s]), 0.0, 0.0
            c.kp, c.kd = float(self.kp[s]), float(self.kd[s])
        m.crc = hg_lowcmd_crc(m)
        self.pub.publish(m)


def main(args=None):
    # Ctrl+C jako zwykły KeyboardInterrupt (jak w cmd_vel_bridge): kontekst ROS jeszcze żyje, więc zdążymy
    # wysłać PASSIVE (kp 0, kd 3) zamiast zostawić silniki z ostatnim celem
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = None
    try:
        node = R1Policy()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        if node is not None and node.lowstate is not None:
            node.ctrl.mode = 'PASSIVE'
            node.q_target, node.kp, node.kd = node.ctrl.command(None, None, None, None, None, 0.0)
            for _ in range(5):
                node.publish_lowcmd()
                time.sleep(0.01)
            node.get_logger().warning('zatrzymanie: wysłano PASSIVE')
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
