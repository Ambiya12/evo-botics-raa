from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="evo_screen",
            executable="lcd_screen_node",
            name="lcd_screen_node",
            output="screen",
        ),
    ])
