"""Wysyła kolejno kilka celów do Nav2 i wypisuje, które zostały osiągnięte.

Użycie (Nav2 musi działać - nav.launch.py):
    ros2 run w3_go2_sim send_goals
    ros2 run w3_go2_sim send_goals --ros-args -p goals:="[3.0, -1.0, -4.0, 3.5]"

Parametr goals to płaska lista par x, y w ramce map (metry). Domyślnie trzy
punkty w sali go2_room.sdf. Każdy cel ma limit czasu (parametr timeout, w sekundach).
"""
import math
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

DEFAULT_GOALS = [2.0, -1.5, -4.5, -3.0, 4.5, 3.5]


def make_pose(nav, x, y, yaw=0.0):
    p = PoseStamped()
    p.header.frame_id = 'map'
    p.header.stamp = nav.get_clock().now().to_msg()
    p.pose.position.x = x
    p.pose.position.y = y
    p.pose.orientation.z = math.sin(yaw / 2.0)
    p.pose.orientation.w = math.cos(yaw / 2.0)
    return p


def main():
    rclpy.init()
    nav = BasicNavigator(node_name='send_goals')
    nav.declare_parameter('goals', DEFAULT_GOALS)
    nav.declare_parameter('timeout', 180.0)
    goals = list(nav.get_parameter('goals').value)
    timeout = float(nav.get_parameter('timeout').value)
    pairs = [(goals[i], goals[i + 1]) for i in range(0, len(goals) - 1, 2)]

    # Czeka, aż AMCL i bt_navigator będą aktywne (lifecycle „active”)
    nav.waitUntilNav2Active(localizer='amcl')

    results = []
    for i, (x, y) in enumerate(pairs, start=1):
        nav.get_logger().info(f'Cel {i}/{len(pairs)}: x={x:.2f} y={y:.2f}')
        wall = time.time()
        nav.goToPose(make_pose(nav, x, y))
        while not nav.isTaskComplete():
            if time.time() - wall > timeout:
                nav.get_logger().warn('Przekroczony czas - anuluję cel')
                nav.cancelTask()
                break
            time.sleep(0.5)
        result = nav.getResult()
        ok = result == TaskResult.SUCCEEDED
        results.append(ok)
        nav.get_logger().info(
            f'Cel {i}: {"OSIĄGNIĘTY" if ok else "NIEOSIĄGNIĘTY (" + str(result) + ")"} '
            f'po {time.time() - wall:.0f} s')

    nav.get_logger().info(f'WYNIK: {sum(results)}/{len(results)} celów osiągniętych')
    nav.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
