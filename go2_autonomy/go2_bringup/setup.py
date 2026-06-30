import os
from glob import glob
from setuptools import setup

package_name = 'go2_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml') + glob('config/*.xml')),
        (os.path.join('share', package_name, 'maps'), glob('maps/*')),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Lukasz Gruszka',
    maintainer_email='lukasz.gruszka90@gmail.com',
    description='Go2 autonomy bringup: cloud->scan, SLAM (mapowanie) i Nav2 (nawigacja). Kurs ROS2 Intro / LucsRobotics.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'odom_tf_relay = go2_bringup.odom_tf_relay:main',
            'scan_qos_relay = go2_bringup.scan_qos_relay:main',
        ],
    },
)
