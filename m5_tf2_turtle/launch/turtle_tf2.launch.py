from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node


def generate_launch_description():
    spawn_turtle2 = ExecuteProcess(
        cmd=['ros2', 'service', 'call', '/spawn', 'turtlesim/srv/Spawn',
             '{x: 4.0, y: 2.0, theta: 0.0, name: turtle2}'],
        output='screen',
    )
    return LaunchDescription([
        Node(package='turtlesim', executable='turtlesim_node', name='turtlesim'),
        TimerAction(period=2.0, actions=[spawn_turtle2]),
        Node(package='m5_tf2_turtle', executable='tf_broadcaster',
             name='br_turtle1', parameters=[{'turtle_name': 'turtle1'}]),
        TimerAction(period=3.0, actions=[
            Node(package='m5_tf2_turtle', executable='tf_broadcaster',
                 name='br_turtle2', parameters=[{'turtle_name': 'turtle2'}]),
            Node(package='m5_tf2_turtle', executable='tf_follower', name='follower'),
        ]),
    ])
