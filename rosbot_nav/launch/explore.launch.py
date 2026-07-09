"""TRYB 3 (REAL) — Autonomiczna eksploracja na realnym ROSbocie XL: robot sam mapuje pomieszczenie.

explore_lite (frontier-based) sam wybiera granice znane/nieznane i jedzie je zbadać — zero teleopu.
Działa tylko w ZAMKNIĘTEJ przestrzeni. Jeden launch składa cały stos (slam + box-filter + nav2 +
explore), więc po bringupie + lidarze wystarczy JEDEN dodatkowy terminal.

KOLEJNOŚĆ:
    1) na ROBOCIE:  ros2 launch rosbot_bringup rosbot_xl.yaml
    2) na ROBOCIE:  ros2 launch rplidar_ros rplidar_s3_launch.py serial_port:=/dev/ttyUSB1
    3) gdziekolwiek: ros2 launch rosbot_nav explore.launch.py        # slam+nav2+explore (use_sim_time:=false)
    4) gdy zwiedzi:  ros2 run nav2_map_server map_saver_cli -f ~/maps/sala1

WYMAGANIA (raz): explore_lite + jego msgs ze źródeł (NIE ma w apt — buduj OBA):
    cd ~/ros2_ws && vcs import src < src/ros2-intro-exercises/rosbot_nav/explore.repos
    rosdep install -i --from-path src --rosdistro jazzy -y
    colcon build --packages-select explore_lite_msgs explore_lite && source install/setup.bash
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
    slam_launch = os.path.join(pkg, 'launch', 'slam.launch.py')
    # JEDEN plik params dla całego trybu 3: węzły Nav2 (przez navigation_launch.py) ORAZ
    # węzeł explore_lite czytają explore.yaml (każdy bierze swoją sekcję wg nazwy węzła).
    explore_params = os.path.join(pkg, 'config', 'explore.yaml')
    navigation_launch = os.path.join(
        get_package_share_directory('nav2_bringup'), 'launch', 'navigation_launch.py')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='false',
            description='Realny robot = false (zegar systemowy).'),

        # 1) SLAM (z box-filtrem w środku) — buduje mapę i publikuje map->odom.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(slam_launch),
            launch_arguments={'use_sim_time': use_sim_time}.items(),
        ),

        # 2) Nav2 w trybie SLAM (navigation_launch.py NIE odpala map_servera/AMCL).
        #    explore.yaml = zwalidowany config eksploracji (RegulatedPurePursuit), wariant REAL
        #    (collision_monitor ON, /scan_filtered), z kompletem sekcji dla Jazzy.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(navigation_launch),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'params_file': explore_params,
            }.items(),
        ),

        # 3) explore_lite — frontier-based eksploracja, wysyła cele do Nav2.
        Node(
            package='explore_lite',
            executable='explore',
            name='explore_node',
            output='screen',
            parameters=[explore_params, {'use_sim_time': use_sim_time}],
        ),
    ])
