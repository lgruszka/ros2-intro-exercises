#!/usr/bin/env python3
"""r1_mock - makieta R1 do ćwiczeń bez robota: odtwarza zachowanie API, nie fizykę chodu.

Sport API (/api/sport/request -> /api/sport/response, pary po header.identity.id):
  7001 GetFsmId -> {"data": fsm}; 7101 SetFsmId {"data": id}; 7105 SetVelocity {"velocity", "duration"}
  (prędkość działa tylko w FSM 811, przez `duration` s od ostatniej komendy, potem stop); inne -> 3203.
  Odpowiedź na 7105 ma kod `reply_code` (127 = jak w zgłoszeniach społeczności, w których robot i tak szedł).
/lowstate (unitree_hg/LowState, rate_hz): IMU (rpy, kwaternion w,x,y,z, żyroskop) z symulowanego kursu
  + opcjonalny dryf `imu_yaw_bias` [rad/s] i szum `imu_noise` [rad]; motor_state q/dq 13 przegubów arm_sdk.
/arm_sdk (unitree_hg/LowCmd): q = w*q_cmd + (1-w)*q_domyślna (w = mode_pr/100), śledzenie z limitem
  prędkości; sprawdza CRC i ostrzega przy niezgodności; mode_pr >= 2 w FSM 811 -> FSM 816, chód
  zablokowany (jak zgłoszenia społeczności, sdk2_python #182).
/r1/mock/ground_truth (Odometry): prawdziwa poza makiety - do porównania z odometrią zliczeniową.
"""
import json
import math
import random
import time

from nav_msgs.msg import Odometry
from r1_basics.arm_sdk import ARM_JOINTS, hg_lowcmd_crc
from r1_basics.params import declare_float
from r1_basics.sport_api import (API_GET_FSM_ID, API_SET_FSM_ID, API_SET_VELOCITY, FSM_ARM_BLOCKED, FSM_DAMP,
                                 fsm_name, FSM_NAMES, FSM_WALK, FSM_ZERO_TORQUE, REQUEST_TOPIC,
                                 RESPONSE_TOPIC)
from r1_basics.util import clamp, wrap_angle, yaw_to_quat
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from unitree_api.msg import Request, Response
from unitree_hg.msg import LowCmd, LowState

# Poza, którą trzyma wbudowany sterownik (waga arm_sdk = 0): ręce zwisają lekko odwiedzione, prawie proste
# (łokieć +1.57 = wyprostowany, patrz arm_sdk.py). Poza prawdziwego R1 - do sprawdzenia na /lowstate.
DEFAULT_ARM_POSE = {'left_shoulder_roll_joint': 0.12, 'right_shoulder_roll_joint': -0.12,
                    'left_elbow_joint': 1.35, 'right_elbow_joint': 1.35}
CODE_BAD_PARAMETER = 3202      # zły format 7105 (tak odpowiedział R1 w zgłoszeniu xr_teleoperate #319)
CODE_NOT_IMPLEMENTED = 3203    # „API not implemented on the server” (dds_services_interface); 7002/7107 w #319
CODE_INVALID_FSM = 7302        # UT_ROBOT_LOCO_ERR_INVALID_FSM_ID (unitree_sdk2 r1_loco_error.hpp); w #319 robot dał 1003
CODE_FSM_REJECTED = 1001       # SetFsmId(811) w stanie 816 (zgłoszenia społeczności)
ARM_STALE_S = 0.5
JUMP_WARN_RAD = 0.05           # skok celu > 0.05 rad między wiadomościami (= 5 rad/s przy 100 Hz)


