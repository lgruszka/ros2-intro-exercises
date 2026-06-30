"""
Module 3 — Service server (SKELETON).

Wypełnij 3 TODO. Po zbudowaniu pakietu i uruchomieniu:
    ros2 run intro_services add_server

powinieneś widzieć:
    [INFO] [add_two_ints_server]: Service /add_two_ints ready

i potem (gdy klient zawoła):
    [INFO] [add_two_ints_server]: request: 7 + 5 → 12
"""

import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts


class AddTwoIntsServer(Node):
    def __init__(self):
        super().__init__('add_two_ints_server')

        # TODO 1: utwórz service
        # Hint: self.create_service(<Typ>, <nazwa>, <callback>)
        # Użyj: AddTwoInts, 'add_two_ints', self.handle_request
        # self.srv = ...

        self.get_logger().info('Service /add_two_ints ready')

    def handle_request(self, request, response):
        # TODO 2: policz sumę
        # Hint: response.sum = request.a + request.b
        pass

        # TODO 3: zaloguj
        # Hint:
        #   self.get_logger().info(f'request: {request.a} + {request.b} → {response.sum}')

        return response


def main():
    rclpy.init()
    node = AddTwoIntsServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
