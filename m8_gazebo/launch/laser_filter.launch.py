"""Box laser-filter: /scan -> /scan_filtered (wycina bryłę robota). Węzeł STANDALONE.

UWAGA: `slam.launch.py` ORAZ `explore.launch.py` JUŻ odpalają ten filtr w środku — przy
mapowaniu (tryb 1) i eksploracji (tryb 3) NIE musisz go uruchamiać osobno (i nie uruchamiaj,
bo będą dwa węzły o tej samej nazwie). Ten launch jest do:
  - nauki/diagnostyki (zobaczyć /scan_filtered niezależnie od SLAM),
  - ścieżki nav-only, gdyby ktoś chciał karmić costmapy /scan_filtered.

Filtr potrzebny TAKŻE w symulacji: lidar ROSbota XL w Gazebo widzi własną konstrukcję ~5 cm
(~100 pkt @ 0.066-0.2 m). Bez filtra SLAM rysuje pierścień przeszkód wokół robota → komórka
startowa "lethal" → planner nie rusza → robot kręci się w kółko. (To NIE jest artefakt tylko
realnego RPLIDAR-a — w Gazebo dzieje się to samo.)
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    cfg = os.path.join(
        get_package_share_directory('m8_gazebo'), 'config', 'laser_filter.yaml')
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
