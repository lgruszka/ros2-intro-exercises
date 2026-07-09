"""
Module 4 — Counter node.

Publikuje rosnący Int32 na topic 'count' z parametryzowaną częstotliwością.
Remappable przez --ros-args -r count:=count_a.

ros2 run intro_demo counter
ros2 run intro_demo counter --ros-args -p rate:=2.0
ros2 run intro_demo counter --ros-args -r count:=count_a
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32


class Counter(Node):
    def __init__(self):
        super().__init__('counter')

        self.declare_parameter('rate', 1.0)
        rate_hz = self.get_parameter('rate').value

        self.publisher = self.create_publisher(Int32, 'count', 10)
        self.timer = self.create_timer(1.0 / rate_hz, self.tick)
        self.count = 0
        self.get_logger().info(f'Counter publishing on /count at {rate_hz} Hz')

    def tick(self):
        msg = Int32()
        msg.data = self.count
        self.publisher.publish(msg)
        self.count += 1


def main():
    rclpy.init()
    node = Counter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
