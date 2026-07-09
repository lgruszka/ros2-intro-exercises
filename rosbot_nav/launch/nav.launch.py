"""TRYB 2 (REAL) — Nawigacja po zapisanej mapie na realnym ROSbocie XL (cele w RViz).

KOLEJNOŚĆ:
    1) na ROBOCIE:  ros2 launch rosbot_bringup rosbot_xl.yaml
    2) na ROBOCIE:  ros2 launch rplidar_ros rplidar_s3_launch.py serial_port:=/dev/ttyUSB1
    3) gdziekolwiek: ros2 launch rosbot_nav nav.launch.py map:=$HOME/maps/moja_mapa.yaml
RViz (Fixed Frame = map): 2D Pose Estimate (gdzie stoi robot) → 2D Goal Pose (cel). Robot jedzie.

CO ROBI: (a) box-filter /scan → /scan_filtered, (b) nav2_bringup (map_server + AMCL + planner +
controller + collision_monitor + lifecycle) z naszym nav2_rosbot.yaml (wariant REAL).
DLACZEGO box-filter też tutaj: w wariancie REAL AMCL, costmapy I collision_monitor czytają
/scan_filtered (collision_monitor jest WŁĄCZONY dla bezpieczeństwa — bez filtra self-hity lidaru
fałszywie by hamowały). Sam nav2_bringup NIE zlokalizuje ROSbota gołą ręką: domyślny AMCL ma
base_frame_id=base_footprint, a ROSbot ma base_link — nasz config to naprawia (+ enable_stamped_cmd_vel).
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    pkg = get_package_share_directory('rosbot_nav')
    nav2_params = os.path.join(pkg, 'config', 'nav2_rosbot.yaml')
    filter_params = os.path.join(pkg, 'config', 'laser_filter.yaml')
    nav2_bringup = os.path.join(
        get_package_share_directory('nav2_bringup'), 'launch', 'bringup_launch.py')

    laser_filter = Node(
        package='laser_filters',
        executable='scan_to_scan_filter_chain',
        name='scan_to_scan_filter_chain',
        output='screen',
        parameters=[filter_params, {'use_sim_time': use_sim_time}],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='false',
            description='Realny robot = false (zegar systemowy).'),
        DeclareLaunchArgument(
            'map',
            description='Ścieżka do zapisanej mapy .yaml (z slam.launch.py + map_saver_cli).'),
        laser_filter,
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(nav2_bringup),
            launch_arguments={
                'map': LaunchConfiguration('map'),
                'use_sim_time': use_sim_time,
                'params_file': nav2_params,
            }.items(),
        ),
    ])
