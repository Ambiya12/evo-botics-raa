"""Apartment-safe navigation orchestrator with a non-overridable mock backend."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    default_waypoints = PathJoinSubstitution([
        FindPackageShare("evo_navigation"),
        "config",
        "home_reception_waypoints.yaml",
    ])
    return LaunchDescription([
        DeclareLaunchArgument("mock_outcome", default_value="arrived"),
        DeclareLaunchArgument(
            "waypoint_config_path",
            default_value=default_waypoints,
        ),
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
                "mock_outcome": LaunchConfiguration("mock_outcome"),
                "waypoint_config_path": LaunchConfiguration(
                    "waypoint_config_path"
                ),
            }.items(),
        ),
    ])
