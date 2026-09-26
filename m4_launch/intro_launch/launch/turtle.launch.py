# intro_launch/launch/turtle.launch.py
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='turtlesim',
            executable='turtlesim_node',
            name='sim',
            output='screen',
        ),
        # TODO L1: drugi Node - program circle_driver z pakietu intro_launch
    ])
