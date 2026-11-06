"""W8 - stos pod pick & place z moveit_py na Franka Research 3 (FR3).

To samo co moveit.launch.py z W7, ale BEZ move_groupa (w W8 "move_groupem" jest Twój
skrypt z MoveItPy) i z RViz bez panelu MotionPlanning (config/pick_place.rviz):
  robot_state_publisher + ros2_control (fr3_arm_controller, joint_state_broadcaster)
  + joint_state_publisher (ramię + chwytak -> /joint_states) + chwytak + RViz.

Bez robota (domyślnie):
    ros2 launch fr3_moveit pick_place.launch.py
Z prawdziwym FR3 (FCI włączone w Desk, kabel LAN, jądro RT):
    ros2 launch fr3_moveit pick_place.launch.py robot_ip:=<IP_ROBOTA> use_fake_hardware:=false

Node z sekwencją odpalasz OSOBNO (drugi terminal):  ros2 run fr3_moveit pick_place
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg = get_package_share_directory('fr3_moveit')
    args = [
        DeclareLaunchArgument('robot_ip', default_value='dont-care',
                              description='IP robota (FCI). Przy fake hardware bez znaczenia.'),
        DeclareLaunchArgument('use_fake_hardware', default_value='true',
                              description='true = symulacja bez robota, false = prawdziwy FR3.'),
        DeclareLaunchArgument('use_rviz', default_value='true',
                              description='Odpal RViz (false = headless).'),
    ]
    stack = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg, 'launch', 'moveit.launch.py')),
        launch_arguments={
            'robot_ip': LaunchConfiguration('robot_ip'),
            'use_fake_hardware': LaunchConfiguration('use_fake_hardware'),
            'use_rviz': LaunchConfiguration('use_rviz'),
            'use_move_group': 'false',
            'rviz_config': os.path.join(pkg, 'config', 'pick_place.rviz'),
        }.items(),
    )
    return LaunchDescription(args + [stack])
