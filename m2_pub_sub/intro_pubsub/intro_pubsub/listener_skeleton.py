"""
Module 2 — Ćwiczenie listener (SKELETON).

Wypełnij 2 TODO. Po zbudowaniu pakietu i uruchomieniu (gdy talker działa):
    ros2 run intro_pubsub listener

powinieneś widzieć w logu:
    [INFO] [listener]: Received: Hello ROS2 #0
    [INFO] [listener]: Received: Hello ROS2 #1
    ...
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Listener(Node):
    def __init__(self):
        super().__init__('listener')

        # TODO 1: utwórz subscription
        # Hint: self.create_subscription(<typ>, <topic>, <callback>, <depth>)
        # Użyj: String, 'chatter', self.on_message, depth = 10
        # self.subscription = ...

    def on_message(self, msg: String):
        # TODO 2: zaloguj otrzymaną wiadomość
        # Hint: self.get_logger().info(f'Received: {msg.data}')
        pass


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
