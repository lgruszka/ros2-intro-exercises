"""W12: polityka chodu R1 jako sterownik niskiego poziomu (r1_policy: /cmd_vel + /lowstate -> /lowcmd).

!!! NA PRAWDZIWYM R1 TYLKO NA SZUBIENICY Z PODWIESZONYM I ASEKUROWANYM ROBOTEM (tryb debug Unitree) !!!

Symulacja (robot startuje zawieszony na wirtualnej szubienicy):
    ros2 launch r1_basics policy.launch.py sim_dir:=$HOME/r1_policy use_sim:=true [cmd_delay_ms:=20]
Robot (tylko r1_policy; robot w trybie debug, na szubienicy, CycloneDDS jak w W9):
    ros2 launch r1_basics policy.launch.py sim_dir:=$HOME/r1_policy use_sim:=false
"""
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def setup(context):
    config = PathJoinSubstitution([FindPackageShare('r1_basics'), 'config', 'r1_basics.yaml'])
    sim_dir = os.path.expanduser(LaunchConfiguration('sim_dir').perform(context))
    use_sim = LaunchConfiguration('use_sim').perform(context).lower() in ('true', '1', 'yes')
    policy = os.path.join(sim_dir, LaunchConfiguration('policy_file').perform(context))
    actions = [Node(package='r1_basics', executable='r1_policy', name='r1_policy', output='screen', emulate_tty=True,
                    parameters=[config, {'policy': policy}])]
    if use_sim:
        actions.insert(0, Node(
            package='r1_basics', executable='r1_sim', name='r1_sim', output='screen', emulate_tty=True,
            parameters=[config, {'interface': 'lowcmd', 'rate_hz': 200.0,
                                 'model': os.path.join(sim_dir, 'scene', 'scene.xml'), 'policy': policy,
                                 'meta': os.path.join(sim_dir, 'sim_meta.json'),
                                 'gantry': LaunchConfiguration('gantry').perform(context).lower() in ('true', '1'),
                                 'cmd_delay_ms': float(LaunchConfiguration('cmd_delay_ms').perform(context))}]))
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('sim_dir', description='katalog z policy.onnx (i scene/, sim_meta.json dla symulacji)'),
        DeclareLaunchArgument('policy_file', default_value='policy.onnx',
                              description='plik polityki w sim_dir (pakiet: policy_delay.onnx = odporna na opóźnienie)'),
        DeclareLaunchArgument('use_sim', default_value='true', description='true = r1_sim w trybie lowcmd'),
        DeclareLaunchArgument('gantry', default_value='true', description='symulacja: wirtualna szubienica'),
        DeclareLaunchArgument('cmd_delay_ms', default_value='0.0', description='symulacja: opóźnienie /lowcmd [ms]'),
        OpaqueFunction(function=setup),
    ])
