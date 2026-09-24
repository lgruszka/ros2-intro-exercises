"""TRYB 2 (REAL) — Nawigacja po zapisanej mapie na realnym ROSbocie XL (cele w RViz).

KOLEJNOŚĆ:
    1) na ROBOCIE:  ros2 launch rosbot_bringup rosbot_xl.yaml
    2) na ROBOCIE:  ros2 launch rplidar_ros rplidar_s3_launch.py serial_port:=/dev/ttyUSB1
    3) gdziekolwiek: ros2 launch rosbot_nav nav.launch.py map:=$HOME/maps/moja_mapa.yaml
                     (wariant RPP: dopisz controller:=rpp)
    4) osobno:      rviz2   (NIE drugi nav.launch.py — mapa pojawi się w RViz sama)
RViz (Fixed Frame = map): 2D Pose Estimate (gdzie stoi robot) → 2D Goal Pose (cel). Robot jedzie.
Pozycję startową zaznacz w ~60 s od startu — inaczej global_costmap nie wstanie ("Aborting bringup").

CO ROBI: (a) box-filter /scan → /scan_filtered, (b) nav2_bringup (map_server + AMCL + planner +
controller + collision_monitor + lifecycle) z naszym nav2_rosbot.yaml (wariant REAL).
DLACZEGO box-filter też tutaj: w wariancie REAL AMCL, costmapy I collision_monitor czytają
/scan_filtered (collision_monitor jest WŁĄCZONY dla bezpieczeństwa — bez filtra self-hity lidaru
fałszywie by hamowały). Sam nav2_bringup NIE zlokalizuje ROSbota gołą ręką: domyślny AMCL ma
base_frame_id=base_footprint, a ROSbot ma base_link — nasz config to naprawia (+ enable_stamped_cmd_vel).

ARGUMENTY: controller:=mppi (domyślnie; omija przeszkody) | rpp (prosty, szybki, przed przeszkodą staje),
params_file:=<pełna ścieżka> nadpisuje oba. BLOKADA: jeśli w sieci (ten sam ROS_DOMAIN_ID) działa już
Nav2 (/bt_navigator), launch się NIE uruchomi — dwa Nav2 o tych samych nazwach ładują sobie nawzajem
węzły do kontenerów i cele padają ("unknown goal response", "Goal failed"). Obejście: allow_duplicate:=true.
"""
import os
import time

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription, LogInfo,
                            OpaqueFunction, Shutdown)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

CONTROLLER_FILES = {'mppi': 'nav2_rosbot.yaml', 'rpp': 'nav2_rosbot_rpp.yaml'}


def nav2_already_running(timeout=2.5):
    """Czy w grafie ROS jest już /bt_navigator (czyli działający Nav2)? Błąd sprawdzenia = False."""
    try:
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        ctx = rclpy.Context()
        rclpy.init(context=ctx)
        try:
            node = rclpy.create_node('rosbot_nav_duplicate_check', context=ctx)
            executor = SingleThreadedExecutor(context=ctx)
            executor.add_node(node)
            deadline = time.time() + timeout
            while time.time() < deadline:  # discovery DDS potrzebuje chwili
                executor.spin_once(timeout_sec=0.2)
                if any(name == 'bt_navigator' for name, _ in node.get_node_names_and_namespaces()):
                    return True
            return False
        finally:
            rclpy.shutdown(context=ctx)
    except Exception:
        return False


def launch_setup(context):
    if (LaunchConfiguration('allow_duplicate').perform(context).lower() != 'true'
            and nav2_already_running()):
        return [
            LogInfo(msg='[rosbot_nav] Nav2 JUŻ DZIAŁA w tej sieci (/bt_navigator) — NIE uruchamiam '
                        'drugiego. Do podglądu mapy wystarczy samo: rviz2. Restart nawigacji: Ctrl+C '
                        'w terminalu z działającym nav.launch.py i uruchom ponownie.'),
            Shutdown(reason='Nav2 already running'),
        ]

    pkg = get_package_share_directory('rosbot_nav')
    params_file = LaunchConfiguration('params_file').perform(context)
    if not params_file:
        controller = LaunchConfiguration('controller').perform(context).lower()
        if controller not in CONTROLLER_FILES:
            return [LogInfo(msg=f'[rosbot_nav] Nieznany controller:={controller} (mppi|rpp).'),
                    Shutdown(reason='bad controller argument')]
        params_file = os.path.join(pkg, 'config', CONTROLLER_FILES[controller])
    use_sim_time = LaunchConfiguration('use_sim_time')

    laser_filter = Node(
        package='laser_filters',
        executable='scan_to_scan_filter_chain',
        name='scan_to_scan_filter_chain',
        output='screen',
        parameters=[os.path.join(pkg, 'config', 'laser_filter.yaml'),
                    {'use_sim_time': use_sim_time}],
    )
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('nav2_bringup'), 'launch', 'bringup_launch.py')),
        launch_arguments={
            'map': LaunchConfiguration('map'),
            'use_sim_time': use_sim_time,
            'params_file': params_file,
        }.items(),
    )
    return [LogInfo(msg=f'[rosbot_nav] Nav2 z plikiem: {params_file}'), laser_filter, nav2]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='false',
            description='Realny robot = false (zegar systemowy).'),
        DeclareLaunchArgument(
            'map',
            description='Ścieżka do zapisanej mapy .yaml (z slam.launch.py + map_saver_cli).'),
        DeclareLaunchArgument(
            'controller', default_value='mppi',
            description='mppi (omija przeszkody) | rpp (prosty, szybki, przed przeszkodą staje).'),
        DeclareLaunchArgument(
            'params_file', default_value='',
            description='Pełna ścieżka do własnego pliku Nav2 (nadpisuje controller:=).'),
        DeclareLaunchArgument(
            'allow_duplicate', default_value='false',
            description='true = pomiń blokadę drugiego Nav2 w tej samej sieci (tylko świadomie).'),
        OpaqueFunction(function=launch_setup),
    ])
