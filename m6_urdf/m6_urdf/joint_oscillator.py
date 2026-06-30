import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class JointOscillator(Node):
    """Publikuje /joint_states z sinusoidalnym ruchem stawów."""

    def __init__(self):
        super().__init__('joint_oscillator')
        self.pub = self.create_publisher(JointState, '/joint_states', 10)
        self.t0 = self.get_clock().now()
        self.create_timer(0.02, self.tick)   # 50 Hz
        self.get_logger().info('Joint oscillator pracuje, ruch sinusoidalny')

    def tick(self):
        t = (self.get_clock().now() - self.t0).nanoseconds * 1e-9
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = ['joint1', 'joint2', 'joint3']
        msg.position = [
            0.7 * math.sin(t * 0.6),
            0.5 * math.sin(t * 0.9 + 1.0),
            0.6 * math.sin(t * 1.2 + 2.0),
        ]
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(JointOscillator())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
