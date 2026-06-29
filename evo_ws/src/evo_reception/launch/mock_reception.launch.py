from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def package_launch(package: str, filename: str, arguments=None):
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare(package), "launch", filename])
        ),
        launch_arguments=(arguments or {}).items(),
    )


def generate_launch_description():
    reservation_outcome = LaunchConfiguration("reservation_outcome")
    destination_id = LaunchConfiguration("destination_id")
    navigation_outcome = LaunchConfiguration("navigation_outcome")
    max_retries = LaunchConfiguration("max_retries")

    return LaunchDescription([
        DeclareLaunchArgument("reservation_outcome", default_value="valid"),
        DeclareLaunchArgument("destination_id", default_value="1"),
        DeclareLaunchArgument("navigation_outcome", default_value="arrived"),
        DeclareLaunchArgument("max_retries", default_value="0"),
        DeclareLaunchArgument(
            "transcript_text", default_value="I have a reservation"
        ),

        package_launch(
            "evo_voice",
            "tts.launch.py",
            {"mock_audio": "true"},
        ),
        package_launch("evo_voice", "intent_detector.launch.py"),
        package_launch(
            "evo_reception",
            "reception.launch.py",
            {
                "mock_mode": "true",
                "mock_outcome": reservation_outcome,
                "mock_destination_id": destination_id,
            },
        ),
        package_launch(
            "evo_reception",
            "dialogue_manager.launch.py",
            {"max_retries": max_retries},
        ),
        package_launch(
            "evo_navigation",
            "orchestrator.launch.py",
            {
                "mock_navigation": "true",
                "mock_outcome": navigation_outcome,
            },
        ),
        package_launch(
            "evo_vision",
            "human_approach.launch.py",
            {"debounce_frames": "3"},
        ),
        Node(
            package="evo_reception",
            executable="mock_reception_driver_node",
            name="mock_reception_driver_node",
            parameters=[{
                "transcript_text": LaunchConfiguration("transcript_text"),
                "detection_frames": 3,
            }],
            output="screen",
        ),
    ])
