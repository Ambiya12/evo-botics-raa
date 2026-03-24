from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node

import os


def _prepend_environment_path(variable_name: str, *paths: str) -> str:
    current_value = os.environ.get(variable_name, "")
    joined_paths = [path for path in paths if path]
    if current_value:
        joined_paths.append(current_value)
    return os.pathsep.join(joined_paths)


def generate_launch_description():
    use_rviz = LaunchConfiguration("use_rviz")
    use_joint_state_publisher = LaunchConfiguration("use_joint_state_publisher")
    use_sim_time = LaunchConfiguration("use_sim_time")
    gz_args = LaunchConfiguration("gz_args")
    robot_name = LaunchConfiguration("robot_name")
    x = LaunchConfiguration("x")
    y = LaunchConfiguration("y")
    z = LaunchConfiguration("z")
    roll = LaunchConfiguration("roll")
    pitch = LaunchConfiguration("pitch")
    yaw = LaunchConfiguration("yaw")

    declare_use_rviz = DeclareLaunchArgument(
        "use_rviz",
        default_value="true",
        description="Launch RViz together with Gazebo.",
    )

    declare_use_joint_state_publisher = DeclareLaunchArgument(
        "use_joint_state_publisher",
        default_value="true",
        description="Start joint_state_publisher for the RViz TF tree.",
    )

    declare_use_sim_time = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        description="Use Gazebo clock for ROS nodes.",
    )

    declare_gz_args = DeclareLaunchArgument(
        "gz_args",
        default_value="-r empty.sdf",
        description="Arguments passed to ros_gz_sim gz_sim.launch.py.",
    )

    declare_robot_name = DeclareLaunchArgument(
        "robot_name",
        default_value="m3pro",
        description="Name of the spawned Gazebo entity.",
    )

    declare_x = DeclareLaunchArgument("x", default_value="0.0", description="Spawn X position.")
    declare_y = DeclareLaunchArgument("y", default_value="0.0", description="Spawn Y position.")
    declare_z = DeclareLaunchArgument("z", default_value="0.05", description="Spawn Z position.")
    declare_roll = DeclareLaunchArgument("roll", default_value="0.0", description="Spawn roll.")
    declare_pitch = DeclareLaunchArgument("pitch", default_value="0.0", description="Spawn pitch.")
    declare_yaw = DeclareLaunchArgument("yaw", default_value="0.0", description="Spawn yaw.")

    bringup_share = get_package_share_directory("evo_bringup")
    description_share = get_package_share_directory("yahboom_M3Pro_description")
    ros_gz_sim_share = get_package_share_directory("ros_gz_sim")

    urdf_path = os.path.join(description_share, "urdf", "M3Pro.urdf")
    share_root = os.path.dirname(description_share)

    display_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, "launch", "display_m3pro.launch.py")
        ),
        launch_arguments={
            "use_joint_state_publisher": use_joint_state_publisher,
            "use_rviz": use_rviz,
            "use_sim_time": use_sim_time,
        }.items(),
    )

    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_share, "launch", "gz_sim.launch.py")
        ),
        launch_arguments={"gz_args": gz_args}.items(),
    )

    clock_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="clock_bridge",
        output="screen",
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
    )

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        name="spawn_m3pro",
        output="screen",
        arguments=[
            "-world",
            "empty",
            "-name",
            robot_name,
            "-x",
            x,
            "-y",
            y,
            "-z",
            z,
            "-R",
            roll,
            "-P",
            pitch,
            "-Y",
            yaw,
            "-file",
            urdf_path,
        ],
    )

    return LaunchDescription([
        declare_use_rviz,
        declare_use_joint_state_publisher,
        declare_use_sim_time,
        declare_gz_args,
        declare_robot_name,
        declare_x,
        declare_y,
        declare_z,
        declare_roll,
        declare_pitch,
        declare_yaw,
        SetEnvironmentVariable(
            name="GZ_SIM_RESOURCE_PATH",
            value=_prepend_environment_path("GZ_SIM_RESOURCE_PATH", share_root, description_share),
        ),
        SetEnvironmentVariable(
            name="IGN_GAZEBO_RESOURCE_PATH",
            value=_prepend_environment_path("IGN_GAZEBO_RESOURCE_PATH", share_root, description_share),
        ),
        gazebo_launch,
        display_launch,
        clock_bridge,
        TimerAction(period=8.0, actions=[spawn_robot]),
    ])