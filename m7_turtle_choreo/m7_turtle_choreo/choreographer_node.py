import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64


class Choreographer(Node):
    def __init__(self):
        super().__init__('choreographer')
        self.declare_parameter('speed', 0.5)
        self.phase = 0.0
        self.last_t = self.get_clock().now()
        self.pub = self.create_publisher(Float64, '/choreo/phase', 10)
        self.create_timer(0.02, self.tick)
        self.get_logger().info('Dyryguję')

    def tick(self):
        now = self.get_clock().now()
        dt = (now - self.last_t).nanoseconds * 1e-9
        self.last_t = now
        speed = self.get_parameter('speed').value
        self.phase += speed * dt
        msg = Float64()
        msg.data = self.phase
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(Choreographer())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
