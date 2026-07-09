"""
Module 2 — Ćwiczenie talker (SKELETON).

Wypełnij 3 TODO. Po zbudowaniu pakietu i uruchomieniu:
    ros2 run intro_pubsub talker

powinieneś widzieć w logu:
    [INFO] [talker]: Published: Hello ROS2 #0
    [INFO] [talker]: Published: Hello ROS2 #1
    ...

W razie problemu — talker_solution.py jest obok jako referencja.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Talker(Node):
    def __init__(self):
        super().__init__('talker')

        # TODO 1: utwórz publisher
        # Hint: self.create_publisher(<typ>, <nazwa topiku>, <depth>)
        # Użyj: String, 'chatter', depth = 10
        # self.publisher = ...

        # TODO 2: utwórz timer co 500 ms
        # Hint: self.create_timer(<period_sec>, <callback>)
        # Użyj: 0.5, self.tick
        # self.timer = ...

        self.count = 0

    def tick(self):
        # TODO 3: zbuduj wiadomość, opublikuj, zaloguj
        # Hint:
        #   msg = String()
        #   msg.data = f'Hello ROS2 #{self.count}'
        #   self.publisher.publish(msg)
        #   self.get_logger().info(f'Published: {msg.data}')
        #   self.count += 1
        pass


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
