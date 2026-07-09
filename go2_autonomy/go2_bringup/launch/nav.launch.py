"""Autonomiczna nawigacja na realnym Unitree Go2 (Nav2 + AMCL na gotowej mapie).

Składa: percepcja (cloud->scan) + TF + Nav2 (planner/controller/AMCL) + most ruchu
(arbiter cmd_vel -> sport API Unitree). Mapę zrób najpierw przez mapping.launch.py.

  ros2 launch go2_bringup nav.launch.py map:=$HOME/maps/sala1.yaml

Wariant nav-only z tego kursu (BEZ courier dock/mission/kamery). Cele wskazujesz
ręcznie w RViz/Foxglove (2D Pose Estimate -> Nav2 Goal).

Założenia (firmware Go2 publikuje natywnie):
  - /lowstate, /api/sport/request (sport API)
  - /utlidar/cloud_base (PointCloud2 w base_link) + /utlidar/imu
  - /utlidar/robot_odom (Odometry — źródło dla odom_tf_relay)
"""
from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            GroupAction, TimerAction)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node, SetRemap
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    bringup = get_package_share_directory('go2_bringup')
    nav2_params = LaunchConfiguration('nav2_params')
    map_yaml = LaunchConfiguration('map')

    default_urdf = os.path.join(
        get_package_share_directory('go2_description'), 'urdf', 'go2.urdf')
    robot_description = ParameterValue(
        Command(['xacro ', LaunchConfiguration('urdf_path')]), value_type=str)

    odom_topic = LaunchConfiguration('odom_topic')
    odom_frame = LaunchConfiguration('odom_frame')
    base_frame = LaunchConfiguration('base_frame')

    return LaunchDescription([
        DeclareLaunchArgument('nav2_params',
            default_value=os.path.join(bringup, 'config', 'nav2_params.yaml')),
        DeclareLaunchArgument('map',
            default_value=os.path.join(bringup, 'maps', 'sala1.yaml'),
            description='Zapisana mapa 2D dla AMCL (z mapping.launch.py + map_saver_cli).'),
        DeclareLaunchArgument('odom_topic', default_value='/utlidar/robot_odom',
            description='Odometria firmware Go2 (źródło dla odom_tf_relay -> TF odom->base_link).'),
        DeclareLaunchArgument('odom_frame', default_value='odom'),
        DeclareLaunchArgument('base_frame', default_value='base_link'),
        DeclareLaunchArgument('publish_odom_tf', default_value='true'),
        DeclareLaunchArgument('urdf_path', default_value=default_urdf),
        DeclareLaunchArgument('enable_robot_model', default_value='true',
            description='robot_state_publisher + lowstate_to_joint_states (TF + RViz model).'),
        DeclareLaunchArgument('cloud_topic', default_value='/utlidar/cloud_base',
            description='Źródło PointCloud2. cloud_base = firmware już w base_link '
                        '(zna montaż lidaru). MUSI być to samo co w mapping.'),
        DeclareLaunchArgument('pointcloud_start_delay', default_value='3.0',
            description='Opóźnienie (s) startu p2l — na static TF + RSP.'),
        DeclareLaunchArgument('lidar_frame_id', default_value='utlidar_lidar'),
        DeclareLaunchArgument('nav2_start_delay', default_value='6.0',
            description='Opóźnienie (s) startu Nav2 — MUSI być > pointcloud_start_delay '
                        '(/scan przed AMCL/costmapami).'),
        DeclareLaunchArgument('switch_to_normal', default_value='false',
            description='Most wysyła StandUp(1004)+BalanceStand(1002) na starcie (FSM w tryb '
                        'chodu PRZED Move). Ustaw true gdy Move odbija code=3202. '
                        'UWAGA: robot fizycznie WSTANIE na starcie.'),

        # robot_state_publisher: TF base_link -> linki URDF.
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             name='robot_state_publisher',
             parameters=[{'robot_description': robot_description}],
             condition=IfCondition(LaunchConfiguration('enable_robot_model'))),

        # /lowstate -> /joint_states.
        Node(package='go2_bridge', executable='lowstate_to_joint_states',
             name='lowstate_to_joint_states',
             condition=IfCondition(LaunchConfiguration('enable_robot_model'))),

        # Static TF base_link -> base (root URDF Go2).
        Node(package='tf2_ros', executable='static_transform_publisher',
             name='base_link_to_base_tf',
             arguments=['0', '0', '0', '0', '0', '0', '1', 'base_link', 'base'],
             condition=IfCondition(LaunchConfiguration('enable_robot_model'))),

        # Static TF base_link -> lidar (identity — cloud_base już w base_link).
        Node(package='tf2_ros', executable='static_transform_publisher',
             name='static_tf_lidar',
             arguments=['--x', '0.0', '--y', '0.0', '--z', '0.4',
                        '--frame-id', 'base_link',
                        '--child-frame-id', LaunchConfiguration('lidar_frame_id')]),

        # PointCloud2 -> 2D LaserScan (po opóźnieniu, żeby TF był gotowy).
        TimerAction(period=LaunchConfiguration('pointcloud_start_delay'), actions=[
            Node(package='pointcloud_to_laserscan', executable='pointcloud_to_laserscan_node',
                 name='pointcloud_to_laserscan',
                 parameters=[os.path.join(bringup, 'config', 'pointcloud_to_laserscan.yaml'),
                             {'queue_size': 50}],
                 remappings=[('cloud_in', LaunchConfiguration('cloud_topic')),
                             ('scan', '/scan')]),
        ]),

        # odom -> base_link TF z odometrii firmware.
        Node(package='go2_bringup', executable='odom_tf_relay', name='odom_tf_relay',
             condition=IfCondition(LaunchConfiguration('publish_odom_tf')),
             parameters=[{'odom_topic': odom_topic, 'odom_frame': odom_frame,
                          'base_frame': base_frame, 'use_msg_frame_ids': False,
                          'use_msg_stamp': False}]),

        # Nav2 (planner + controller + bt_navigator + AMCL). SetRemap: nav2 publikuje na
        # /cmd_vel_nav, żeby arbiter mógł je scalić i nałożyć limity.
        TimerAction(period=LaunchConfiguration('nav2_start_delay'), actions=[
            GroupAction([
                SetRemap(src='/cmd_vel', dst='/cmd_vel_nav'),
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(os.path.join(
                        get_package_share_directory('nav2_bringup'), 'launch', 'bringup_launch.py')),
                    launch_arguments={'map': map_yaml, 'use_sim_time': 'false',
                                      'params_file': nav2_params}.items()),
            ]),
        ]),

        # Arbiter cmd_vel: bierze WYGŁADZONY output nav2 (/cmd_vel_smoothed) + limity.
        Node(package='go2_bridge', executable='cmd_vel_arbiter', name='cmd_vel_arbiter',
             parameters=[os.path.join(
                             get_package_share_directory('go2_bridge'), 'config', 'safety.yaml'),
                         {'nav_topic': '/cmd_vel_smoothed'}]),

        # Most: /cmd_vel -> Unitree sport API (firmware). Caps zsynchronizowane z arbiter.
        Node(package='go2_bridge', executable='unitree_cmd_vel_bridge_node',
             name='unitree_cmd_vel_bridge_node',
             parameters=[{
                 'max_vx': 1.0, 'max_vy': 0.5, 'max_vyaw': 1.5,
                 'switch_to_normal': ParameterValue(
                     LaunchConfiguration('switch_to_normal'), value_type=bool),
             }]),
    ])
