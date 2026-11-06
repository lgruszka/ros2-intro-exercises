from glob import glob
from setuptools import setup

package_name = 'fr3_moveit'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
        (f'share/{package_name}/launch', glob('launch/*.py')),
        (f'share/{package_name}/config', glob('config/*.yaml') + glob('config/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='LucsRobotics',
    maintainer_email='lucs.robotics@gmail.com',
    description='W7/W8 - Franka Research 3 + MoveIt 2: pick & place z moveit_py (fake hardware albo prawdziwy FR3)',
    license='MIT',
    entry_points={
        'console_scripts': [
            'pick_place = fr3_moveit.pick_place:main',
            'fake_gripper = fr3_moveit.fake_gripper:main',
        ],
    },
)
