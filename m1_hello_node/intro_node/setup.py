from setuptools import find_packages, setup

package_name = 'intro_node'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='LucsRobotics',
    maintainer_email='lucs.robotics@gmail.com',
    description='Module 1 exercise — hello node z timerem',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # Domyślnie ros2 run uruchamia skeleton (twój kod do uzupełnienia)
            'hello = intro_node.hello_skeleton:main',
            # Solution dostępny jako osobny executable
            'hello_solution = intro_node.hello_solution:main',
        ],
    },
)
