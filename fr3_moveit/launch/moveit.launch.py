"""W7 - MoveIt 2 na Franka Research 3 (FR3): move_group + RViz (MotionPlanning) + ros2_control.

Odpowiednik oficjalnego franka_fr3_moveit_config/launch/moveit.launch.py (te same pliki
URDF/SRDF/kinematyki z franka_ros2, ten sam xacro z fake hardware) z dwiema zmianami
dla symulacji (use_fake_hardware:=true, domyślnie):
  1. fr3_arm_controller na interfejsie POSITION (config/fr3_fake_ros_controllers.yaml).
     Oficjalny kontroler EFFORT na fake hardware planuje i "wykonuje", ale ramię stoi.
  2. Zastępczy chwytak (fr3_moveit/fake_gripper.py) z serwerem akcji, bo fake hardware
     franka_ros2 publikuje tylko stały stan palców.
Z prawdziwym FR3 (use_fake_hardware:=false) wstają oficjalne kontrolery i franka_gripper_node.

    ros2 launch fr3_moveit moveit.launch.py                      # bez robota
    ros2 launch fr3_moveit moveit.launch.py robot_ip:=<IP> use_fake_hardware:=false
Argument use_move_group:=false zostawia samą infrastrukturę (tak robi pick_place.launch.py w W8).
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder
import xacro


def moveit_config():
    """Ta sama konfiguracja, którą w W8 składa build_config() w pick_place.py."""
    bringup = get_package_share_directory('franka_bringup')
    description = get_package_share_directory('franka_description')
    fr3_cfg = get_package_share_directory('franka_fr3_moveit_config')
    return (
        MoveItConfigsBuilder(robot_name='fr3', package_name='fr3_moveit')
        .robot_description(file_path=os.path.join(bringup, 'urdf', 'franka_arm.urdf.xacro'),
                           mappings={'robot_type': 'fr3', 'hand': 'true', 'ee_id': 'franka_hand'})
        .robot_description_semantic(file_path=os.path.join(description, 'robots', 'fr3', 'fr3.srdf.xacro'),
                                    mappings={'hand': 'true', 'ee_id': 'franka_hand'})
        .robot_description_kinematics(file_path=os.path.join(fr3_cfg, 'config', 'kinematics.yaml'))
        .joint_limits(file_path=os.path.join(fr3_cfg, 'config', 'fr3_joint_limits.yaml'))
        .trajectory_execution(file_path='config/moveit_controllers.yaml')
        .planning_pipelines(pipelines=['ompl'])
        .to_moveit_configs()
    )


def launch_setup(context):
    pkg = get_package_share_directory('fr3_moveit')
    fr3_cfg = get_package_share_directory('franka_fr3_moveit_config')
    robot_ip = context.launch_configurations['robot_ip']
    fake = context.launch_configurations['use_fake_hardware'].lower() == 'true'
    use_rviz = context.launch_configurations['use_rviz'].lower() == 'true'
    use_move_group = context.launch_configurations['use_move_group'].lower() == 'true'
    rviz_config = context.launch_configurations['rviz_config']

    # URDF z ros2_control: ten sam xacro i te same argumenty co oficjalny moveit.launch.py
    urdf = xacro.process_file(
        os.path.join(get_package_share_directory('franka_bringup'), 'urdf', 'franka_arm.urdf.xacro'),
        mappings={'robot_type': 'fr3', 'hand': 'true', 'ee_id': 'franka_hand', 'robot_ip': robot_ip,
                  'use_fake_hardware': 'true' if fake else 'false', 'fake_sensor_commands': 'false'},
    ).toxml()
    robot_description = {'robot_description': urdf}
    cfg = moveit_config()

    controllers_yaml = (os.path.join(pkg, 'config', 'fr3_fake_ros_controllers.yaml') if fake
                        else os.path.join(fr3_cfg, 'config', 'fr3_ros_controllers.yaml'))
    nodes = [
        # TF z URDF (M7)
        Node(package='robot_state_publisher', executable='robot_state_publisher', output='log',
             parameters=[robot_description]),
        # ros2_control: fake hardware (mock_components) albo FrankaHardwareInterface (FCI)
        Node(package='controller_manager', executable='ros2_control_node', output='log',
             parameters=[robot_description, controllers_yaml],
             remappings=[('joint_states', 'franka/joint_states')], on_exit=Shutdown()),
        # /joint_states = ramię (franka/joint_states) + palce (franka_gripper/joint_states)
        Node(package='joint_state_publisher', executable='joint_state_publisher', output='log',
             parameters=[{'source_list': ['franka/joint_states', 'franka_gripper/joint_states'],
                          'rate': 30}]),
    ]
    for c in ('fr3_arm_controller', 'joint_state_broadcaster'):
        nodes.append(Node(package='controller_manager', executable='spawner', output='log',
                          arguments=[c, '--controller-manager-timeout', '60']))
    if fake:
        # zastępczy chwytak: ~/joint_states + akcje gripper_action, move, grasp
        nodes.append(Node(package='fr3_moveit', executable='fake_gripper', name='franka_gripper',
                          output='log'))
    else:
        nodes.append(Node(package='controller_manager', executable='spawner', output='log',
                          arguments=['franka_robot_state_broadcaster']))
        nodes.append(IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(
                get_package_share_directory('franka_gripper'), 'launch', 'gripper.launch.py')),
            launch_arguments={'robot_ip': robot_ip, 'use_fake_hardware': 'false',
                              'namespace': ''}.items()))
    if use_move_group:
        nodes.append(Node(package='moveit_ros_move_group', executable='move_group', output='screen',
                          parameters=[cfg.to_dict()]))
    if use_rviz:
        # moveit.rviz = oficjalny widok franka_fr3_moveit_config z włączonym od razu MotionPlanning
        rviz_file = rviz_config or os.path.join(pkg, 'config', 'moveit.rviz' if use_move_group
                                                else 'pick_place.rviz')
        nodes.append(Node(package='rviz2', executable='rviz2', output='log',
                          arguments=['-d', rviz_file],
                          parameters=[cfg.robot_description, cfg.robot_description_semantic,
                                      cfg.robot_description_kinematics, cfg.planning_pipelines,
                                      cfg.joint_limits]))
    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('robot_ip', default_value='dont-care',
                              description='IP robota (FCI). Przy fake hardware bez znaczenia.'),
        DeclareLaunchArgument('use_fake_hardware', default_value='true',
                              description='true = symulacja bez robota, false = prawdziwy FR3.'),
        DeclareLaunchArgument('use_rviz', default_value='true',
                              description='Odpal RViz (false = headless).'),
        DeclareLaunchArgument('use_move_group', default_value='true',
                              description='false = bez move_group (W8: "move_groupem" jest skrypt moveit_py).'),
        DeclareLaunchArgument('rviz_config', default_value='',
                              description='Własny plik .rviz (puste = domyślny dla trybu).'),
        OpaqueFunction(function=launch_setup),
    ])
