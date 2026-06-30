"""
Module 3 — Service server (SOLUTION).
"""

import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts


class AddTwoIntsServer(Node):
    def __init__(self):
        super().__init__('add_two_ints_server')
        # TODO 1: ✓
        self.srv = self.create_service(
            AddTwoInts,
            'add_two_ints',
            self.handle_request,
        )
        self.get_logger().info('Service /add_two_ints ready')

    def handle_request(self, request, response):
        # TODO 2: ✓
        response.sum = request.a + request.b
        # TODO 3: ✓
        self.get_logger().info(
            f'request: {request.a} + {request.b} → {response.sum}'
        )
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
