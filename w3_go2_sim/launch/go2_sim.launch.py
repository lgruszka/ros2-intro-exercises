"""Warsztat W3 (wariant Go2) - symulacja Unitree Go2 w Gazebo Harmonic.

Uruchom (Terminal 1):
    ros2 launch w3_go2_sim go2_sim.launch.py
Opcje:
    gui:=false    - Gazebo bez okna (oszczędza CPU/GPU; symulacja działa tak samo)
    rviz:=true    - od razu otwiera RViz z konfiguracją warsztatu

CO URUCHAMIA TEN LAUNCH:
1. Gazebo Harmonic ze światem worlds/go2_room.sdf (sala 12 x 10 m z przeszkodami).
2. Model Go2 z repo khaledgabr77/unitree_go2_ros2 (pakiety unitree_go2_description
   i unitree_go2_sim) - tylko z lidarem Velodyne VLP-16 (kamery i lidar L1 wyłączone,
   żeby odciążyć komputer).
3. Kontroler chodu CHAMP (quadruped_controller_node): słucha /cmd_vel (Twist)
   i generuje ruch nóg przez ros2_control.
4. Estymację stanu CHAMP + dwa filtry EKF (robot_localization):
   odom -> base_footprint -> base_link, odometria na topicu /odom.
5. pointcloud_to_laserscan: chmura 3D /velodyne_points/points -> 2D /scan
   (SLAM i AMCL potrzebują 2D LaserScan).

Czym różni się od stockowego unitree_go2_launch.py:
- NIE publikuje statycznej transformacji map -> odom. W oryginale jest tam
  static_transform_publisher, który kłóci się z slam_toolbox i AMCL (oba same
  publikują map -> odom). Dwa źródła tej samej ramki = skaczący robot w RViz.
- dokłada /scan (pointcloud_to_laserscan) i własny świat ze ścianami,
- argument gui działa (w oryginale jest zadeklarowany, ale nieużywany).
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node, SetParameter


def generate_launch_description():
    pkg = get_package_share_directory('w3_go2_sim')
    go2_sim = get_package_share_directory('unitree_go2_sim')
    go2_desc = get_package_share_directory('unitree_go2_description')
    champ_base = get_package_share_directory('champ_base')
    ros_gz_sim = get_package_share_directory('ros_gz_sim')

    joints_config = os.path.join(go2_sim, 'config', 'joints', 'joints.yaml')
    links_config = os.path.join(go2_sim, 'config', 'links', 'links.yaml')
    gait_config = os.path.join(go2_sim, 'config', 'gait', 'gait.yaml')
    ros_control_config = os.path.join(go2_sim, 'config', 'ros_control', 'ros_control.yaml')
    xacro_file = os.path.join(go2_desc, 'urdf', 'unitree_go2_robot.xacro')

    world = LaunchConfiguration('world')
    gui = LaunchConfiguration('gui')
    rviz = LaunchConfiguration('rviz')

    # Opis robota: tylko Velodyne (lidar 3D). Kamera, D455 i lidar L1 wyłączone.
    description = Command([
        'xacro ', xacro_file,
        ' robot_controllers:=', ros_control_config,
        ' command_interface:=effort',
        ' disable_camera:=true disable_d455:=true disable_lidar_l1:=true',
        ' disable_velodyne_lidar:=false',
    ])

    # -r = start od razu (bez pauzy); -s = sam serwer, bez okna
    gz_args = PythonExpression([
        "'", world, " -r' if '", gui, "' == 'true' else '", world, " -r -s'"])

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': gz_args}.items(),
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': description}],
    )

    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=['-name', 'go2', '-topic', 'robot_description',
                   '-x', '0.0', '-y', '0.0', '-z', '0.375', '-Y', '0.0'],
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='gazebo_bridge',
        output='screen',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/imu/data@sensor_msgs/msg/Imu[gz.msgs.IMU',
            '/odom/ground_truth@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            '/lf_foot_contacts@ros_gz_interfaces/msg/Contacts[gz.msgs.Contacts',
            '/rf_foot_contacts@ros_gz_interfaces/msg/Contacts[gz.msgs.Contacts',
            '/lh_foot_contacts@ros_gz_interfaces/msg/Contacts[gz.msgs.Contacts',
            '/rh_foot_contacts@ros_gz_interfaces/msg/Contacts[gz.msgs.Contacts',
            '/velodyne_points/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
        ],
    )

    quadruped_controller = Node(
        package='champ_base',
        executable='quadruped_controller_node',
        output='screen',
        parameters=[
            {'gazebo': True},
            {'publish_joint_states': True},
            {'publish_joint_control': True},
            {'publish_foot_contacts': False},
            {'joint_controller_topic': 'joint_group_effort_controller/joint_trajectory'},
            {'urdf': description},
            joints_config, links_config, gait_config,
            {'hardware_connected': False},
            {'close_loop_odom': True},
        ],
        remappings=[('/cmd_vel/smooth', '/cmd_vel')],
    )

    foot_contacts = Node(
        package='unitree_application',
        executable='foot_contacts_bridge',
        output='screen',
    )

    state_estimator = Node(
        package='champ_base',
        executable='state_estimation_node',
        output='screen',
        parameters=[
            {'orientation_from_imu': True},
            {'urdf': description},
            joints_config, links_config, gait_config,
        ],
    )

    ekf_base = Node(
        package='robot_localization',
        executable='ekf_node',
        name='base_to_footprint_ekf',
        output='screen',
        parameters=[os.path.join(champ_base, 'config', 'ekf', 'base_to_footprint.yaml')],
        remappings=[('odometry/filtered', 'odom/local')],
    )

    ekf_odom = Node(
        package='robot_localization',
        executable='ekf_node',
        name='footprint_to_odom_ekf',
        output='screen',
        parameters=[os.path.join(champ_base, 'config', 'ekf', 'footprint_to_odom.yaml')],
        remappings=[('odometry/filtered', 'odom')],
    )

    cloud_to_scan = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pointcloud_to_laserscan',
        output='screen',
        parameters=[os.path.join(pkg, 'params', 'pointcloud_to_laserscan.yaml')],
        remappings=[('cloud_in', '/velodyne_points/points'), ('scan', '/scan')],
    )

    # Kontrolery ros2_control startują z opóźnieniem - Gazebo musi najpierw
    # wczytać robota (na słabszym laptopie trwa to kilkanaście sekund).
    spawner_js = TimerAction(period=15.0, actions=[Node(
        package='controller_manager', executable='spawner', output='screen',
        arguments=['--controller-manager-timeout', '120', 'joint_states_controller'])])
    spawner_effort = TimerAction(period=20.0, actions=[Node(
        package='controller_manager', executable='spawner', output='screen',
        arguments=['--controller-manager-timeout', '120', 'joint_group_effort_controller'])])

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', os.path.join(pkg, 'rviz', 'go2_nav.rviz')],
        condition=IfCondition(rviz),
    )

    return LaunchDescription([
        DeclareLaunchArgument('world', default_value=os.path.join(pkg, 'worlds', 'go2_room.sdf'),
                              description='Plik świata Gazebo (.sdf)'),
        DeclareLaunchArgument('gui', default_value='true',
                              description='true = okno Gazebo, false = sam serwer (lżej)'),
        DeclareLaunchArgument('rviz', default_value='false',
                              description='true = od razu otwórz RViz'),
        # Wszystkie nodes (węzły) tego launcha używają zegara symulacji (/clock)
        SetParameter(name='use_sim_time', value=True),
        gazebo,
        robot_state_publisher,
        spawn,
        bridge,
        quadruped_controller,
        foot_contacts,
        state_estimator,
        ekf_base,
        ekf_odom,
        cloud_to_scan,
        spawner_js,
        spawner_effort,
        rviz_node,
    ])
