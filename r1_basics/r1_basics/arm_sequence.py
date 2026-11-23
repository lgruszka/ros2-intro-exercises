#!/usr/bin/env python3
"""arm_sequence - ręce, talia (yaw) i głowa R1 przez arm_sdk (unitree_hg/LowCmd na /arm_sdk, 100 Hz).

Przebieg (docs/r1_plan.md §5, wzorzec: unitree_sdk2 example/r1/high_level/r1_arm_sdk_dds_example.cpp):
  1. czekaj na /lowstate, zasiej cele zmierzonymi pozycjami 13 przegubów arm_sdk (motor_state[slot].q),
  2. rampa wagi mode_pr 0 -> 100 przez ramp_s, cele = zmierzona poza (ręce się nie ruszają),
  3. interpolacja do pozy startowej, machanie prawą ręką x3, głowa w lewo/prawo, skinienie, talia,
  4. powrót do zmierzonej pozy, rampa wagi 100 -> 0 przez ramp_s, koniec programu.
Bezpieczeństwo: cele przycięte do 70% zakresu URDF, prędkość celu <= max_joint_speed (1 rad/s),
nieświeży /lowstate (> 0.2 s) albo motorstate != 0 -> natychmiastowe oddanie rampą,
Ctrl+C / wyjątek -> oddanie rampą w `finally` (handler sygnałów rclpy wyłączony).
ROBOT MUSI STAĆ (FSM 4, na stojaku albo w ramie). arm_sdk w trybie chodu 811 przełącza robota
w FSM 816 i blokuje chód (zgłoszenia społeczności) - dlatego węzeł najpierw pyta o FSM.
"""
import json
import time
import traceback

from r1_basics.arm_sdk import ARM_JOINTS, build_sequence, effective_limits, hg_lowcmd_crc, weight_to_mode_pr
from r1_basics.params import declare_float
from r1_basics.sport_api import (API_GET_FSM_ID, fsm_name, FSM_WALK, make_request, REQUEST_TOPIC,
                                 RESPONSE_TOPIC)
from r1_basics.util import clamp
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from rclpy.task import Future
from unitree_api.msg import Request, Response
from unitree_hg.msg import LowCmd, LowState

FINAL_ZERO_MSGS = 10        # po oddaniu jeszcze 10 wiadomości z wagą 0 (0.1 s przy 100 Hz)
FSM_QUERY_TIMEOUT_S = 2.0


