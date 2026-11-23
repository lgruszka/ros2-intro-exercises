#!/usr/bin/env python3
"""cmd_vel_bridge - most /cmd_vel (Twist) -> sport API R1 (SetVelocity 7105 na /api/sport/request).

Co tick (rate_hz) most wysyła SetVelocity z krótkim `duration_s`: robot idzie tą prędkością przez
duration_s od ostatniej komendy, potem sam staje. Ponawianie co 0.1 s + krótki duration = watchdog
po stronie robota (gdy most padnie, robot staje po duration_s).

Bezpieczeństwo: limity prędkości (max_vx, max_vy, max_wz), cisza na /cmd_vel > cmd_timeout_s -> [0,0,0],
/r1/estop True -> [0,0,0] do odwołania (False), Ctrl+C -> StopMove przed wyjściem.
Most NIE stawia robota i nie zmienia FSM - to robisz pilotem (R2+A) albo, z robotem w ramie i w FSM 4,
`ros2 run r1_basics sport_cli start`.
"""
import time

from geometry_msgs.msg import Twist
from r1_basics.params import declare_float
from r1_basics.sport_api import (API_SET_VELOCITY, CODE_127_REPORTED, make_request, REQUEST_TOPIC,
                                 RESPONSE_TOPIC, velocity_parameter)
from r1_basics.util import clamp
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import Bool
from unitree_api.msg import Request, Response

STOP_REPEAT = 3          # ile razy wysłać [0,0,0] po przejściu w spoczynek (potem most milknie)
PENDING_MAX_AGE_S = 2.0  # po tylu sekundach przestajemy czekać na odpowiedź do danego id


