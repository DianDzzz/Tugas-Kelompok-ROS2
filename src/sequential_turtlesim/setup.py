from setuptools import find_packages, setup

package_name = 'sequential_turtlesim'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    package_data={'': ['py.typed']},
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='lenovo',
    maintainer_email='lenovo@todo.todo',
    description='TODO: Package description',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'fazle_node = sequential_turtlesim.fazle_node:main',
            'fathur_node = sequential_turtlesim.fathur_node:main',
            'fayyazi_node = sequential_turtlesim.fayyazi_node:main',
        ],
    },
)
