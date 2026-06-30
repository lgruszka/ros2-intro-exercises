"""
Module 4 — Launch file uruchamiający 2 countery + monitor.

Wypełnij 3 TODO. Po build i source:

    ros2 launch intro_demo two_counters.launch.py
    ros2 launch intro_demo two_counters.launch.py rate:=3.0
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # TODO 1: zadeklaruj argument 'rate' z default_value '1.0'
    # Hint:
    #   rate_arg = DeclareLaunchArgument(
    #       'rate',
    #       default_value='1.0',
    #       description='Częstotliwość publikowania w Hz',
    #   )
    # rate_arg = ...

    # TODO 2: counter A — package intro_demo, executable counter, name counter_a,
    #         parameter rate z LaunchConfiguration('rate'),
    #         remap 'count' → 'count_a', output='screen'
    # Hint:
    #   counter_a = Node(
    #       package='intro_demo',
    #       executable='counter',
    #       name='counter_a',
    #       parameters=[{'rate': LaunchConfiguration('rate')}],
    #       remappings=[('count', 'count_a')],
    #       output='screen',
    #   )
    # counter_a = ...

    # TODO 3: counter B — analogicznie jak A, ale name='counter_b'
    #         i remap 'count' → 'count_b'
    # counter_b = ...

    # Monitor — gotowy, nie musisz nic zmieniać:
    monitor = Node(
        package='intro_demo',
        executable='monitor',
        name='monitor',
        output='screen',
    )

    return LaunchDescription([
        # TODO: dodaj tu rate_arg, counter_a, counter_b, monitor
        monitor,
    ])
