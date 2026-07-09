"""Mapowanie SLAM na realnym Unitree Go2 (slam_toolbox 2D).

Jeźdź robotem PILOTEM (RC) po sali, slam_toolbox buduje mapę z 2D-cięcia lidaru.
Zapisz mapę:
  ros2 run nav2_map_server map_saver_cli -f ~/maps/sala1

Potem podaj zapisany YAML do nav.launch.py (arg `map`).

Ten launch NIE startuje nav2/AMCL — to wyłącznie mapowanie. Ruch robota = sport API
firmware Unitree konsumujące /cmd_vel (most uruchom osobno lub jedź pilotem).

Drzewo TF:
  - odom -> base_link        : odom_tf_relay (z /utlidar/robot_odom firmware)
  - base_link -> linki URDF  : robot_state_publisher (go2_description)
  - base_link -> lidar       : static_transform_publisher
  - /joint_states            : lowstate_to_joint_states (z /lowstate)

KLUCZOWE: mapę buduj TYM SAMYM potokiem /scan, którym potem lokalizujesz (AMCL) —
ten launch i nav.launch.py dzielą pointcloud_to_laserscan.yaml, więc mapa jest spójna.

KLUCZOWE (Jazzy): slam_toolbox to węzeł LIFECYCLE — bez lifecycle_manager (autostart)
startuje UNCONFIGURED i nie mapuje. QoS: p2l publikuje /scan best_effort, slam chce
reliable → scan_qos_relay republikuje /scan -> /scan_reliable.
"""
from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    bringup = get_package_share_directory('go2_bringup')
    default_urdf = os.path.join(
        get_package_share_directory('go2_description'), 'urdf', 'go2.urdf')

    robot_description = ParameterValue(
        Command(['xacro ', LaunchConfiguration('urdf_path')]), value_type=str)

    cloud_topic = LaunchConfiguration('cloud_topic')
    scan_topic = LaunchConfiguration('scan_topic')
    odom_topic = LaunchConfiguration('odom_topic')
    odom_frame = LaunchConfiguration('odom_frame')
    base_frame = LaunchConfiguration('base_frame')
    lidar_frame = LaunchConfiguration('lidar_frame_id')
    enable_robot_model = IfCondition(LaunchConfiguration('enable_robot_model'))

    return LaunchDescription([
        DeclareLaunchArgument('urdf_path', default_value=default_urdf,
            description='Ścieżka do URDF Go2 (domyślnie vendored go2_description).'),
        DeclareLaunchArgument('enable_robot_model', default_value='true',
            description='robot_state_publisher + lowstate_to_joint_states (TF + RViz model). '
                        'false = headless (slam i tak działa, znika tylko model).'),
        DeclareLaunchArgument('cloud_topic', default_value='/utlidar/cloud_base',
            description='Źródło PointCloud2. /utlidar/cloud_base = firmware już w base_link '
                        '(zna montaż lidaru, bez ręcznej kalibracji). MUSI być to samo co w nav.'),
        DeclareLaunchArgument('scan_topic', default_value='/scan_reliable',
            description='LaserScan dla slam_toolbox. /scan_reliable (NIE /scan): p2l publikuje '
                        'best_effort, slam chce reliable → scan_qos_relay /scan -> /scan_reliable.'),
        DeclareLaunchArgument('odom_topic', default_value='/utlidar/robot_odom',
            description='Odometria firmware Go2 (źródło dla odom_tf_relay -> TF odom->base_link).'),
        DeclareLaunchArgument('odom_frame', default_value='odom'),
        DeclareLaunchArgument('base_frame', default_value='base_link'),
        DeclareLaunchArgument('lidar_frame_id', default_value='utlidar_lidar'),
        DeclareLaunchArgument('publish_odom_tf', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='true',
            description='Auto-start RViz z presetem mapping.rviz (gotowe QoS). false = bez.'),

        # robot_state_publisher: TF base_link -> linki URDF.
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             name='robot_state_publisher',
             parameters=[{'robot_description': robot_description}],
             condition=enable_robot_model),

        # /lowstate -> /joint_states (żywe kąty stawów dla RSP).
        Node(package='go2_bridge', executable='lowstate_to_joint_states',
             name='lowstate_to_joint_states', condition=enable_robot_model),

        # Static TF base_link -> base (root URDF Go2 to `base`; reszta stacka na base_link).
        Node(package='tf2_ros', executable='static_transform_publisher',
             name='base_link_to_base_tf',
             arguments=['0', '0', '0', '0', '0', '0', '1', 'base_link', 'base'],
             condition=enable_robot_model),

        # Static TF base_link -> lidar (identity — cloud_base jest już w base_link).
        Node(package='tf2_ros', executable='static_transform_publisher',
             name='base_to_lidar_static_tf',
             arguments=['--x', '0.0', '--y', '0.0', '--z', '0.0',
                        '--frame-id', base_frame, '--child-frame-id', lidar_frame]),

        # odom -> base_link TF z odometrii firmware.
        Node(package='go2_bringup', executable='odom_tf_relay', name='odom_tf_relay',
             condition=IfCondition(LaunchConfiguration('publish_odom_tf')),
             parameters=[{'odom_topic': odom_topic, 'odom_frame': odom_frame,
                          'base_frame': base_frame, 'use_msg_frame_ids': False,
                          'use_msg_stamp': True}]),

        # Relay QoS: /scan (best_effort) -> /scan_reliable (reliable dla slam).
        Node(package='go2_bringup', executable='scan_qos_relay', name='scan_qos_relay',
             arguments=['--in', '/scan', '--out', '/scan_reliable']),

        # PointCloud2 -> 2D LaserScan.
        Node(package='pointcloud_to_laserscan', executable='pointcloud_to_laserscan_node',
             name='pointcloud_to_laserscan',
             parameters=[os.path.join(bringup, 'config', 'pointcloud_to_laserscan.yaml'),
                         {'queue_size': 50}],
             remappings=[('cloud_in', cloud_topic), ('scan', '/scan')]),

        # slam_toolbox (mapowanie).
        Node(package='slam_toolbox', executable='async_slam_toolbox_node',
             name='slam_toolbox', output='screen',
             parameters=[os.path.join(bringup, 'config', 'slam_toolbox_mapping.yaml'),
                         {'scan_topic': scan_topic, 'odom_frame': odom_frame,
                          'base_frame': base_frame}]),

        # Jazzy: slam_toolbox = lifecycle → autostart przez lifecycle_manager.
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_slam', output='screen',
             parameters=[{'autostart': True, 'node_names': ['slam_toolbox'],
                          'bond_timeout': 0.0}]),

        # RViz z presetem mapowania (Fixed Frame=map, QoS gotowe).
        Node(package='rviz2', executable='rviz2', name='rviz2_mapping',
             arguments=['-d', os.path.join(bringup, 'rviz', 'mapping.rviz')],
             additional_env={'LIBGL_ALWAYS_SOFTWARE': '1'},
             condition=IfCondition(LaunchConfiguration('rviz'))),
    ])
