"""Warsztat W3 (wariant Go2) - Nav2 z AMCL na zapisanej mapie.

Najpierw symulacja (Terminal 1, SLAM musi być wyłączony):
    ros2 launch w3_go2_sim go2_sim.launch.py
potem ten launch (Terminal 2):
    ros2 launch w3_go2_sim nav.launch.py map:=$HOME/maps/go2_room.yaml

Używa stockowego nav2_bringup/bringup_launch.py (map_server + AMCL + cały stos
nawigacji) z parametrami params/nav2_go2_sim.yaml. AMCL startuje z pozy (0, 0, 0),
czyli z miejsca, w którym robot pojawia się w Gazebo i w którym zaczęło się mapowanie.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg = get_package_share_directory('w3_go2_sim')
    bringup = os.path.join(
        get_package_share_directory('nav2_bringup'), 'launch', 'bringup_launch.py')
    return LaunchDescription([
        DeclareLaunchArgument(
            'map', default_value=os.path.join(os.path.expanduser('~'), 'maps', 'go2_room.yaml'),
            description='Pełna ścieżka do mapy .yaml zapisanej po SLAM'),
        DeclareLaunchArgument(
            'params_file', default_value=os.path.join(pkg, 'params', 'nav2_go2_sim.yaml'),
            description='Parametry Nav2 dla Go2 w symulacji'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(bringup),
            launch_arguments={
                'map': LaunchConfiguration('map'),
                'params_file': LaunchConfiguration('params_file'),
                'use_sim_time': 'true',
                'autostart': 'true',
            }.items(),
        ),
    ])
