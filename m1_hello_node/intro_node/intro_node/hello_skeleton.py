"""
Module 1 — Ćwiczenie hello node (SKELETON).

Wypełnij 2 TODO. Po zbudowaniu pakietu i uruchomieniu:
    ros2 run intro_node hello

powinieneś widzieć w logu:
    [INFO] [hello]: alive #0
    [INFO] [hello]: alive #1
    [INFO] [hello]: alive #2
    ...

Pomocnik: hello_solution.py obok zawiera referencyjne rozwiązanie.
"""

import rclpy
from rclpy.node import Node


class Hello(Node):
    def __init__(self):
        super().__init__('hello')

        # TODO 1: utwórz timer 1.0 sekundy wywołujący self.tick
        # Hint: self.create_timer(<period_sec>, <callback>)
        # Użyj: 1.0, self.tick
        # self.timer = ...

        self.count = 0

    def tick(self):
        # TODO 2: zaloguj wiadomość "alive #N" gdzie N to self.count
        # Hint:
        #   self.get_logger().info(f'alive #{self.count}')
        #   self.count += 1
        pass


def main():
    rclpy.init()
    node = Hello()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
