import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'intro_launch'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # pliki launch - bez tego wpisu ros2 launch ich nie znajdzie
        (os.path.join('share', package_name, 'launch'),
         glob(os.path.join('launch', '*.launch.py'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='LucsRobotics',
    maintainer_email='lucs.robotics@gmail.com',
    description='M5 exercise - turtlesim + circle_driver from one launch file',
    license='MIT',
    entry_points={
        'console_scripts': [
            'circle_driver = intro_launch.circle_driver:main',
        ],
    },
)