class R1Mock(Node):
    def __init__(self, node_name='r1_mock'):
        super().__init__(node_name)
        self.fsm = int(self.declare_parameter('fsm', FSM_WALK).value)
        self.declare_parameter('reply_code', 0)
        self.imu_yaw_bias = declare_float(self, 'imu_yaw_bias', 0.0)
        self.imu_yaw0 = declare_float(self, 'imu_yaw0', 0.3)
        self.imu_noise = declare_float(self, 'imu_noise', 0.0)
        rate_hz = declare_float(self, 'rate_hz', 100.0)
        self.vel_tau = max(declare_float(self, 'vel_tau', 0.15), 1e-3)
        self.arm_max_speed = declare_float(self, 'arm_max_speed', 3.0)
        self.inject_fault_s = declare_float(self, 'inject_fault_s', 0.0)
        self.declare_parameter('pause_lowstate', False)

        self.create_subscription(Request, REQUEST_TOPIC, self.on_request, 10)
        self.create_subscription(LowCmd, '/arm_sdk', self.on_arm_sdk, qos_profile_sensor_data)
        self.resp_pub = self.create_publisher(Response, RESPONSE_TOPIC, 10)
        self.state_pub = self.create_publisher(LowState, '/lowstate', 10)
        self.gt_pub = self.create_publisher(Odometry, '/r1/mock/ground_truth', 10)

        # chód
        self.x = self.y = self.yaw = 0.0
        self.v_cmd = (0.0, 0.0, 0.0)
        self.v_act = [0.0, 0.0, 0.0]
        self.v_until = 0.0
        self.yaw_drift = 0.0
        # ręce
        self.q_default = [DEFAULT_ARM_POSE.get(j.name, 0.0) for j in ARM_JOINTS]
        self.q = list(self.q_default)
        self.dq = [0.0] * len(ARM_JOINTS)
        self.q_cmd = list(self.q_default)
        self.weight = 0.0
        self.arm_time = None
        self.arm_active_since = None
        self.fault = False
        self.arm_stale_warned = False
        self.stats = None
        self.crc_logged = False
        self.reset_arm_stats()

        self.state = LowState()
        self.tick_count = 0
        self.last_step = time.monotonic()
        self.create_timer(1.0 / max(rate_hz, 1.0), self.step)
        self.get_logger().info(
            f'{self.get_name()}: FSM {self.fsm} ({fsm_name(self.fsm)}), lowstate {rate_hz:.0f} Hz, '
            f'imu_yaw0 {self.imu_yaw0} rad, imu_yaw_bias {self.imu_yaw_bias} rad/s, '
            f'reply_code {self.get_parameter("reply_code").value}')

    # ---- sport API --------------------------------------------------------------------------
    def on_request(self, req):
        api_id = req.header.identity.api_id
        code, data = 0, ''
        if api_id == API_GET_FSM_ID:
            data = json.dumps({'data': self.fsm})
        elif api_id == API_SET_FSM_ID:
            code = self.set_fsm(req.parameter)
        elif api_id == API_SET_VELOCITY:
            code = self.set_velocity(req.parameter)
        else:
            code = CODE_NOT_IMPLEMENTED
        resp = Response()
        resp.header.identity.id = req.header.identity.id
        resp.header.identity.api_id = api_id
        resp.header.status.code = int(code)
        resp.data = data
        self.resp_pub.publish(resp)

    def set_fsm(self, parameter):
        try:
            fsm = int(json.loads(parameter)['data'])
        except (ValueError, KeyError, TypeError):
            return CODE_BAD_PARAMETER
        if fsm not in FSM_NAMES or fsm == FSM_ARM_BLOCKED:
            return CODE_INVALID_FSM
        if fsm == FSM_WALK and self.fsm == FSM_ARM_BLOCKED and self.weight >= 0.02:
            self.get_logger().warning('SetFsmId(811) odrzucone kodem 1001: arm_sdk wciąż trzyma ręce (FSM 816)')
            return CODE_FSM_REJECTED
        if fsm in (FSM_ZERO_TORQUE, FSM_DAMP):
            self.get_logger().warning(f'FSM {fsm} ({fsm_name(fsm)}): prawdziwy R1 właśnie by upadł!')
        self.get_logger().info(f'FSM {self.fsm} -> {fsm} ({fsm_name(fsm)})')
        self.fsm = fsm
        if fsm != FSM_WALK:
            self.v_until = 0.0
        return 0

    def set_velocity(self, parameter):
        try:
            p = json.loads(parameter)
            vx, vy, wz = (float(v) for v in p['velocity'])
            duration = float(p['duration'])
        except (ValueError, KeyError, TypeError):
            self.get_logger().warning(f'SetVelocity: zły parametr {parameter!r}', throttle_duration_sec=2.0)
            return CODE_BAD_PARAMETER
        if self.fsm == FSM_WALK:
            self.v_cmd = (vx, vy, wz)
            self.v_until = time.monotonic() + max(duration, 0.0)
        elif vx or vy or wz:
            self.get_logger().warning(
                f'SetVelocity zignorowane: FSM {self.fsm} ({fsm_name(self.fsm)}) - prędkość działa tylko w 811 '
                '(sport_cli start)', throttle_duration_sec=2.0)
        return int(self.get_parameter('reply_code').value)

    # ---- arm_sdk ----------------------------------------------------------------------------
    def reset_arm_stats(self):
        self.stats = {'msgs': 0, 'crc_ok': 0, 'crc_bad': 0, 'max_w_jump': 0, 'max_q_jump': 0.0,
                      'over_limit': 0, 'max_mode_pr': 0}
        self.last_mode_pr = 0
        self.last_q_cmd_msg = None

    def on_arm_sdk(self, msg):
        now = time.monotonic()
        st = self.stats
        st['msgs'] += 1
        expected = hg_lowcmd_crc(msg)
        if expected == msg.crc:
            if not self.crc_logged:
                self.get_logger().info('arm_sdk: CRC OK (pierwsza wiadomość)')
                self.crc_logged = True
            st['crc_ok'] += 1
        else:
            st['crc_bad'] += 1
            self.get_logger().warning(
                f'arm_sdk: CRC niezgodne (jest {msg.crc}, powinno {expected}); oficjalny przykład R1 '
                'nie liczy CRC, więc makieta tylko ostrzega', throttle_duration_sec=2.0)

        mode_pr = int(msg.mode_pr)
        st['max_w_jump'] = max(st['max_w_jump'], abs(mode_pr - self.last_mode_pr))
        st['max_mode_pr'] = max(st['max_mode_pr'], mode_pr)
        if abs(mode_pr - self.last_mode_pr) > 10:
            self.get_logger().warning(f'arm_sdk: skok wagi {self.last_mode_pr} -> {mode_pr} (brak rampy?)')
        q_cmd = [float(msg.motor_cmd[j.slot].q) for j in ARM_JOINTS]
        for i, (j, q) in enumerate(zip(ARM_JOINTS, q_cmd)):
            if mode_pr > 0 and not j.lower <= q <= j.upper:
                st['over_limit'] += 1
                self.get_logger().warning(f'arm_sdk: {j.name} cel {q:.3f} poza URDF [{j.lower}, {j.upper}]',
                                          throttle_duration_sec=1.0)
            if mode_pr > 0 and self.last_q_cmd_msg is not None:
                jump = abs(q - self.last_q_cmd_msg[i])
                st['max_q_jump'] = max(st['max_q_jump'], jump)
                if jump > JUMP_WARN_RAD:
                    self.get_logger().warning(f'arm_sdk: skok celu {j.name} o {jump:.3f} rad',
                                              throttle_duration_sec=1.0)
        self.last_q_cmd_msg = q_cmd

        if mode_pr >= 2 and self.fsm == FSM_WALK:
            self.get_logger().warning(
                'arm_sdk z wagą >= 0.02 w FSM 811 -> FSM 816: chód zablokowany (jak zgłoszenia społeczności, '
                'sdk2_python #182). W10 rób na stojącym robocie (FSM 4)!')
            self.fsm = FSM_ARM_BLOCKED
            self.v_until = 0.0
        if mode_pr > 0 and self.arm_active_since is None:
            self.arm_active_since = now
            self.get_logger().info('arm_sdk: przejęcie górnej części ciała (waga > 0)')
        if mode_pr == 0 and self.last_mode_pr > 0:
            self.get_logger().info(
                f'arm_sdk oddane (waga 0): wiadomości {st["msgs"]}, CRC OK {st["crc_ok"]} / złe {st["crc_bad"]}, '
                f'max mode_pr {st["max_mode_pr"]}, max skok wagi {st["max_w_jump"]}, '
                f'max skok celu {st["max_q_jump"]:.4f} rad, cele poza URDF {st["over_limit"]}'
                + (' - FSM nadal 816, wyślij Start (811)' if self.fsm == FSM_ARM_BLOCKED else ''))
            self.arm_active_since = None
            self.fault = False
            self.reset_arm_stats()
        self.last_mode_pr = mode_pr
        self.weight = mode_pr / 100.0
        self.q_cmd = q_cmd
        self.arm_time = now
        self.arm_stale_warned = False

    # ---- symulacja --------------------------------------------------------------------------
    def step(self):
        now = time.monotonic()
        dt = min(now - self.last_step, 0.1)
        self.last_step = now
        self.step_walk(now, dt)
        self.step_arms(now, dt)
        self.tick_count += 1
        if not self.get_parameter('pause_lowstate').value:
            self.publish_lowstate()
        if self.tick_count % 5 == 0:
            self.publish_ground_truth()

    def step_walk(self, now, dt):
        target = self.v_cmd if (self.fsm == FSM_WALK and now < self.v_until) else (0.0, 0.0, 0.0)
        alpha = min(1.0, dt / self.vel_tau)          # robot nie rusza w miejscu: opóźnienie 1. rzędu
        for i in range(3):
            self.v_act[i] += (target[i] - self.v_act[i]) * alpha
        vx, vy, wz = self.v_act
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        self.x += (vx * c - vy * s) * dt
        self.y += (vx * s + vy * c) * dt
        self.yaw = wrap_angle(self.yaw + wz * dt)
        self.yaw_drift += self.imu_yaw_bias * dt

    def step_arms(self, now, dt):
        if self.arm_time is not None and self.weight > 0 and now - self.arm_time > ARM_STALE_S \
                and not self.arm_stale_warned:
            self.get_logger().warning(
                f'brak /arm_sdk od {ARM_STALE_S} s przy wadze {self.weight:.2f}: górna część ciała zostaje '
                'w ostatniej pozie (jak w dokumentacji) - program nie oddał sterowania!')
            self.arm_stale_warned = True
        if self.inject_fault_s > 0 and self.arm_active_since is not None and not self.fault \
                and now - self.arm_active_since > self.inject_fault_s:
            self.fault = True
            self.get_logger().warning('makieta: wstrzykuję błąd motorstate=1 w right_elbow_joint (slot 25)')
        max_step = self.arm_max_speed * dt
        w = self.weight
        for i in range(len(ARM_JOINTS)):
            target = w * self.q_cmd[i] + (1.0 - w) * self.q_default[i]
            step = clamp(target - self.q[i], -max_step, max_step)
            self.q[i] += step
            self.dq[i] = step / dt if dt > 0 else 0.0

    def publish_lowstate(self):
        st = self.state
        noise = random.gauss(0.0, self.imu_noise) if self.imu_noise > 0 else 0.0
        imu_yaw = wrap_angle(self.yaw + self.imu_yaw0 + self.yaw_drift + noise)
        qx, qy, qz, qw = yaw_to_quat(imu_yaw)
        st.tick = (self.tick_count * 10) & 0xFFFFFFFF            # ms przy 100 Hz
        st.imu_state.rpy = [0.0, 0.0, imu_yaw]
        st.imu_state.quaternion = [qw, qx, qy, qz]               # Unitree: kolejność w, x, y, z
        st.imu_state.gyroscope = [0.0, 0.0, self.v_act[2] + self.imu_yaw_bias]
        st.imu_state.accelerometer = [0.0, 0.0, 9.81]
        for i, j in enumerate(ARM_JOINTS):
            m = st.motor_state[j.slot]
            m.q, m.dq = self.q[i], self.dq[i]
            m.motorstate = 1 if (self.fault and j.slot == 25) else 0
        self.state_pub.publish(st)

    def publish_ground_truth(self):
        odom = Odometry()
        odom.header.stamp = self.get_clock().now().to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        odom.pose.pose.position.x, odom.pose.pose.position.y = self.x, self.y
        qx, qy, qz, qw = yaw_to_quat(self.yaw)
        odom.pose.pose.orientation.z, odom.pose.pose.orientation.w = qz, qw
        odom.twist.twist.linear.x, odom.twist.twist.linear.y = self.v_act[0], self.v_act[1]
        odom.twist.twist.angular.z = self.v_act[2]
        self.gt_pub.publish(odom)


def main(args=None):
    rclpy.init(args=args)
    node = R1Mock()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
