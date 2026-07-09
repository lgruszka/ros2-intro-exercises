import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'intro_demo'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Launch files — wymagane żeby ros2 launch je znalazło:
        (os.path.join('share', package_name, 'launch'),
         glob(os.path.join('launch', '*.launch.py'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='LucsRobotics',
    maintainer_email='lucs.robotics@gmail.com',
    description='Module 4 exercise — workspace + launch file',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'counter = intro_demo.counter:main',
            'monitor = intro_demo.monitor:main',
        ],
    },
)
