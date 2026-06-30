"""Box laser-filter: /scan -> /scan_filtered (wycina bryłę robota). Węzeł STANDALONE.

UWAGA: slam.launch.py, nav.launch.py ORAZ explore.launch.py JUŻ odpalają ten filtr w środku —
przy normalnej pracy NIE uruchamiaj go osobno (byłyby dwa węzły o tej samej nazwie). Ten launch
jest tylko do diagnostyki: zobaczyć /scan_filtered niezależnie i porównać z /scan.

Filtr wycina ~5 cm bryły robota (RPLIDAR montowany nisko widzi własną konstrukcję). Bez tego SLAM
rysuje pierścień przeszkód, a collision_monitor (na realu WŁĄCZONY) fałszywie hamuje.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    cfg = os.path.join(
        get_package_share_directory('rosbot_nav'), 'config', 'laser_filter.yaml')
    return LaunchDescription([
        Node(
            package='laser_filters',
            executable='scan_to_scan_filter_chain',
            name='scan_to_scan_filter_chain',
            output='screen',
            parameters=[cfg],
            # domyślnie: subskrybuje /scan, publikuje /scan_filtered
        ),
    ])
