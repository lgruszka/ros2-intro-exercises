"""Nawigacja Nav2 dla ROSbota XL w Gazebo (po zapisaniu mapy slam.launch.py).

NAJPIERW symulacja z lidarem:
    ros2 launch rosbot_gazebo simulation.yaml robot_model:=rosbot_xl configuration:=autonomy
potem nawigacja:
    ros2 launch m8_gazebo nav.launch.py map:=$HOME/maps/sala1.yaml

W RViz: 2D Pose Estimate (powiedz robotowi gdzie stoi) -> 2D Goal Pose (cel). Robot pojedzie.

Deleguje do nav2_bringup z naszym nav2_rosbot.yaml — sedno: base_link zamiast base_footprint
(ROSbot nie ma base_footprint, inaczej AMCL nie zlokalizuje). nav2_bringup sam odpala
map_server + amcl + planner + controller + lifecycle_manager (configure+activate).
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    nav2_params = os.path.join(
        get_package_share_directory('m8_gazebo'), 'config', 'nav2_rosbot.yaml')
    nav2_bringup = os.path.join(
        get_package_share_directory('nav2_bringup'), 'launch', 'bringup_launch.py')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='true',
            description='Zegar z symulacji (Gazebo). Na realnym robocie: false.'),
        DeclareLaunchArgument(
            'map',
            description='Ścieżka do zapisanej mapy .yaml (z slam.launch.py + map_saver_cli).'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(nav2_bringup),
            launch_arguments={
                'map': LaunchConfiguration('map'),
                'use_sim_time': use_sim_time,
                'params_file': nav2_params,
            }.items(),
        ),
    ])
