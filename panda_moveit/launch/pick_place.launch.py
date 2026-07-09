"""W8 — stos pod pick & place z moveit_py (wzorzec: oficjalny tutorial MoveIt 2
'Motion Planning Python API', dopasowany do moveit_resources_panda na Jazzy).

Wstaje: robot_state_publisher + ros2_control (mock hardware) + kontrolery + RViz.
Node z sekwencją odpalasz OSOBNO (drugi terminal):  ros2 run panda_moveit pick_place

UWAGA (uczciwie): konfiguracja moveit_py bywa wrażliwa na wersje paczek —
przetestuj pełny scenariusz przed zajęciami (lekcja z Gdyni).
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    pkg = get_package_share_directory('panda_moveit')
    panda_cfg_share = get_package_share_directory('moveit_resources_panda_moveit_config')

    moveit_config = (
        MoveItConfigsBuilder(robot_name='panda', package_name='moveit_resources_panda_moveit_config')
        .trajectory_execution(file_path=os.path.join(panda_cfg_share, 'config', 'gripper_moveit_controllers.yaml'))
        .moveit_cpp(file_path=os.path.join(pkg, 'config', 'moveit_cpp.yaml'))
        .to_moveit_configs()
    )

    # TF z URDF (M7): robot_description -> drzewo frame'ów
    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='log',
        parameters=[moveit_config.robot_description],
    )

    # ros2_control z mock hardware + kontrolery (jak w demo.launch.py z W7)
    ros2_control = Node(
        package='controller_manager',
        executable='ros2_control_node',
        output='log',
        parameters=[
            moveit_config.robot_description,
            os.path.join(panda_cfg_share, 'config', 'ros2_controllers.yaml'),
        ],
    )
    spawners = [
        Node(package='controller_manager', executable='spawner', arguments=[c], output='log')
        for c in ('joint_state_broadcaster', 'panda_arm_controller', 'panda_hand_controller')
    ]

    # Podgląd sceny i ruchu (dodaj display: PlanningScene + Trajectory).
    # rviz:=false na maszynach bez GUI (np. headless test / komputer pokładowy).
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        output='log',
        arguments=['-d', os.path.join(panda_cfg_share, 'launch', 'moveit.rviz')],
        parameters=[moveit_config.robot_description, moveit_config.robot_description_semantic],
        condition=IfCondition(LaunchConfiguration('rviz')),
    )

    return LaunchDescription([
        DeclareLaunchArgument('rviz', default_value='true', description='Odpal RViz (false = headless).'),
        rsp, ros2_control, *spawners, rviz,
    ])
