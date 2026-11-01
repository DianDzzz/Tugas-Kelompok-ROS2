"""Launch turtlesim and every sequential_turtlesim relay node."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """Start turtlesim, the relay receivers, then the autostarting starter node."""
    return LaunchDescription([
        Node(
            package='turtlesim',
            executable='turtlesim_node',
            name='turtlesim',
            output='screen',
        ),
        # Receivers first so they are already subscribed when the token appears.
        Node(
            package='sequential_turtlesim',
            executable='fazle_node',
            output='screen',
        ),
        Node(
            package='sequential_turtlesim',
            executable='umar_node',
            output='screen',
        ),
        Node(
            package='sequential_turtlesim',
            executable='didan_node',
            output='screen',
        ),
        Node(
            package='sequential_turtlesim',
            executable='awi_node',
            output='screen',
        ),
        Node(
            package='sequential_turtlesim',
            executable='fathur_node',
            output='screen',
        ),
        Node(
            package='sequential_turtlesim',
            executable='fayyazi_node',
            output='screen',
        ),
        # vito_node autostarts the relay, so it goes last.
        Node(
            package='sequential_turtlesim',
            executable='vito_node',
            output='screen',
        ),
    ])