class R1CmdVelBridge(Node):
    def __init__(self):
        super().__init__('cmd_vel_bridge')
        self.max_vx = declare_float(self, 'max_vx', 0.3)
        self.max_vy = declare_float(self, 'max_vy', 0.2)
        self.max_wz = declare_float(self, 'max_wz', 0.5)
        self.duration_s = declare_float(self, 'duration_s', 0.5)
        rate_hz = declare_float(self, 'rate_hz', 10.0)
        self.cmd_timeout_s = declare_float(self, 'cmd_timeout_s', 0.5)

        self.req_pub = self.create_publisher(Request, REQUEST_TOPIC, 10)
        self.sent_pub = self.create_publisher(Twist, '/r1/cmd_vel_sent', 10)
        self.create_subscription(Twist, '/cmd_vel', self.on_cmd_vel, 10)
        self.create_subscription(Bool, '/r1/estop', self.on_estop, 10)
        # best effort przyjmie odpowiedzi i od nadawcy reliable, i best effort
        self.create_subscription(Response, RESPONSE_TOPIC, self.on_response, qos_profile_sensor_data)

        self.last_cmd = Twist()
        self.last_cmd_time = None
        self.estop = False
        self.moving = False
        self.stop_left = 0
        self.pending = {}          # id żądania -> (api_id, czas wysłania)
        self.sent_count = 0
        self.response_count = 0
        self.warned_127 = False
        self.warned_no_response = False

        self.create_timer(1.0 / max(rate_hz, 1.0), self.tick)
        self.create_timer(5.0, self.check_link)
        self.get_logger().info(
            f'cmd_vel_bridge: /cmd_vel -> {REQUEST_TOPIC} (SetVelocity {API_SET_VELOCITY}), '
            f'limity vx {self.max_vx} vy {self.max_vy} wz {self.max_wz}, duration {self.duration_s} s, '
            f'{rate_hz:.0f} Hz, timeout {self.cmd_timeout_s} s')

    def on_cmd_vel(self, msg):
        self.last_cmd = msg
        self.last_cmd_time = self.get_clock().now()

    def on_estop(self, msg):
        if msg.data and not self.estop:
            self.get_logger().warning('E-STOP (/r1/estop = true): wysyłam [0, 0, 0] do odwołania')
            self.send_velocity(0.0, 0.0, 0.0, self.duration_s)
        elif not msg.data and self.estop:
            self.get_logger().info('E-STOP zwolniony (/r1/estop = false)')
        self.estop = bool(msg.data)

    def tick(self):
        """Co 1/rate_hz: wybierz prędkość (E-Stop / cisza / komenda po limitach) i wyślij 7105."""
        vx = vy = wz = 0.0
        send = False
        if self.estop:
            send = True                                   # E-Stop: aktywnie trzymamy zero
        elif self.last_cmd_time is not None and self.cmd_age() <= self.cmd_timeout_s:
            vx = clamp(self.last_cmd.linear.x, -self.max_vx, self.max_vx)
            vy = clamp(self.last_cmd.linear.y, -self.max_vy, self.max_vy)
            wz = clamp(self.last_cmd.angular.z, -self.max_wz, self.max_wz)
            send = True
            if not self.moving and (vx or vy or wz):
                self.get_logger().info(f'ruch: vx={vx:.2f} vy={vy:.2f} wz={wz:.2f}')
                self.moving = True
        else:
            if self.moving:
                self.get_logger().info(
                    f'cisza na /cmd_vel > {self.cmd_timeout_s} s -> stop [0, 0, 0]')
                self.moving = False
                self.stop_left = STOP_REPEAT
            if self.stop_left > 0:
                self.stop_left -= 1
                send = True

        if send:
            self.send_velocity(vx, vy, wz, self.duration_s)
        sent = Twist()
        sent.linear.x, sent.linear.y, sent.angular.z = float(vx), float(vy), float(wz)
        self.sent_pub.publish(sent)

    def cmd_age(self):
        return (self.get_clock().now() - self.last_cmd_time).nanoseconds * 1e-9

    def send_velocity(self, vx, vy, wz, duration):
        req = make_request(API_SET_VELOCITY, velocity_parameter(vx, vy, wz, duration))
        self.req_pub.publish(req)
        self.pending[req.header.identity.id] = (API_SET_VELOCITY, time.monotonic())
        self.sent_count += 1

    def send_stop(self):
        """Wyślij StopMove, czyli SetVelocity(0, 0, 0) z duration 1 s (jak StopMove w unitree_sdk2)."""
        for _ in range(STOP_REPEAT):
            self.send_velocity(0.0, 0.0, 0.0, 1.0)
        time.sleep(0.2)   # daj DDS chwilę na wysłanie, zanim proces zniknie

    def on_response(self, msg):
        entry = self.pending.pop(msg.header.identity.id, None)
        if entry is None:
            return                                        # odpowiedź na cudze żądanie
        self.response_count += 1
        api_id, code = entry[0], msg.header.status.code
        if code == 0:
            return
        if code == CODE_127_REPORTED and api_id == API_SET_VELOCITY:
            if not self.warned_127:
                self.get_logger().warning(
                    'SetVelocity zwraca kod 127 - znany ze zgłoszeń (xr_teleoperate #319, sdk2_python #182): '
                    'u części robotów w 811 i tak idzie, u innych nie. Nie traktuję tego jako błąd; patrz, '
                    'czy robot się rusza. (ten komunikat tylko raz)')
                self.warned_127 = True
            return
        self.get_logger().warning(
            f'sport API: api_id {api_id} -> kod {code}, data={msg.data!r}', throttle_duration_sec=2.0)

    def check_link(self):
        """Co 5 s: czy ktoś słucha /api/sport/request i czy przychodzą odpowiedzi."""
        now = time.monotonic()
        self.pending = {k: v for k, v in self.pending.items() if now - v[1] < PENDING_MAX_AGE_S}
        if self.req_pub.get_subscription_count() == 0:
            self.get_logger().warning(
                f'nikt nie subskrybuje {REQUEST_TOPIC} - robot (albo r1_mock) niewidoczny? '
                'Sprawdź kabel, RMW_IMPLEMENTATION, CYCLONEDDS_URI i ROS_DOMAIN_ID')
        elif self.sent_count and not self.response_count and not self.warned_no_response:
            self.get_logger().warning(
                f'brak odpowiedzi na {RESPONSE_TOPIC} (wysłano {self.sent_count} żądań). '
                'Robot może nie odpowiadać na 7105 - patrz, czy reaguje ruchem.')
            self.warned_no_response = True


def main(args=None):
    """Start mostu; Ctrl+C wysyła jeszcze StopMove (handler sygnałów rclpy wyłączony)."""
    # Bez handlera rclpy Ctrl+C to zwykły KeyboardInterrupt, a kontekst ROS jeszcze działa, więc
    # StopMove zdąży wyjść (wzorzec z mostu Go2). Zabity proces (SIGKILL) nie wyśle nic - wtedy
    # robot stanie sam po duration_s, bo most przestał ponawiać komendę.
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = R1CmdVelBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.send_stop()
            node.get_logger().info('koniec: wysłano StopMove (SetVelocity 0, 0, 0)')
        except Exception as exc:  # noqa: BLE001 - przy wyjściu nie ma już kogo ratować
            print(f'cmd_vel_bridge: nie udało się wysłać StopMove: {exc}')
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
