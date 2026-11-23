#!/usr/bin/env python3
"""goto_point - dojazd R1 do punktu (x, y) regulatorem P (robot holonomiczny: idzie też bokiem).

Cel: parametry goal_x/goal_y albo /goal_pose (RViz „2D Goal Pose"; bierzemy x, y, zakładamy ramę odom).
Co 1/rate_hz: błąd pozycji -> rama robota -> vx, vy = k_lin * błąd (wektor przycięty do max_v),
wz = k_yaw * kąt do celu (przycięty do max_wz) - robot obraca się przodem do celu.
W tolerancji `tol`: zero na /cmd_vel i „cel osiągnięty". Nieświeża odometria: zero i czekamy.
"""
import math

from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import Odometry
from r1_basics.params import declare_float
from r1_basics.util import holonomic_p_control, quat_to_yaw
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


class GotoPoint(Node):
    def __init__(self):
        super().__init__('goto_point')
        odom_topic = self.declare_parameter('odom_topic', '/r1/odom').value
        goal_x = declare_float(self, 'goal_x', float('nan'))
        goal_y = declare_float(self, 'goal_y', float('nan'))
        self.k_lin = declare_float(self, 'k_lin', 0.8)
        self.k_yaw = declare_float(self, 'k_yaw', 1.5)
        self.tol = declare_float(self, 'tol', 0.10)
        self.max_v = declare_float(self, 'max_v', 0.3)
        self.max_wz = declare_float(self, 'max_wz', 0.5)
        rate_hz = declare_float(self, 'rate_hz', 10.0)
        self.odom_timeout_s = declare_float(self, 'odom_timeout_s', 0.5)

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(Odometry, odom_topic, self.on_odom, 10)
        self.create_subscription(PoseStamped, '/goal_pose', self.on_goal, 10)

        self.pose = None            # (x, y, yaw)
        self.odom_time = None
        self.goal = None
        self.stale = False
        if not (math.isnan(goal_x) or math.isnan(goal_y)):
            self.set_goal(goal_x, goal_y, 'parametry')
        self.create_timer(1.0 / max(rate_hz, 1.0), self.tick)
        self.get_logger().info(
            f'goto_point: {odom_topic} -> /cmd_vel, k_lin {self.k_lin} k_yaw {self.k_yaw} tol {self.tol} m, '
            f'max_v {self.max_v} max_wz {self.max_wz}' + ('' if self.goal else '; czekam na /goal_pose'))

    def set_goal(self, x, y, source):
        self.goal = (x, y)
        self.get_logger().info(f'nowy cel ({source}): x={x:.2f} y={y:.2f}')

    def on_goal(self, msg):
        if msg.header.frame_id not in ('', 'odom'):
            self.get_logger().warning(
                f'cel w ramie {msg.header.frame_id!r} - traktuję x, y jak w odom (bez transformacji TF)')
        self.set_goal(msg.pose.position.x, msg.pose.position.y, '/goal_pose')

    def on_odom(self, msg):
        q = msg.pose.pose.orientation
        self.pose = (msg.pose.pose.position.x, msg.pose.pose.position.y, quat_to_yaw(q.x, q.y, q.z, q.w))
        self.odom_time = self.get_clock().now()

    def tick(self):
        if self.goal is None:
            return                           # bez celu milczymy - /cmd_vel wolny dla teleop
        if self.pose is None or (self.get_clock().now() - self.odom_time).nanoseconds * 1e-9 > self.odom_timeout_s:
            if not self.stale:
                self.cmd_pub.publish(Twist())
                self.get_logger().warning('odometria nieświeża albo brak - stop, czekam na odometrię')
                self.stale = True
            return
        if self.stale:
            self.get_logger().info('odometria wróciła - jadę dalej')
            self.stale = False

        x, y, yaw = self.pose
        dx, dy = self.goal[0] - x, self.goal[1] - y
        dist = math.hypot(dx, dy)
        if dist < self.tol:
            self.cmd_pub.publish(Twist())
            self.get_logger().info(
                f'cel osiągnięty: ({self.goal[0]:.2f}, {self.goal[1]:.2f}), odom ({x:.3f}, {y:.3f}), '
                f'błąd {dist:.3f} m')
            self.goal = None
            return
        vx, vy, wz = holonomic_p_control(dx, dy, yaw, self.k_lin, self.k_yaw, self.max_v, self.max_wz)
        cmd = Twist()
        cmd.linear.x, cmd.linear.y, cmd.angular.z = vx, vy, wz
        self.cmd_pub.publish(cmd)
        self.get_logger().info(
            f'do celu {dist:.2f} m: vx={vx:.2f} vy={vy:.2f} wz={wz:.2f}', throttle_duration_sec=1.0)


def main(args=None):
    rclpy.init(args=args)
    node = GotoPoint()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
