from glob import glob
from setuptools import setup

package_name = 'm7_nav2_capstone'

setup(
    name=package_name,
    version='0.2.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
        (f'share/{package_name}/launch', glob('launch/*.launch.py')),
        (f'share/{package_name}/params', glob('params/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='LucsRobotics',
    maintainer_email='lucs.robotics@gmail.com',
    description='Warsztat W3 — Nav2 i SLAM w Webots (TurtleBot3): scan_fix, launch SLAM, parametry',
    license='MIT',
    entry_points={
        'console_scripts': [
            'scan_fix = m7_nav2_capstone.scan_fix:main',
        ],
    },
)
