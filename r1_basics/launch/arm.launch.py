"""W10: sekwencja rąk/głowy/talii przez arm_sdk. Robot STOI (FSM 4), nigdy razem z chodem (W9).

Użycie:
    ros2 launch r1_basics arm.launch.py use_mock:=true    # makieta (startuje w FSM 4)
    ros2 launch r1_basics arm.launch.py                   # robot
Launch kończy się razem z arm_sequence (po oddaniu sterowania).
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, Shutdown
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def setup(context):
    config = PathJoinSubstitution([FindPackageShare('r1_basics'), 'config', 'r1_basics.yaml'])
    actions = []
    if LaunchConfiguration('use_mock').perform(context).lower() in ('true', '1', 'yes'):
        actions.append(Node(package='r1_basics', executable='r1_mock', name='r1_mock', output='screen',
                            emulate_tty=True, parameters=[config, {'fsm': 4}]))
    actions.append(Node(package='r1_basics', executable='arm_sequence', name='arm_sequence', output='screen',
                        emulate_tty=True, parameters=[config], on_exit=Shutdown()))
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('use_mock', default_value='false', description='true = makieta r1_mock (FSM 4)'),
        OpaqueFunction(function=setup),
    ])
