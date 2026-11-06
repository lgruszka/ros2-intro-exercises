#!/usr/bin/env python3
"""Zastępczy chwytak Franka Hand dla fake hardware (W8).

Po co: w trybie use_fake_hardware:=true franka_ros2 uruchamia tylko
fake_gripper_state_publisher.py, który publikuje STAŁY stan palców (0.035 m) i nie ma
żadnego serwera akcji. MoveIt nie miałby więc komu wysłać komendy chwytaka.

Ten node udaje interfejs prawdziwego franka_gripper_node (nazwa node'a: franka_gripper):
  ~/joint_states   (sensor_msgs/JointState)            fr3_finger_joint1/2 = szerokość / 2
  ~/gripper_action (control_msgs/action/GripperCommand) cel: position = szerokość / 2
  ~/move           (franka_msgs/action/Move)            cel: width [m], speed [m/s]
  ~/grasp          (franka_msgs/action/Grasp)           cel: width, speed, force, epsilon
Palce jadą do celu z zadaną prędkością (bez fizyki: na klocku też się domkną).
Na prawdziwym FR3 ten node NIE startuje - interfejs daje oficjalny franka_gripper_node.
"""
import threading
import time

import rclpy
from control_msgs.action import GripperCommand
from rclpy.action import ActionServer
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState

try:  # franka_msgs jest w workspace franka_ros2; bez niego zostaje sam gripper_action
    from franka_msgs.action import Grasp, Move
except ImportError:  # pragma: no cover
    Grasp = Move = None

MAX_WIDTH = 0.08        # Franka Hand: palce 0-0.04 m każdy
DEFAULT_SPEED = 0.1     # m/s, jak default_speed w franka_gripper_node.yaml


class FakeGripper(Node):

    def __init__(self):
        super().__init__('franka_gripper')
        self.declare_parameter('joint_names', ['fr3_finger_joint1', 'fr3_finger_joint2'])
        # start: palce zamknięte - jak chwytak, który ostatnio coś zacisnął (lekcja W8: najpierw open)
        self.declare_parameter('initial_width', 0.0)
        self.joint_names = list(self.get_parameter('joint_names').value)
        self.width = float(self.get_parameter('initial_width').value)
        self.lock = threading.Lock()
        group = ReentrantCallbackGroup()
        self.pub = self.create_publisher(JointState, '~/joint_states', 1)
        self.create_timer(1.0 / 30.0, self.publish_state)
        ActionServer(self, GripperCommand, '~/gripper_action', self.on_gripper_command,
                     callback_group=group)
        if Move is not None:
            ActionServer(self, Move, '~/move', self.on_move, callback_group=group)
            ActionServer(self, Grasp, '~/grasp', self.on_grasp, callback_group=group)
        self.get_logger().info(
            f'Zastępczy chwytak (fake hardware) gotowy, szerokość {self.width:.3f} m')

    def publish_state(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = self.joint_names
        with self.lock:
            half = self.width / 2.0
        msg.position = [half, half]
        msg.velocity = [0.0, 0.0]
        msg.effort = [0.0, 0.0]
        self.pub.publish(msg)

    def drive_to(self, target, speed):
        """Jedź palcami do szerokości `target` [m] z prędkością `speed` [m/s]."""
        target = min(max(target, 0.0), MAX_WIDTH)
        speed = speed if speed > 0.0 else DEFAULT_SPEED
        dt = 0.02
        while True:
            with self.lock:
                err = target - self.width
                if abs(err) <= speed * dt:
                    self.width = target
                    return self.width
                self.width += speed * dt if err > 0 else -speed * dt
            time.sleep(dt)

    def on_gripper_command(self, goal_handle):
        target = 2.0 * goal_handle.request.command.position
        self.get_logger().info(f'gripper_action: szerokość -> {target:.3f} m')
        width = self.drive_to(target, DEFAULT_SPEED)
        goal_handle.succeed()
        result = GripperCommand.Result()
        result.position = width
        result.reached_goal = True
        return result

    def on_move(self, goal_handle):
        g = goal_handle.request
        self.get_logger().info(f'move: szerokość -> {g.width:.3f} m')
        self.drive_to(g.width, g.speed)
        goal_handle.succeed()
        result = Move.Result()
        result.success = True
        return result

    def on_grasp(self, goal_handle):
        g = goal_handle.request
        self.get_logger().info(f'grasp: szerokość -> {g.width:.3f} m, siła {g.force:.1f} N')
        self.drive_to(g.width, g.speed)
        goal_handle.succeed()
        result = Grasp.Result()
        result.success = True
        return result


def main(args=None):
    rclpy.init(args=args)
    node = FakeGripper()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
