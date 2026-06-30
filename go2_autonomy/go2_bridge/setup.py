from setuptools import find_packages, setup

package_name = 'go2_bridge'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', ['config/safety.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Lukasz Gruszka',
    maintainer_email='lukasz.gruszka90@gmail.com',
    description='Most Go2: /cmd_vel -> Unitree sport API, lowstate -> /joint_states, arbiter cmd_vel. Kurs ROS2 Intro (LucsRobotics).',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'cmd_vel_arbiter = go2_bridge.cmd_vel_arbiter:main',
            'lowstate_to_joint_states = go2_bridge.lowstate_to_joint_states:main',
            'unitree_cmd_vel_bridge_node = go2_bridge.unitree_cmd_vel_bridge_node:main',
        ],
    },
)
