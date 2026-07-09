from glob import glob
from setuptools import setup

package_name = 'panda_moveit'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
        (f'share/{package_name}/launch', glob('launch/*.py')),
        (f'share/{package_name}/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='LucsRobotics',
    maintainer_email='lucs.robotics@gmail.com',
    description='W7/W8 — Franka Panda + MoveIt 2: pick & place z moveit_py',
    license='MIT',
    entry_points={
        'console_scripts': [
            'pick_place = panda_moveit.pick_place:main',
        ],
    },
)
