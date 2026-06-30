from glob import glob
from setuptools import setup

package_name = 'm6_urdf'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
        (f'share/{package_name}/launch', glob('launch/*.py')),
        (f'share/{package_name}/urdf', glob('urdf/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='LucsRobotics',
    maintainer_email='lucs.robotics@gmail.com',
    description='Moduł 6 — URDF',
    license='MIT',
    entry_points={
        'console_scripts': [
            'joint_oscillator = m6_urdf.joint_oscillator:main',
        ],
    },
)
