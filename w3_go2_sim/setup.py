from glob import glob
from setuptools import setup

package_name = 'w3_go2_sim'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
        (f'share/{package_name}/launch', glob('launch/*.launch.py')),
        (f'share/{package_name}/params', glob('params/*.yaml')),
        (f'share/{package_name}/worlds', glob('worlds/*.sdf')),
        (f'share/{package_name}/rviz', glob('rviz/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='LucsRobotics',
    maintainer_email='lucs.robotics@gmail.com',
    description='Warsztat W3 (wariant Go2): Unitree Go2 w Gazebo Harmonic - SLAM, mapa, Nav2 z AMCL',
    license='MIT',
    entry_points={
        'console_scripts': [
            'send_goals = w3_go2_sim.send_goals:main',
        ],
    },
)
