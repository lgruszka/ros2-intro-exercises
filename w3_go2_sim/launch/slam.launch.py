"""Warsztat W3 (wariant Go2) - SLAM: slam_toolbox buduje mapę sali.

Najpierw symulacja (Terminal 1):
    ros2 launch w3_go2_sim go2_sim.launch.py
potem ten launch (Terminal 2):
    ros2 launch w3_go2_sim slam.launch.py

Na Jazzy slam_toolbox jest węzłem lifecycle - stockowy online_async_launch.py
sam robi configure + activate. Podajemy mu params/slam.yaml (ramka base_footprint,
topic /scan z pointcloud_to_laserscan).
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    pkg = get_package_share_directory('w3_go2_sim')
    online_async = os.path.join(
        get_package_share_directory('slam_toolbox'), 'launch', 'online_async_launch.py')
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(online_async),
            launch_arguments={
                'slam_params_file': os.path.join(pkg, 'params', 'slam.yaml'),
                'use_sim_time': 'true',
            }.items(),
        ),
    ])
