"""
Module 2 — Ćwiczenie talker (SOLUTION).

Referencyjne rozwiązanie. Najpierw spróbuj sam w talker_skeleton.py.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Talker(Node):
    def __init__(self):
        super().__init__('talker')
        # TODO 1: ✓
        self.publisher = self.create_publisher(String, 'chatter', 10)
        # TODO 2: ✓
        self.timer = self.create_timer(0.5, self.tick)
        self.count = 0

    def tick(self):
        # TODO 3: ✓
        msg = String()
        msg.data = f'Hello ROS2 #{self.count}'
        self.publisher.publish(msg)
        self.get_logger().info(f'Published: {msg.data}')
        self.count += 1


def main():
    rclpy.init()
    node = Talker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
