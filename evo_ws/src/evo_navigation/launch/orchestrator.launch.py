from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    default_waypoints = PathJoinSubstitution(
        [FindPackageShare("evo_navigation"), "config", "reception_waypoints.yaml"]
    )
    return LaunchDescription([
        DeclareLaunchArgument("waypoint_config_path", default_value=default_waypoints),
        DeclareLaunchArgument("allow_real_navigation", default_value="false"),
        DeclareLaunchArgument("navigation_timeout_sec", default_value="120.0"),
        DeclareLaunchArgument(
            "guide_action_name", default_value="/reception/guide_to_destination"
        ),
        DeclareLaunchArgument(
            "status_topic", default_value="/reception/navigation/status"
        ),
        DeclareLaunchArgument("nav2_action_name", default_value="/navigate_to_pose"),
        DeclareLaunchArgument("estop_topic", default_value="/e_stop_active"),
        DeclareLaunchArgument("localization_topic", default_value="/amcl_pose"),
        DeclareLaunchArgument(
            "localization_timeout_sec",
            default_value="0.0",
            description=(
                "Optional AMCL message freshness limit. Zero keeps a "
                "covariance-validated stationary pose ready."
            ),
        ),
        DeclareLaunchArgument(
            "max_localization_xy_variance", default_value="0.5"
        ),
        Node(
            package="evo_navigation",
            executable="navigation_orchestrator_node",
            name="navigation_orchestrator_node",
            parameters=[{
                "waypoint_config_path": LaunchConfiguration("waypoint_config_path"),
                "allow_real_navigation": ParameterValue(
                    LaunchConfiguration("allow_real_navigation"), value_type=bool
                ),
                "navigation_timeout_sec": ParameterValue(
                    LaunchConfiguration("navigation_timeout_sec"), value_type=float
                ),
                "guide_action_name": LaunchConfiguration("guide_action_name"),
                "status_topic": LaunchConfiguration("status_topic"),
                "nav2_action_name": LaunchConfiguration("nav2_action_name"),
                "estop_topic": LaunchConfiguration("estop_topic"),
                "localization_topic": LaunchConfiguration("localization_topic"),
                "localization_timeout_sec": ParameterValue(
                    LaunchConfiguration("localization_timeout_sec"),
                    value_type=float,
                ),
                "max_localization_xy_variance": ParameterValue(
                    LaunchConfiguration("max_localization_xy_variance"),
                    value_type=float,
                ),
            }],
            output="screen",
        ),
    ])
