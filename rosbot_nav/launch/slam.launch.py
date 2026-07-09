"""TRYB 1 (REAL) — Mapowanie SLAM na realnym ROSbocie XL: budujesz mapę, zapisujesz do pliku.

KOLEJNOŚĆ (3 terminale na robocie / laptopie, ten sam ROS_DOMAIN_ID):
    1) na ROBOCIE:  ros2 launch rosbot_bringup rosbot_xl.yaml      # koła, odometria, TF
    2) na ROBOCIE:  ros2 launch rplidar_ros rplidar_s3_launch.py serial_port:=/dev/ttyUSB1   # → /scan
    3) gdziekolwiek: ros2 launch rosbot_nav slam.launch.py         # TEN launch (use_sim_time:=false domyślnie)
    4) jedź teleopem: ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true
    5) zapisz mapę:   ros2 run nav2_map_server map_saver_cli -f ~/maps/moja_mapa

CO ROBI: (a) box-filter /scan → /scan_filtered (wycina bryłę robota — bez tego SLAM rysuje pierścień
przeszkód i robot „kręci się w kółko"), (b) slam_toolbox (Jazzy lifecycle, przez stockowy
online_async_launch.py; base_frame: base_link bo ROSbot nie ma base_footprint). Config: rosbot_nav/config.
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
    slam_params = os.path.join(pkg, 'config', 'slam_rosbot.yaml')
    filter_params = os.path.join(pkg, 'config', 'laser_filter.yaml')
    online_async = os.path.join(
        get_package_share_directory('slam_toolbox'), 'launch', 'online_async_launch.py')

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
            description='Realny robot = false (zegar systemowy). true tylko jeśli puszczasz w sim.'),
        laser_filter,
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(online_async),
            launch_arguments={
                'slam_params_file': slam_params,
                'use_sim_time': use_sim_time,
            }.items(),
        ),
    ])
