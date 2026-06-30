from glob import glob
from setuptools import setup

package_name = 'm7_turtle_choreo'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
        (f'share/{package_name}/launch', glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='LucsRobotics',
    maintainer_email='lucs.robotics@gmail.com',
    description='Warsztat 2 — choreografia żółwi',
    license='MIT',
    entry_points={
        'console_scripts': [
            'choreographer_node = m7_turtle_choreo.choreographer_node:main',
            'dancer_node = m7_turtle_choreo.dancer_node:main',
        ],
    },
)
