"""
Module 2 — Ćwiczenie listener (SOLUTION).
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Listener(Node):
    def __init__(self):
        super().__init__('listener')
        # TODO 1: ✓
        self.subscription = self.create_subscription(
            String,
            'chatter',
            self.on_message,
            10,
        )

    def on_message(self, msg: String):
        # TODO 2: ✓
        self.get_logger().info(f'Received: {msg.data}')


def main():
    rclpy.init()
    node = Listener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
