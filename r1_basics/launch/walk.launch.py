"""W9: most /cmd_vel -> sport API + odometria zliczeniowa + dojazd do punktu.

Użycie:
    ros2 launch r1_basics walk.launch.py use_mock:=true goal_x:=1.5 goal_y:=0.8   # makieta
    ros2 launch r1_basics walk.launch.py                                           # robot (cel z RViz /goal_pose)
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def node(executable, params):
    return Node(package='r1_basics', executable=executable, name=executable, output='screen',
                emulate_tty=True, parameters=params)


def setup(context):
    config = PathJoinSubstitution([FindPackageShare('r1_basics'), 'config', 'r1_basics.yaml'])
    use_mock = LaunchConfiguration('use_mock').perform(context).lower() in ('true', '1', 'yes')
    goal_x = LaunchConfiguration('goal_x').perform(context)
    goal_y = LaunchConfiguration('goal_y').perform(context)
    goto_params = [config]
    if goal_x and goal_y:
        goto_params.append({'goal_x': float(goal_x), 'goal_y': float(goal_y)})
    actions = [node('cmd_vel_bridge', [config]), node('dead_reckoning', [config]),
               node('goto_point', goto_params)]
    if use_mock:
        bias = float(LaunchConfiguration('imu_yaw_bias').perform(context))
        actions.insert(0, node('r1_mock', [config, {'imu_yaw_bias': bias}]))
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('use_mock', default_value='false',
                              description='true = makieta r1_mock zamiast robota'),
        DeclareLaunchArgument('goal_x', default_value='',
                              description='cel x [m] w odom (puste = czekaj na /goal_pose)'),
        DeclareLaunchArgument('goal_y', default_value='', description='cel y [m] w odom'),
        DeclareLaunchArgument('imu_yaw_bias', default_value='0.0', description='makieta: dryf kursu IMU [rad/s]'),
        OpaqueFunction(function=setup),
    ])
