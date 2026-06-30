"""cmd_vel arbiter (Go2 variant — bez carry_mode bo Go2 nie ma rąk).

Inputs (priority order, top wins):
  1. /cmd_vel_estop            - if any source latched true, output zero (no override).
  2. freeze flag (service)     - mission asks loco to hold still.
  3. /cmd_vel_dock             - dock action while servoing.
  4. /cmd_vel_retreat          - retreat action while backing off.
  5. /cmd_vel_nav              - nav2 controller output.

Output:
  /cmd_vel  -> consumed by unitree_cmd_vel_bridge_node.

Inactivity:
  - If no fresh input from any source for `cmd_timeout_s`, publishes zero.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy,
)
from std_msgs.msg import Bool
from geometry_msgs.msg import Twist

from go2_msgs.srv import SetFreeze

# Latched profile so a late-joining arbiter still sees the last e-stop value.
_ESTOP_QOS = QoSProfile(
    depth=1, reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL, history=HistoryPolicy.KEEP_LAST,
)


@dataclass
class _Source:
    msg: Optional[Twist] = None
    last_stamp_ns: int = 0


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _floor(v: float, min_v: float) -> float:
    """Boost |v| to min_v while keeping sign — but only when v is intentionally
    non-zero. v=0 stays 0 (freeze / no source). Used for hardware that has a
    minimum velocity threshold (G1 sport API ~0.11 m/s below which the firmware
    refuses to step). Set min_v=0.0 to disable."""
    import math
    if min_v <= 0.0:
        return v
    if abs(v) < 1e-6:
        return 0.0
    return math.copysign(max(abs(v), min_v), v)


class CmdVelArbiter(Node):
    def __init__(self) -> None:
        super().__init__('cmd_vel_arbiter')

        self.declare_parameter('output_topic', '/cmd_vel')
        self.declare_parameter('publish_rate_hz', 20.0)
        self.declare_parameter('cmd_timeout_s', 0.4)
        # When nav2 owns /cmd_vel directly, set this False so arbiter still
        # hosts /safety/set_freeze service but doesn't fight nav2 on /cmd_vel.
        # Dock/retreat then publish straight to /cmd_vel via their own
        # cmd_vel_topic params.
        self.declare_parameter('enable_publish', True)
        # Velocity caps (Go2 sport API — może iść szybciej niż G1)
        self.declare_parameter('max_vx', 1.0)
        self.declare_parameter('max_vy', 0.5)
        self.declare_parameter('max_vyaw', 1.0)
        # Minimum-velocity floor (hardware threshold). Go2 ma niższy floor
        # niż G1 (~0.05 m/s vs 0.12). Set 0.0 to disable.
        self.declare_parameter('min_vx_threshold', 0.0)
        self.declare_parameter('min_vy_threshold', 0.0)
        self.declare_parameter('min_vyaw_threshold', 0.0)
        # Topik wejścia nav2. Domyślnie /cmd_vel_nav (surowy output controllera —
        # zachowanie historyczne). Ustaw /cmd_vel_smoothed by wejść przez nav2
        # velocity_smoother (accel-limited) → mniej szarpane komendy obrotu, mniej
        # oscylacji. (velocity_smoother subskrybuje cmd_vel_nav, publikuje
        # cmd_vel_smoothed — inaczej jego wygładzanie jest OMIJANE.)
        self.declare_parameter('nav_topic', '/cmd_vel_nav')

        self._timeout_ns = int(float(self.get_parameter('cmd_timeout_s').value) * 1e9)
        self._max = (
            float(self.get_parameter('max_vx').value),
            float(self.get_parameter('max_vy').value),
            float(self.get_parameter('max_vyaw').value),
        )
        self._min_floor = (
            float(self.get_parameter('min_vx_threshold').value),
            float(self.get_parameter('min_vy_threshold').value),
            float(self.get_parameter('min_vyaw_threshold').value),
        )

        # State.
        self._lock = threading.Lock()
        self._dock = _Source()
        self._retreat = _Source()
        self._nav = _Source()
        self._estop = False
        self._freeze = False

        # IO.
        self._pub = self.create_publisher(
            Twist, str(self.get_parameter('output_topic').value), 10,
        )
        self.create_subscription(Twist, '/cmd_vel_dock', self._on_dock, 10)
        self.create_subscription(Twist, '/cmd_vel_retreat', self._on_retreat, 10)
        _nav_topic = str(self.get_parameter('nav_topic').value)
        self.create_subscription(Twist, _nav_topic, self._on_nav, 10)
        self.get_logger().info(f'arbiter nav input: {_nav_topic}')
        self.create_subscription(Bool, '/cmd_vel_estop', self._on_estop, _ESTOP_QOS)
        self.create_service(SetFreeze, '/safety/set_freeze', self._on_set_freeze)

        rate_hz = max(1.0, float(self.get_parameter('publish_rate_hz').value))
        self.create_timer(1.0 / rate_hz, self._tick)
        self.get_logger().info('cmd_vel_arbiter ready')

    # ---------- callbacks ----------

    def _stamp(self, src: _Source, msg: Twist) -> None:
        with self._lock:
            src.msg = msg
            src.last_stamp_ns = self.get_clock().now().nanoseconds

    def _on_dock(self, msg: Twist) -> None: self._stamp(self._dock, msg)
    def _on_retreat(self, msg: Twist) -> None: self._stamp(self._retreat, msg)
    def _on_nav(self, msg: Twist) -> None: self._stamp(self._nav, msg)

    def _on_estop(self, msg: Bool) -> None:
        with self._lock:
            self._estop = bool(msg.data)
        if msg.data:
            self.get_logger().warn('E-STOP latched -> zero cmd_vel')

    def _on_set_freeze(self, request: SetFreeze.Request, response: SetFreeze.Response):
        with self._lock:
            self._freeze = bool(request.freeze)
        response.success = True
        response.message = f'freeze={self._freeze}'
        self.get_logger().info(response.message)
        return response

    # ---------- selection ----------

    def _is_fresh(self, src: _Source, now_ns: int) -> bool:
        return src.msg is not None and (now_ns - src.last_stamp_ns) <= self._timeout_ns

    def _select(self, now_ns: int) -> Optional[Twist]:
        if self._estop or self._freeze:
            return Twist()
        if self._is_fresh(self._dock, now_ns):
            return self._dock.msg
        if self._is_fresh(self._retreat, now_ns):
            return self._retreat.msg
        if self._is_fresh(self._nav, now_ns):
            return self._nav.msg
        return None

    def _apply_caps(self, cmd: Twist) -> Twist:
        vx_max, vy_max, vyaw_max = self._max
        vx_min, vy_min, vyaw_min = self._min_floor
        out = Twist()
        out.linear.x = _floor(_clamp(cmd.linear.x, -vx_max, vx_max), vx_min)
        out.linear.y = _floor(_clamp(cmd.linear.y, -vy_max, vy_max), vy_min)
        out.angular.z = _floor(_clamp(cmd.angular.z, -vyaw_max, vyaw_max), vyaw_min)
        return out

    # ---------- main loop ----------

    def _tick(self) -> None:
        if not bool(self.get_parameter('enable_publish').value):
            return  # service-only mode (Faza 1.5+ where nav2 owns /cmd_vel)
        now_ns = self.get_clock().now().nanoseconds
        with self._lock:
            chosen = self._select(now_ns)
        if chosen is None:
            self._pub.publish(Twist())
            return
        self._pub.publish(self._apply_caps(chosen))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = CmdVelArbiter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
