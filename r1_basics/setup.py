from glob import glob

from setuptools import find_packages, setup

package_name = 'r1_basics'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
        (f'share/{package_name}/launch', glob('launch/*.launch.py')),
        (f'share/{package_name}/config', glob('config/*.yaml') + glob('config/*.xml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='LucsRobotics',
    maintainer_email='lucs.robotics@gmail.com',
    description='Unitree R1 EDU w ROS 2 Jazzy (W9/W10 kursu ROS 2 Intro, LucsRobotics)',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'cmd_vel_bridge = r1_basics.cmd_vel_bridge:main',
            'sport_cli = r1_basics.sport_cli:main',
            'dead_reckoning = r1_basics.dead_reckoning:main',
            'goto_point = r1_basics.goto_point:main',
            'arm_sequence = r1_basics.arm_sequence:main',
            'camera = r1_basics.camera:main',
            'r1_mock = r1_basics.r1_mock:main',
            'r1_sim = r1_basics.r1_sim:main',
            'r1_policy = r1_basics.r1_policy:main',
        ],
    },
)
