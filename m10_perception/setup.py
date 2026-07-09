from glob import glob
from setuptools import setup

package_name = 'm10_perception'

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
    description='M10 — percepcja: toy_camera + detektor koloru (cv_bridge + OpenCV)',
    license='MIT',
    entry_points={
        'console_scripts': [
            'toy_camera = m10_perception.toy_camera:main',
            'color_detector = m10_perception.color_detector_skeleton:main',
            'color_detector_solution = m10_perception.color_detector_solution:main',
        ],
    },
)
