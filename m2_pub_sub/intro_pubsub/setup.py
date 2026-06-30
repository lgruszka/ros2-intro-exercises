from glob import glob

from setuptools import find_packages, setup

package_name = 'intro_pubsub'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (f'share/{package_name}/launch', glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='LucsRobotics',
    maintainer_email='lucs.robotics@gmail.com',
    description='Module 2 exercise — first pub/sub',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # Domyślnie ros2 run uruchamia skeleton.
            # Po wypełnieniu TODO to twoja praca.
            'talker = intro_pubsub.talker_skeleton:main',
            'listener = intro_pubsub.listener_skeleton:main',
            # Solution-y dostępne jako osobne entry points:
            'talker_solution = intro_pubsub.talker_solution:main',
            'listener_solution = intro_pubsub.listener_solution:main',
        ],
    },
)
