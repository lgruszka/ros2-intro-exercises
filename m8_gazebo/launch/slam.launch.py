"""TRYB 1 — Mapowanie (SLAM) ROSbota XL: budujesz mapę, na końcu zapisujesz do pliku.

Uruchom NAJPIERW symulację z lidarem:
    ros2 launch rosbot_gazebo simulation.yaml robot_model:=rosbot_xl configuration:=autonomy
potem ten launch:
    ros2 launch m8_gazebo slam.launch.py use_sim_time:=true      # na realnym robocie: false
jeźdź teleopem (Jazzy: /cmd_vel to TwistStamped, stąd stamped:=true):
    ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true
i na końcu zapisz mapę:
    ros2 run nav2_map_server map_saver_cli -f ~/maps/moja_mapa

CO ROBI TEN LAUNCH (dwie rzeczy):
1. laser_filters (box-filter, config/laser_filter.yaml): /scan -> /scan_filtered.
   Lidar ROSbota — TAKŻE w Gazebo — widzi własną konstrukcję ~5 cm (~100 pkt @ 0.066-0.2 m).
   Bez filtra SLAM wrysowuje je jako pierścień przeszkód → komórka startowa "lethal" → planner
   nie rusza → robot kręci się w kółko. Filtr wycina prostokąt bryły robota (base_link).
2. slam_toolbox przez stockowy online_async_launch.py. UWAGA: na ROS 2 Jazzy slam_toolbox to
   węzeł LIFECYCLE — uruchomiony jako zwykły Node startuje UNCONFIGURED i NIE buduje /map.
   Stockowy launch odpala go jako LifecycleNode i sam robi configure+activate (autostart),
   dlatego delegujemy do niego, podając nasz config (base_frame: base_link, scan_topic: /scan_filtered).
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
    pkg = get_package_share_directory('m8_gazebo')
    slam_params = os.path.join(pkg, 'config', 'slam_rosbot.yaml')
    filter_params = os.path.join(pkg, 'config', 'laser_filter.yaml')
    online_async = os.path.join(
        get_package_share_directory('slam_toolbox'), 'launch', 'online_async_launch.py')

    # Box-filter: /scan -> /scan_filtered (wycina self-hity bryły robota). slam_rosbot.yaml
    # ma scan_topic: /scan_filtered, więc slam_toolbox czyta wyjście filtra.
    laser_filter = Node(
        package='laser_filters',
        executable='scan_to_scan_filter_chain',
        name='scan_to_scan_filter_chain',
        output='screen',
        parameters=[filter_params, {'use_sim_time': use_sim_time}],
        # domyślne topiki: 'scan' -> /scan (wejście), 'scan_filtered' -> /scan_filtered (wyjście)
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Zegar z symulacji (Gazebo). Na realnym robocie: false.',
        ),
        laser_filter,
        # Delegacja do stockowego launcha slam_toolbox — on odpala LifecycleNode i robi
        # configure+activate (autostart). Podajemy nasz config (base_link, /scan_filtered).
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(online_async),
            launch_arguments={
                'slam_params_file': slam_params,
                'use_sim_time': use_sim_time,
            }.items(),
        ),
    ])
