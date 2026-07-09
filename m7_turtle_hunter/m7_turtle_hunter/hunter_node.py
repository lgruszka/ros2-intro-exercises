import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from turtlesim.msg import Pose
from turtlesim.srv import Kill

CAPTURE_DIST = 0.5
KILL_COOLDOWN_SEC = 1.5      # po /kill ignorujemy pose tego żółwia
PREY_NAMES = ['prey1', 'prey2', 'prey3']


class HunterNode(Node):
    def __init__(self):
        super().__init__('hunter_node')

        self.declare_parameter('kp_linear', 1.5)
        self.declare_parameter('kp_angular', 6.0)
        self.declare_parameter('max_linear', 2.0)

        self.hunter_pose = None
        self.prey_poses = {}
        # recently_killed: name -> czas kill'a. Dzięki temu unikamy podwójnego
        # capture, gdy /kill leci async a w międzyczasie subscription dla tej
        # ofiary dostarcza jeszcze jeden pose (race condition w turtlesim).
        self.recently_killed = {}
        self.score = 0

        self.create_subscription(
            Pose, '/turtle1/pose', self.on_hunter_pose, 10)

        for name in PREY_NAMES:
            self.create_subscription(
                Pose, f'/{name}/pose',
                lambda msg, n=name: self.on_prey_pose(n, msg), 10)

        self.cmd_pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        self.capture_pub = self.create_publisher(String, '/captures', 10)
        self.kill_cli = self.create_client(Kill, '/kill')

        self.create_timer(0.1, self.tick)
        self.create_timer(0.5, self._expire_killed)
        self.get_logger().info('Hunter ready, poluję na 3 żółwie')

    def on_hunter_pose(self, msg):
        self.hunter_pose = msg

    def on_prey_pose(self, name, msg):
        if name in self.recently_killed:
            return                      # ignoruj „duchy" tuż po /kill
        self.prey_poses[name] = msg

    def _expire_killed(self):
        now = self.get_clock().now()
        expired = [n for n, t in self.recently_killed.items()
                   if (now - t).nanoseconds * 1e-9 > KILL_COOLDOWN_SEC]
        for n in expired:
            del self.recently_killed[n]

    def tick(self):
        if not self.hunter_pose or not self.prey_poses:
            return

        h = self.hunter_pose
        nearest_name, nearest = min(
            self.prey_poses.items(),
            key=lambda kv: math.hypot(kv[1].x - h.x, kv[1].y - h.y))

        dx = nearest.x - h.x
        dy = nearest.y - h.y
        dist = math.hypot(dx, dy)

        if dist < CAPTURE_DIST:
            self.capture(nearest_name)
            return

        target_angle = math.atan2(dy, dx)
        angle_err = self._angle_diff(target_angle, h.theta)

        kp_lin = self.get_parameter('kp_linear').value
        kp_ang = self.get_parameter('kp_angular').value
        max_lin = self.get_parameter('max_linear').value

        cmd = Twist()
        cmd.linear.x = min(kp_lin * dist, max_lin)
        cmd.angular.z = kp_ang * angle_err
        self.cmd_pub.publish(cmd)

    def capture(self, name):
        self.score += 1
        self.get_logger().info(f'Złapany {name}! Score: {self.score}')
        req = Kill.Request()
        req.name = name
        self.kill_cli.call_async(req)
        self.prey_poses.pop(name, None)
        self.recently_killed[name] = self.get_clock().now()
        msg = String()
        msg.data = name
        self.capture_pub.publish(msg)

    @staticmethod
    def _angle_diff(target, current):
        diff = target - current
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi
        return diff


def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(HunterNode())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
