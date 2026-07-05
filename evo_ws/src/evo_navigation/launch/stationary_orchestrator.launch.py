"""Apartment-safe navigation orchestrator with a non-overridable mock backend."""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([
                    FindPackageShare("evo_navigation"),
                    "launch",
                    "orchestrator.launch.py",
                ])
            ),
            launch_arguments={
                "mock_navigation": "true",
                "allow_real_navigation": "false",
            }.items(),
        ),
    ])
