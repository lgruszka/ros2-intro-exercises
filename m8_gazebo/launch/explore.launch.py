"""TRYB 3 — Autonomiczna eksploracja: robot sam jeździ do "frontierów" (granic znane/nieznane)
i mapuje, aż zwiedzi ZAMKNIĘTĄ przestrzeń (w otwartej nigdy nie skończy). Bez teleopu.

Ten JEDEN launch składa cały stos eksploracji (oszczędza Ci żonglerki terminalami):
  1. slam.launch.py        — box-filter (/scan -> /scan_filtered) + slam_toolbox (mapa, map->odom)
  2. navigation_launch.py  — Nav2 w trybie SLAM (planner + controller + costmapy; BEZ map_servera
                             i AMCL — to slam_toolbox daje map->odom). Params: nasz nav2_rosbot.yaml.
  3. explore (explore_lite) — wybiera frontiery i wysyła cele do Nav2.

Wystarczą 2 terminale:
    T1:  ros2 launch rosbot_gazebo simulation.yaml robot_model:=rosbot_xl configuration:=autonomy
    T2:  ros2 launch m8_gazebo explore.launch.py use_sim_time:=true      # na realnym robocie: false

Gdy robot zwiedzi pomieszczenie — zapisz mapę:
    ros2 run nav2_map_server map_saver_cli -f ~/maps/sala1

WYMAGANIA: explore_lite NIE ma w apt — zbuduj ze źródeł (raz):
    cd ~/ros2_ws && vcs import src < src/ros2-intro-exercises/m8_gazebo/explore.repos
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
    pkg = get_package_share_directory('m8_gazebo')
    slam_launch = os.path.join(pkg, 'launch', 'slam.launch.py')
    # JEDEN plik params dla całego trybu 3: węzły Nav2 (przez navigation_launch.py) ORAZ
    # węzeł explore_lite czytają explore.yaml (każdy bierze swoją sekcję wg nazwy węzła).
    explore_params = os.path.join(pkg, 'config', 'explore.yaml')
    navigation_launch = os.path.join(
        get_package_share_directory('nav2_bringup'), 'launch', 'navigation_launch.py')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='true',
            description='true w symulacji (Gazebo), false na realnym robocie.'),

        # 1) SLAM (z box-filtrem w środku) — buduje mapę i publikuje map->odom.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(slam_launch),
            launch_arguments={'use_sim_time': use_sim_time}.items(),
        ),

        # 2) Nav2 w trybie SLAM (navigation_launch.py NIE odpala map_servera/AMCL).
        #    explore.yaml = zwalidowany config eksploracji (RegulatedPurePursuit), z kompletem
        #    sekcji dla Jazzy: collision_monitor + docking_server (inaczej "observation_sources
        #    is not initialized" / "Charging dock plugins not given"), pluginy ::, plugin_lib_names
        #    off, costmapy na /scan_filtered.
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
