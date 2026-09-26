"""Warsztat W3 — SLAM w Webots: scan_fix + slam_toolbox jednym poleceniem.

Uruchom NAJPIERW Webots (Terminal 1):
    ros2 launch webots_ros2_turtlebot robot_launch.py
potem ten launch (Terminal 2):
    ros2 launch m7_nav2_capstone slam_w3.launch.py

CO ROBI TEN LAUNCH (dwie rzeczy):
1. scan_fix: /scan -> /scan_fixed. Lidar w webots_ros2 publikuje skan „od tyłu”
   (angle_increment < 0), a slam_toolbox rysuje wtedy wygięte, podwójne ściany.
   scan_fix odwraca kolejność pomiarów, więc kąty rosną od -π do +π.
2. slam_toolbox przez stockowy online_async_launch.py (na Jazzy slam_toolbox to
   węzeł lifecycle; stockowy launch sam robi configure + activate). Podajemy
   params/slam_w3.yaml = stockowe parametry + scan_topic: /scan_fixed.

Nav2 (AMCL, costmapy) w kroku 3 czyta zwykły /scan i tego fixu nie potrzebuje.
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
    pkg = get_package_share_directory('m7_nav2_capstone')
    slam_params = os.path.join(pkg, 'params', 'slam_w3.yaml')
    online_async = os.path.join(
        get_package_share_directory('slam_toolbox'), 'launch', 'online_async_launch.py')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Zegar symulacji z Webots (/clock). W W3 zawsze true.',
        ),
        Node(
            package='m7_nav2_capstone',
            executable='scan_fix',
            name='scan_fix',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(online_async),
            launch_arguments={
                'slam_params_file': slam_params,
                'use_sim_time': use_sim_time,
            }.items(),
        ),
    ])
