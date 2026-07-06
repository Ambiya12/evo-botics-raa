from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            "detections_topic", default_value="/vision/people/detections"
        ),
        DeclareLaunchArgument(
            "approach_topic", default_value="/vision/people/approach"
        ),
        DeclareLaunchArgument(
            "presence_topic", default_value="/vision/people/presence"
        ),
        DeclareLaunchArgument(
            "dialogue_state_topic", default_value="/reception/dialogue/state"
        ),
        DeclareLaunchArgument("zone_id", default_value="reception"),
        DeclareLaunchArgument("min_confidence", default_value="0.65"),
        DeclareLaunchArgument("min_distance_m", default_value="0.5"),
        DeclareLaunchArgument("max_distance_m", default_value="2.5"),
        DeclareLaunchArgument("zone_min_x", default_value="0.25"),
        DeclareLaunchArgument("zone_max_x", default_value="0.75"),
        DeclareLaunchArgument("zone_min_y", default_value="0.15"),
        DeclareLaunchArgument("zone_max_y", default_value="0.95"),
        DeclareLaunchArgument("debounce_frames", default_value="3"),
        DeclareLaunchArgument("cooldown_sec", default_value="10.0"),
        DeclareLaunchArgument("absence_reset_sec", default_value="10.0"),

        Node(
            package="evo_vision",
            executable="human_approach_node",
            name="human_approach_node",
            parameters=[{
                "detections_topic": LaunchConfiguration("detections_topic"),
                "approach_topic": LaunchConfiguration("approach_topic"),
                "presence_topic": LaunchConfiguration("presence_topic"),
                "dialogue_state_topic": LaunchConfiguration(
                    "dialogue_state_topic"
                ),
                "zone_id": LaunchConfiguration("zone_id"),
                "min_confidence": ParameterValue(
                    LaunchConfiguration("min_confidence"), value_type=float
                ),
                "min_distance_m": ParameterValue(
                    LaunchConfiguration("min_distance_m"), value_type=float
                ),
                "max_distance_m": ParameterValue(
                    LaunchConfiguration("max_distance_m"), value_type=float
                ),
                "zone_min_x": ParameterValue(
                    LaunchConfiguration("zone_min_x"), value_type=float
                ),
                "zone_max_x": ParameterValue(
                    LaunchConfiguration("zone_max_x"), value_type=float
                ),
                "zone_min_y": ParameterValue(
                    LaunchConfiguration("zone_min_y"), value_type=float
                ),
                "zone_max_y": ParameterValue(
                    LaunchConfiguration("zone_max_y"), value_type=float
                ),
                "debounce_frames": ParameterValue(
                    LaunchConfiguration("debounce_frames"), value_type=int
                ),
                "cooldown_sec": ParameterValue(
                    LaunchConfiguration("cooldown_sec"), value_type=float
                ),
                "absence_reset_sec": ParameterValue(
                    LaunchConfiguration("absence_reset_sec"), value_type=float
                ),
            }],
            output="screen",
        ),
    ])
