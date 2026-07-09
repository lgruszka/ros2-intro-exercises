import math

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from geometry_msgs.msg import Twist
from turtlesim.msg import Pose

ARENA_CX, ARENA_CY = 5.5, 5.5
SCALE = 3.0


class Dancer(Node):
    def __init__(self):
        super().__init__('dancer')
        self.declare_parameter('turtle_name', 'turtle1')
        self.declare_parameter('phase_offset', 0.0)
        self.declare_parameter('kp_lin', 4.0)
        self.declare_parameter('kp_ang', 8.0)

        name = self.get_parameter('turtle_name').value
        self.offset = self.get_parameter('phase_offset').value
        self.phase = 0.0
        self.pose = None

        self.create_subscription(Float64, '/choreo/phase', self.on_phase, 10)
        self.create_subscription(Pose, f'/{name}/pose', self.on_pose, 10)
        self.cmd_pub = self.create_publisher(Twist, f'/{name}/cmd_vel', 10)
        self.create_timer(0.05, self.tick)
        self.get_logger().info(f'Dancer {name} z offset {self.offset:.2f}')

    def on_phase(self, msg):
        self.phase = msg.data

    def on_pose(self, msg):
        self.pose = msg

    def target(self):
        t = self.phase + self.offset
        denom = 1 + math.sin(t) ** 2
        x = SCALE * math.cos(t) / denom
        y = SCALE * math.sin(t) * math.cos(t) / denom
        return ARENA_CX + x, ARENA_CY + y

    def tick(self):
        if not self.pose:
            return
        tx, ty = self.target()
        dx, dy = tx - self.pose.x, ty - self.pose.y
        dist = math.hypot(dx, dy)
        target_ang = math.atan2(dy, dx)
        ang_err = target_ang - self.pose.theta
        while ang_err > math.pi:
            ang_err -= 2 * math.pi
        while ang_err < -math.pi:
            ang_err += 2 * math.pi

        kp_lin = self.get_parameter('kp_lin').value
        kp_ang = self.get_parameter('kp_ang').value

        cmd = Twist()
        cmd.linear.x = kp_lin * dist
        cmd.angular.z = kp_ang * ang_err
        self.cmd_pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(Dancer())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
