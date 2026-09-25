"""Model 3-DoF ramienia: robot_state_publisher + źródło /joint_states (+ opcjonalnie RViz).

  ros2 launch m6_urdf display_arm.launch.py              # ramię porusza się samo (joint_oscillator)
  ros2 launch m6_urdf display_arm.launch.py gui:=true    # suwaki joint_state_publisher_gui zamiast oscylatora
  ros2 launch m6_urdf display_arm.launch.py rviz:=true   # dodatkowo uruchamia rviz2

Zawsze działa tylko JEDNO źródło /joint_states (oscylator ALBO suwaki), inaczej model skacze.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro


def generate_launch_description():
    pkg = get_package_share_directory('m6_urdf')
    xacro_file = os.path.join(pkg, 'urdf', 'simple_arm.urdf.xacro')

    # xacro.process_file ROZWIJA makra/parametry -> czysty URDF.
    # (open(path).read() podałby SUROWY xacro z ${...}, którego
    #  robot_state_publisher NIE rozumie -> błąd parsowania.)
    robot_desc = xacro.process_file(xacro_file).toxml()

    gui = LaunchConfiguration('gui')
    rviz = LaunchConfiguration('rviz')

    return LaunchDescription([
        DeclareLaunchArgument(
            'gui', default_value='false',
            description='true = suwaki joint_state_publisher_gui zamiast joint_oscillator'),
        DeclareLaunchArgument(
            'rviz', default_value='false',
            description='true = uruchom też rviz2 (Fixed Frame ustaw na base_link)'),

        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': robot_desc}], output='screen'),

        # źródło /joint_states: oscylator (domyślnie) ALBO okno z suwakami
        Node(package='m6_urdf', executable='joint_oscillator', name='oscillator',
             condition=UnlessCondition(gui)),
        Node(package='joint_state_publisher_gui', executable='joint_state_publisher_gui',
             condition=IfCondition(gui)),

        Node(package='rviz2', executable='rviz2', condition=IfCondition(rviz)),
    ])
