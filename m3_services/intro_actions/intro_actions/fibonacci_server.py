"""
Module 3 stretch — Fibonacci action server.

Gotowy do uruchomienia:
    ros2 run intro_actions fibonacci_server

Test z CLI (drugi terminal):
    ros2 action send_goal /fibonacci \\
        action_tutorials_interfaces/action/Fibonacci \\
        "{order: 6}" \\
        --feedback

Co minutę wypisuje feedback (kolejne wyrazy ciągu), po zakończeniu zwraca
finalną sekwencję jako result.
"""

import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from action_tutorials_interfaces.action import Fibonacci


class FibonacciActionServer(Node):
    def __init__(self):
        super().__init__('fibonacci_action_server')
        self.server = ActionServer(
            self,
            Fibonacci,
            'fibonacci',
            self.execute_callback,
        )
        self.get_logger().info('Action /fibonacci ready')

    def execute_callback(self, goal_handle):
        self.get_logger().info(f'Goal: order={goal_handle.request.order}')

        feedback = Fibonacci.Feedback()
        feedback.partial_sequence = [0, 1]

        for i in range(1, goal_handle.request.order):
            feedback.partial_sequence.append(
                feedback.partial_sequence[i] + feedback.partial_sequence[i - 1]
            )
            self.get_logger().info(f'feedback: {feedback.partial_sequence}')
            goal_handle.publish_feedback(feedback)
            time.sleep(1.0)

        goal_handle.succeed()
        result = Fibonacci.Result()
        result.sequence = feedback.partial_sequence
        return result


def main():
    rclpy.init()
    node = FibonacciActionServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
