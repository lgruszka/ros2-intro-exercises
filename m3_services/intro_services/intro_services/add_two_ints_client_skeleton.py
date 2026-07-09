"""
Module 3 — Service client (SKELETON).

Wypełnij 2 TODO. Po zbudowaniu pakietu i uruchomieniu (serwer musi już biec):
    ros2 run intro_services add_client 7 5

powinieneś widzieć:
    [INFO] [add_two_ints_client]: 7 + 5 = 12
"""

import sys
import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts


class AddTwoIntsClient(Node):
    def __init__(self):
        super().__init__('add_two_ints_client')

        # TODO 1: utwórz klienta
        # Hint: self.create_client(<Typ>, <nazwa>)
        # Użyj: AddTwoInts, 'add_two_ints'
        # self.client = ...

        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('czekam na serwer /add_two_ints...')

    def call(self, a: int, b: int) -> int:
        # TODO 2: zbuduj request, wywołaj asynchronicznie, poczekaj na result
        # Hint:
        #   request = AddTwoInts.Request()
        #   request.a = a
        #   request.b = b
        #   future = self.client.call_async(request)
        #   rclpy.spin_until_future_complete(self, future)
        #   return future.result().sum
        pass


def main():
    rclpy.init()
    node = AddTwoIntsClient()

    if len(sys.argv) != 3:
        node.get_logger().error('Użycie: ros2 run intro_services add_client <a> <b>')
        rclpy.shutdown()
        return

    a = int(sys.argv[1])
    b = int(sys.argv[2])
    result = node.call(a, b)
    node.get_logger().info(f'{a} + {b} = {result}')

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
