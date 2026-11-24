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
"""
import time

from nav_msgs.msg import Odometry
from r1_basics.params import declare_float
from r1_basics.policy_sim import R1PolicySim
from r1_basics.r1_mock import R1Mock
from r1_basics.sport_api import FSM_DAMP, FSM_WALK, FSM_ZERO_TORQUE
from r1_basics.util import wrap_angle, yaw_to_quat
import rclpy
from rclpy.executors import ExternalShutdownException
from std_srvs.srv import Trigger


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
        self.get_logger().info(
            f'r1_sim: model {model}, polityka {policy} ({len(self._sim.joint_names)} przegubów), '
            f'krok polityki {self._sim.step_dt * 1000:.0f} ms. To NASZA polityka z W11, nie sterownik Unitree.')

    # ---- sport API: tryby napędu ----------------------------------------------------------------
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
        st.tick = (self.tick_count * 20) & 0xFFFFFFFF
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
