"""W10: obraz z głowy R1 (RTP H.264 po UDP) -> /r1/camera/image_raw. Uruchom tam, dokąd dochodzi strumień.

Użycie:
    ros2 launch r1_basics camera.launch.py                     # port 5001 (1280x720)
    ros2 launch r1_basics camera.launch.py port:=5002          # lewe oko 544x448
    ros2 launch r1_basics camera.launch.py depth_device:=/dev/video-dep
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def setup(context):
    config = PathJoinSubstitution([FindPackageShare('r1_basics'), 'config', 'r1_basics.yaml'])
    overrides = {'port': int(LaunchConfiguration('port').perform(context))}
    for name in ('pipeline', 'depth_device'):
        value = LaunchConfiguration(name).perform(context)
        if value:
            overrides[name] = value
    return [Node(package='r1_basics', executable='camera', name='camera', output='screen',
                 emulate_tty=True, parameters=[config, overrides])]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('port', default_value='5001', description='port UDP strumienia RTP H.264'),
        DeclareLaunchArgument('pipeline', default_value='', description='własny potok GStreamer (może mieć {port})'),
        DeclareLaunchArgument('depth_device', default_value='', description='np. /dev/video-dep'),
        OpaqueFunction(function=setup),
    ])
