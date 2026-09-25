"""
Warsztat W3 — capstone bringup (Webots + Nav2 jednocześnie).

Opcjonalny launch, który uruchamia Webots z TurtleBot3 i Nav2 naraz. Zakłada, że
mapa już istnieje w ~/maps/my_map.yaml (README, Checkpoint 4). Przydaje się do
iteracji nad Nav2, gdy nie chcesz za każdym razem otwierać kilku terminali.

UWAGA: ten launch NIE startuje SLAM toolboxa ani RViz. Najpierw zbuduj mapę
wg README (Checkpointy 1-4), otwórz RViz (ros2 launch nav2_bringup rviz_launch.py
use_sim_time:=true) i od razu po starcie ustaw „2D Pose Estimate” (Checkpoint 6).

Użycie:
    CAP=~/ros2_ws/src/ros2-intro-exercises/m7_nav2_capstone
    ros2 launch $CAP/launch/capstone_bringup.launch.py

Inna mapa:
    ros2 launch $CAP/launch/capstone_bringup.launch.py \\
        map_file:=/pełna/ścieżka/do/mapy.yaml
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    # katalog m7_nav2_capstone (ten plik leży w jego podkatalogu launch/)
    capstone_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    map_arg = DeclareLaunchArgument(
        'map_file',
        default_value=os.path.expanduser('~/maps/my_map.yaml'),
        description='Ścieżka do zapisanej mapy YAML',
    )

    params_arg = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(capstone_dir, 'params', 'nav2_params.yaml'),
        description='Ścieżka do parametrów Nav2 (domyślne z Jazzy + enable_stamped_cmd_vel)',
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
