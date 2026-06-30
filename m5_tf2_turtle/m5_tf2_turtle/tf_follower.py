import math

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from geometry_msgs.msg import Twist
from tf2_ros import Buffer, TransformListener, TransformException


class TurtleFollower(Node):
    """Turtle2 patrzy na transformację z 'turtle2' do 'turtle1' i jedzie do niej."""

    def __init__(self):
        super().__init__('tf_follower')
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.pub = self.create_publisher(Twist, '/turtle2/cmd_vel', 10)
        self.create_timer(0.1, self.tick)
        self.get_logger().info('Follower: turtle2 dogania turtle1')

    def tick(self):
        try:
            t = self.buffer.lookup_transform(
                'turtle2', 'turtle1', Time())
        except TransformException as e:
            self.get_logger().info(f'Brak transformacji: {e}', throttle_duration_sec=2.0)
            return

        dx = t.transform.translation.x
        dy = t.transform.translation.y
        cmd = Twist()
        cmd.angular.z = 4.0 * math.atan2(dy, dx)
        cmd.linear.x = 0.5 * math.hypot(dx, dy)
        self.pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(TurtleFollower())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
