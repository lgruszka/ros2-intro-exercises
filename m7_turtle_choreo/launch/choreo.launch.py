import math

from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node

OFFSETS = [0.0, 2 * math.pi / 3, 4 * math.pi / 3]


def generate_launch_description():
    spawn_t2 = ExecuteProcess(
        cmd=['ros2', 'service', 'call', '/spawn', 'turtlesim/srv/Spawn',
             '{x: 5.5, y: 5.5, theta: 0.0, name: turtle2}'],
        output='screen')
    spawn_t3 = ExecuteProcess(
        cmd=['ros2', 'service', 'call', '/spawn', 'turtlesim/srv/Spawn',
             '{x: 5.5, y: 5.5, theta: 0.0, name: turtle3}'],
        output='screen')

    actions = [
        Node(package='turtlesim', executable='turtlesim_node', name='turtlesim'),
        TimerAction(period=2.0, actions=[spawn_t2, spawn_t3]),
        Node(package='m7_turtle_choreo', executable='choreographer_node',
             parameters=[{'speed': 0.6}]),
    ]
    for i, off in enumerate(OFFSETS):
        actions.append(TimerAction(period=4.0, actions=[
            Node(package='m7_turtle_choreo', executable='dancer_node',
                 name=f'dancer_{i+1}',
                 parameters=[{
                     'turtle_name': f'turtle{i+1}',
                     'phase_offset': off,
                     'kp_lin': 4.0,
                     'kp_ang': 8.0,
                 }]),
        ]))
    return LaunchDescription(actions)
