"""M10 — demo pipeline'u percepcji: toy_camera + detektor (ROZWIĄZANIE).

Konwencja repo: launch odpala solution, żeby demo działało od razu po buildzie.
Twoja praca to color_detector_skeleton.py (ros2 run m10_perception color_detector).

Podgląd obrazu z adnotacją: ros2 run rqt_image_view rqt_image_view  (/image_annotated)
"""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(package='m10_perception', executable='toy_camera', output='screen'),
        Node(package='m10_perception', executable='color_detector_solution', output='screen'),
    ])
