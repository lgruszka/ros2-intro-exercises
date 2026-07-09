"""
Module 7 — Warsztat praktyczny — capstone bringup.

Opcjonalny launch który uruchamia Webots + Nav2 jednocześnie (zakłada że mapa
już istnieje w maps/my_map.yaml). Przydatne dla iteracji po Checkpoint 4,
kiedy nie chcesz za każdym razem ręcznie odpalać 4 terminali.

UWAGA: ten launch NIE startuje SLAM toolbox-a — najpierw zbuduj mapę
ręcznie wg README (Checkpointy 1-4), potem używaj tego launch-a do
iteracji nad Nav2 (Checkpointy 5+).

Użycie:
    cd ~/ros2_capstone
    ros2 launch launch/capstone_bringup.launch.py

Override mapy:
    ros2 launch launch/capstone_bringup.launch.py \\
        map_file:=/ścieżka/do/mapy.yaml
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    capstone_dir = os.path.expanduser('~/ros2_capstone')

    map_arg = DeclareLaunchArgument(
        'map_file',
        default_value=os.path.join(capstone_dir, 'maps', 'my_map.yaml'),
        description='Ścieżka do zapisanej mapy YAML',
    )

    params_arg = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(capstone_dir, 'params', 'nav2_params.yaml'),
        description='Ścieżka do parametrów Nav2',
    )

    # Webots + TurtleBot3
    webots_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('webots_ros2_turtlebot'),
                'launch',
                'robot_launch.py',
            )
        ),
    )

    # Nav2 (po stronie Webots musi być uruchomiony i działać —
    # uruchamiamy z opóźnieniem albo polegamy na lifecycle_manager retries).
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('nav2_bringup'),
                'launch',
                'bringup_launch.py',
            )
        ),
        launch_arguments={
            'map': LaunchConfiguration('map_file'),
            'params_file': LaunchConfiguration('params_file'),
            'use_sim_time': 'true',
        }.items(),
    )

    return LaunchDescription([
        map_arg,
        params_arg,
        webots_launch,
        nav2_launch,
    ])
