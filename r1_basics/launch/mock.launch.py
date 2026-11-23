"""Makieta R1 (bez robota).

Użycie: ros2 launch r1_basics mock.launch.py [fsm:=4] [reply_code:=127] [imu_yaw_bias:=0.02]
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    config = PathJoinSubstitution([FindPackageShare('r1_basics'), 'config', 'r1_basics.yaml'])
    return LaunchDescription([
        DeclareLaunchArgument('fsm', default_value='811', description='FSM na starcie: 811 chód, 4 stanie'),
        DeclareLaunchArgument('reply_code', default_value='0',
                              description='kod odpowiedzi na 7105 (127 = jak w zgłoszeniach społeczności)'),
        DeclareLaunchArgument('imu_yaw_bias', default_value='0.0', description='dryf kursu IMU [rad/s]'),
        Node(package='r1_basics', executable='r1_mock', name='r1_mock', output='screen', emulate_tty=True,
             parameters=[config, {'fsm': LaunchConfiguration('fsm'),
                                  'reply_code': LaunchConfiguration('reply_code'),
                                  'imu_yaw_bias': LaunchConfiguration('imu_yaw_bias')}]),
    ])
