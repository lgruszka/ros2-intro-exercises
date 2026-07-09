import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster
from turtlesim.msg import Pose


class TurtleTfBroadcaster(Node):
    def __init__(self):
        super().__init__('tf_broadcaster')
        self.declare_parameter('turtle_name', 'turtle1')
        self.name = self.get_parameter('turtle_name').value
        self.br = TransformBroadcaster(self)
        self.create_subscription(
            Pose, f'/{self.name}/pose', self.on_pose, 10)
        self.get_logger().info(f'Broadcaster dla world→{self.name}')

    def on_pose(self, msg):
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'world'
        t.child_frame_id = self.name
        t.transform.translation.x = msg.x
        t.transform.translation.y = msg.y
        t.transform.translation.z = 0.0
        # Pose.theta → quaternion przy obrocie tylko wokół Z
        t.transform.rotation.z = math.sin(msg.theta / 2.0)
        t.transform.rotation.w = math.cos(msg.theta / 2.0)
        self.br.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(TurtleTfBroadcaster())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