class ArmSequence(Node):
    def __init__(self):
        super().__init__('arm_sequence')
        self.ramp_s = max(declare_float(self, 'ramp_s', 1.0), 0.1)
        self.move_s = max(declare_float(self, 'move_s', 2.0), 0.2)
        self.rate_hz = clamp(declare_float(self, 'rate_hz', 100.0), 20.0, 500.0)
        self.max_speed = clamp(declare_float(self, 'max_joint_speed', 1.0), 0.05, 1.0)
        self.lowstate_timeout_s = declare_float(self, 'lowstate_timeout_s', 0.2)
        self.waves = int(self.declare_parameter('waves', 3).value)
        self.interp = self.declare_parameter('interp', 'cosine').value
        self.check_fsm = bool(self.declare_parameter('check_fsm', True).value)
        if self.interp not in ('cosine', 'linear'):
            self.get_logger().warning(f'interp={self.interp!r} nieznane - używam cosine')
            self.interp = 'cosine'

        self.arm_pub = self.create_publisher(LowCmd, '/arm_sdk', 10)
        self.create_subscription(LowState, '/lowstate', self.on_lowstate, qos_profile_sensor_data)
        self.req_pub = self.create_publisher(Request, REQUEST_TOPIC, 10)
        self.create_subscription(Response, RESPONSE_TOPIC, self.on_response, qos_profile_sensor_data)

        self.cmd = LowCmd()
        for j in ARM_JOINTS:
            m = self.cmd.motor_cmd[j.slot]
            m.kp, m.kd, m.dq, m.tau = j.kp, j.kd, 0.0, 0.0
        self.lowstate = None
        self.lowstate_time = None
        self.state = 'FSM' if self.check_fsm else 'WAIT'
        self.fsm_req_id = None
        self.fsm_deadline = None
        self.fsm_match_time = None
        self.seed = None
        self.q_cmd = None
        self.limits = None
        self.weight = 0.0
        self.segments = []
        self.seg_index = 0
        self.seg_start = 0.0
        self.release_from = None     # (waga startowa, czas startu, czas trwania) oddania awaryjnego
        self.zero_left = FINAL_ZERO_MSGS
        self.exit_code = 0
        self.max_step = 0.0          # największa zmiana celu między wiadomościami [rad]
        self.done = Future()
        self.dt = 1.0 / self.rate_hz
        self.create_timer(self.dt, self.tick)
        self.get_logger().info(
            f'arm_sequence: /lowstate -> /arm_sdk, {self.rate_hz:.0f} Hz, ramp_s {self.ramp_s}, '
            f'move_s {self.move_s}, max {self.max_speed} rad/s, interp {self.interp}. ROBOT MUSI STAĆ (FSM 4)!')

    # ---- wejścia -------------------------------------------------------------------------
    def on_lowstate(self, msg):
        self.lowstate = msg
        self.lowstate_time = time.monotonic()

    def on_response(self, msg):
        if self.state != 'FSM' or msg.header.identity.id != self.fsm_req_id:
            return
        fsm = None
        if msg.header.status.code == 0:
            try:
                fsm = json.loads(msg.data).get('data')
            except (ValueError, AttributeError):
                fsm = None
        if fsm == FSM_WALK:
            self.get_logger().error(
                'robot jest w trybie chodu (FSM 811). arm_sdk przełączy go w 816 i zablokuje chód. '
                'Postaw robota (FSM 4: `ros2 run r1_basics sport_cli stand` albo pilot) i uruchom ponownie.')
            self.exit_code = 3
            self.done.set_result(True)
            return
        self.get_logger().info(f'FSM = {fsm} ({fsm_name(fsm)}) - zaczynam' if fsm is not None
                               else f'FSM nieznany (kod {msg.header.status.code}) - upewnij się, że robot stoi')
        self.state = 'WAIT'

    # ---- pętla 100 Hz -----------------------------------------------------------------------
    def tick(self):
        if self.done.done():
            return
        now = time.monotonic()
        if self.state == 'FSM':
            self.query_fsm(now)
            return
        if self.state == 'WAIT':
            if self.lowstate is None:
                self.get_logger().info('czekam na /lowstate...', throttle_duration_sec=1.0)
                return
            self.start_sequence(now)

        if self.state == 'RUN':
            reason = self.safety_problem(now)
            if reason:
                self.start_release(now, reason)
            else:
                q_des, self.weight = self.sample(now)
                if q_des is None:
                    self.state = 'FINISH'
                else:
                    self.q_cmd = self.limit(q_des)
        if self.state == 'RELEASE':
            w0, t0, duration = self.release_from
            self.weight = max(0.0, w0 * (1.0 - (now - t0) / duration))
            if self.weight <= 0.0:
                self.state = 'FINISH'
        if self.state == 'FINISH':
            self.weight = 0.0
            self.zero_left -= 1
            if self.zero_left <= 0:
                self.publish()
                self.get_logger().info(
                    f'koniec: waga 0, sterowanie oddane (max zmiana celu {self.max_step:.4f} rad '
                    f'na wiadomość = {self.max_step * self.rate_hz:.2f} rad/s)')
                self.done.set_result(True)
                return
        self.publish()

    def query_fsm(self, now):
        if self.fsm_deadline is None:
            self.fsm_deadline = now + FSM_QUERY_TIMEOUT_S
        if self.fsm_req_id is None and self.req_pub.get_subscription_count() > 0:
            if self.fsm_match_time is None:
                self.fsm_match_time = now     # DDS dopasowane - chwila na subskrypcję odpowiedzi
            elif now - self.fsm_match_time > 0.3:
                req = make_request(API_GET_FSM_ID)
                self.fsm_req_id = req.header.identity.id
                self.fsm_deadline = now + FSM_QUERY_TIMEOUT_S
                self.req_pub.publish(req)
                return
        if self.fsm_deadline is not None and now > self.fsm_deadline:
            self.get_logger().warning(
                'brak odpowiedzi na GetFsmId (7001) - nie wiem, czy robot stoi. Kontynuuję: '
                'upewnij się sam, że robot jest w FSM 4 (stoi), a nie w chodzie 811.')
            self.state = 'WAIT'

    def start_sequence(self, now):
        self.seed = [float(self.lowstate.motor_state[j.slot].q) for j in ARM_JOINTS]
        self.q_cmd = list(self.seed)
        self.limits = effective_limits(self.seed)
        self.segments = build_sequence(self.seed, self.ramp_s, self.move_s, self.max_speed,
                                       self.waves, self.interp)
        total = sum(s.duration for s in self.segments)
        self.get_logger().info('zasiane cele z /lowstate: ' + ', '.join(
            f'{j.name.replace("_joint", "")}={q:+.2f}' for j, q in zip(ARM_JOINTS, self.seed)))
        self.get_logger().info(f'sekwencja: {len(self.segments)} odcinków, {total:.1f} s')
        self.seg_index = 0
        self.seg_start = now
        self.state = 'RUN'
        self.get_logger().info(f'[1/{len(self.segments)}] {self.segments[0].name}')

    def sample(self, now):
        """Cele i waga z bieżącego odcinka planu; None po ostatnim odcinku."""
        while self.seg_index < len(self.segments):
            seg = self.segments[self.seg_index]
            t = now - self.seg_start
            if t <= seg.duration:
                return seg.fn(t)
            self.seg_start += seg.duration
            self.seg_index += 1
            if self.seg_index < len(self.segments):
                self.get_logger().info(
                    f'[{self.seg_index + 1}/{len(self.segments)}] {self.segments[self.seg_index].name}')
        last = self.segments[-1].fn(self.segments[-1].duration)
        self.q_cmd = self.limit(last[0])
        return None, 0.0

    def limit(self, q_des):
        """Przytnij cele do limitów i ogranicz prędkość celu do max_speed."""
        out = []
        max_delta = self.max_speed * self.dt
        for q, q_prev, (low, high) in zip(q_des, self.q_cmd, self.limits):
            q = clamp(q, low, high)
            step = clamp(q - q_prev, -max_delta, max_delta)
            self.max_step = max(self.max_step, abs(step))
            out.append(q_prev + step)
        return out

    def safety_problem(self, now):
        age = now - self.lowstate_time
        if age > self.lowstate_timeout_s:
            return f'/lowstate nieświeże ({age:.2f} s > {self.lowstate_timeout_s} s)'
        for j in ARM_JOINTS:
            state = int(self.lowstate.motor_state[j.slot].motorstate)
            if state != 0:
                return f'motorstate={state} w {j.name} (slot {j.slot})'
        return None

    def start_release(self, now, reason):
        """Natychmiastowe oddanie: waga z bieżącej do 0 w tempie rampy, cele = ostatnie wysłane."""
        self.get_logger().error(f'STOP: {reason} -> oddaję sterowanie rampą wagi')
        self.exit_code = 1
        self.release_from = (self.weight, now, max(self.ramp_s * self.weight, self.dt))
        self.state = 'RELEASE'

    def publish(self):
        for j, q in zip(ARM_JOINTS, self.q_cmd):
            self.cmd.motor_cmd[j.slot].q = float(q)
        self.cmd.mode_pr = weight_to_mode_pr(self.weight)
        self.cmd.crc = 0
        self.cmd.crc = hg_lowcmd_crc(self.cmd)
        self.arm_pub.publish(self.cmd)

    def emergency_release(self):
        """Blokujące oddanie po Ctrl+C albo wyjątku (pętla poza executorem, publikacja wprost)."""
        if self.q_cmd is None or self.done.done() or self.weight <= 0.0 and self.state != 'RUN':
            return
        w0 = self.weight
        duration = max(self.ramp_s * w0, self.dt)
        self.get_logger().warning(f'przerwanie: oddaję sterowanie (waga {w0:.2f} -> 0 w {duration:.2f} s)')
        t0 = time.monotonic()
        while True:
            self.weight = max(0.0, w0 * (1.0 - (time.monotonic() - t0) / duration))
            self.publish()
            if self.weight <= 0.0:
                break
            time.sleep(self.dt)
        for _ in range(FINAL_ZERO_MSGS):
            self.publish()
            time.sleep(self.dt)
        self.get_logger().info('sterowanie oddane (waga 0)')


def main(args=None):
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = ArmSequence()
    try:
        rclpy.spin_until_future_complete(node, node.done)
    except KeyboardInterrupt:
        pass                  # Ctrl+C = zwykłe przerwanie; kod 1 tylko po awarii (lowstate, motorstate)
    except Exception:  # noqa: BLE001 - błąd w programie: najpierw oddaj sterowanie (finally)
        traceback.print_exc()
        node.exit_code = 1
    finally:
        try:
            node.emergency_release()
        except Exception as exc:  # noqa: BLE001
            print(f'arm_sequence: oddanie sterowania nie powiodło się: {exc} - UŻYJ PILOTA/E-STOP')
            node.exit_code = 1
        code = node.exit_code
        node.destroy_node()
        rclpy.try_shutdown()
    return code


if __name__ == '__main__':
    raise SystemExit(main())
