import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import xacro


def generate_launch_description():
    pkg = get_package_share_directory('m6_urdf')
    xacro_file = os.path.join(pkg, 'urdf', 'simple_arm.urdf.xacro')
    robot_desc = xacro.process_file(xacro_file).toxml()

    return LaunchDescription([
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': robot_desc}]),
        Node(package='m6_urdf', executable='joint_oscillator', name='oscillator'),
    ])
