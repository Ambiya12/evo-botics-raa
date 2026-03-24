from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    use_joint_state_publisher = LaunchConfiguration("use_joint_state_publisher")
    use_rviz = LaunchConfiguration("use_rviz")

    declare_use_joint_state_publisher = DeclareLaunchArgument(
        "use_joint_state_publisher",
        default_value="true",
        description="Start joint_state_publisher for interactive joint updates.",
    )

    declare_use_rviz = DeclareLaunchArgument(
        "use_rviz",
        default_value="true",
        description="Start RViz2.",
    )

    urdf_path = os.path.join(
        get_package_share_directory("yahboom_M3Pro_description"),
        "urdf",
        "M3Pro.urdf",
    )

    rviz_config = os.path.join(
        get_package_share_directory("evo_bringup"),
        "rviz",
        "m3pro_temp.rviz",
    )

    with open(urdf_path, "r", encoding="utf-8") as f:
        robot_description_content = f.read()

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_description_content}],
    )

    joint_state_publisher = Node(
        package="joint_state_publisher",
        executable="joint_state_publisher",
        name="joint_state_publisher",
        output="screen",
        condition=IfCondition(use_joint_state_publisher),
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config],
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription([
        declare_use_joint_state_publisher,
        declare_use_rviz,
        robot_state_publisher,
        joint_state_publisher,
        rviz,
    ])
