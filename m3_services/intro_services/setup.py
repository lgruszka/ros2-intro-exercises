from setuptools import find_packages, setup

package_name = 'intro_services'

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
    description='Module 3 exercise — add_two_ints service',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'add_server = intro_services.add_two_ints_server_skeleton:main',
            'add_client = intro_services.add_two_ints_client_skeleton:main',
            'add_server_solution = intro_services.add_two_ints_server_solution:main',
            'add_client_solution = intro_services.add_two_ints_client_solution:main',
        ],
    },
)
