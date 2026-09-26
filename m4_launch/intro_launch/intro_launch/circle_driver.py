import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from geometry_msgs.msg import Twist


class CircleDriver(Node):
    """Jedzie po okręgu: linear = speed, angular = speed / 2 (promień 2 m)."""

    def __init__(self):
        super().__init__('driver')
        self.declare_parameter('speed', 0.5)
        # nazwa WZGLĘDNA: namespace i remapy z launch zdecydują, dokąd trafi
        self.pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.create_timer(0.1, self.tick)
        speed = self.get_parameter('speed').value
        self.get_logger().info(
            f'Jadę po okręgu: speed={speed} m/s, publikuję na {self.pub.topic_name}')

    def tick(self):
        speed = self.get_parameter('speed').value
        cmd = Twist()
        cmd.linear.x = float(speed)
        cmd.angular.z = float(speed) / 2.0
        self.pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = CircleDriver()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
