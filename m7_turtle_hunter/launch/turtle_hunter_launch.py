from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    # Parametry strojenia huntera - nadpisz je przy launchu, np.:
    #   ros2 launch m7_turtle_hunter turtle_hunter_launch.py kp_angular:=4.0 max_linear:=3.0
    # (na żywo, już uruchomione:  ros2 param set /hunter kp_angular 4.0)
    return LaunchDescription([
        DeclareLaunchArgument('kp_linear', default_value='1.5',
                              description='wzmocnienie prędkości liniowej (dojazd do ofiary)'),
        DeclareLaunchArgument('kp_angular', default_value='6.0',
                              description='wzmocnienie skrętu (za wysokie = oscylacje)'),
        DeclareLaunchArgument('max_linear', default_value='2.5',
                              description='limit prędkości liniowej (za wysoki = przestrzeliwanie)'),

        Node(
            package='turtlesim',
            executable='turtlesim_node',
            name='turtlesim',
        ),
        Node(
            package='m7_turtle_hunter',
            executable='game_manager_node',
            name='game_manager',
        ),
        Node(
            package='m7_turtle_hunter',
            executable='hunter_node',
            name='hunter',
            parameters=[{
                'kp_linear': ParameterValue(LaunchConfiguration('kp_linear'), value_type=float),
                'kp_angular': ParameterValue(LaunchConfiguration('kp_angular'), value_type=float),
                'max_linear': ParameterValue(LaunchConfiguration('max_linear'), value_type=float),
            }],
        ),
    ])
