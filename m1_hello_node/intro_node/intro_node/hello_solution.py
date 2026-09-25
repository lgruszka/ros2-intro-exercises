"""
Module 1 — Ćwiczenie hello node (SOLUTION).

Referencyjne rozwiązanie. Najpierw spróbuj sam w hello_skeleton.py.
"""

import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException


class Hello(Node):
    def __init__(self):
        super().__init__('hello')
        # TODO 1: ✓
        self.timer = self.create_timer(1.0, self.tick)
        self.count = 0

    def tick(self):
        # TODO 2: ✓
        self.get_logger().info(f'alive #{self.count}')
        self.count += 1


def main():
    rclpy.init()
    node = Hello()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
