from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    # Uruchamia referencyjne rozwiązania (talker_solution + listener_solution),
    # żeby demo działało od razu po colcon build, zanim wypełnisz skeletony.
    return LaunchDescription([
        Node(package='intro_pubsub', executable='talker_solution', name='talker'),
        Node(package='intro_pubsub', executable='listener_solution', name='listener'),
    ])
