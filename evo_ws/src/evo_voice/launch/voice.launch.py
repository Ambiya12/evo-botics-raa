from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("model_size", default_value="base"),
        DeclareLaunchArgument("device", default_value="cpu"),
        DeclareLaunchArgument("language", default_value="fr"),

        Node(
            package="evo_voice",
            executable="translator_node",
            name="translator_node",
            parameters=[{
                "model_size": LaunchConfiguration("model_size"),
                "device": LaunchConfiguration("device"),
                "language": LaunchConfiguration("language"),
            }],
            output="screen",
        ),
    ])
