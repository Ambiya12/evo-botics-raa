from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    host = LaunchConfiguration("host")
    port = LaunchConfiguration("port")
    return LaunchDescription([
        DeclareLaunchArgument("host", description="IP du serveur Laravel (ex. 10.10.221.104)"),
        DeclareLaunchArgument("port", default_value="80"),
        Node(
            package="evo_screen",
            executable="kiosk",
            name="kiosk_screen",
            output="screen",
            parameters=[{"host": host, "port": port}],
        ),
    ])
