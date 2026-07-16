"""
Launch Nav2 autonomous navigation with a pre-built map.

Prerequisites:
  - Yahboom bringup must already be running (lidar + odometry + cmd_vel)
  - A map must have been saved previously with slam_toolbox

NOTE: We rely on the Yahboom bringup's robot_state_publisher for TF.
Do not launch a second one — the microcontroller clock offset causes conflicts.

Usage:
  ros2 launch evo_navigation navigation.launch.py map:=/path/to/map.yaml
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    nav_share = FindPackageShare("evo_navigation")

    rviz_path = PathJoinSubstitution([nav_share, "rviz", "nav2_view.rviz"])
    nav2_params = PathJoinSubstitution([nav_share, "config", "nav2_params.yaml"])
    default_map = PathJoinSubstitution([nav_share, "maps", "school_v1.yaml"])
    use_sim_time = LaunchConfiguration("use_sim_time")
    use_velocity_smoother = LaunchConfiguration("use_velocity_smoother")
    use_collision_monitor = LaunchConfiguration("use_collision_monitor")
    lifecycle_bond_timeout = LaunchConfiguration("lifecycle_bond_timeout")
    controller_cmd_topic = PythonExpression([
        "'/cmd_vel_nav_raw' if '", use_velocity_smoother,
        "'.lower() == 'true' else '/cmd_vel_nav'",
    ])
    relay_input_topic = PythonExpression([
        "'/cmd_vel_safe' if '", use_collision_monitor,
        "'.lower() == 'true' else '/cmd_vel_selected'",
    ])

    def navigation_lifecycle_nodes(context, *args, **kwargs):
        node_names = [
            "controller_server",
            "smoother_server",
            "planner_server",
            "behavior_server",
            "bt_navigator",
            "waypoint_follower",
        ]
        if use_velocity_smoother.perform(context).lower() == "true":
            node_names.append("velocity_smoother")
        if use_collision_monitor.perform(context).lower() == "true":
            node_names.append("collision_monitor")

        return [Node(
            package="nav2_lifecycle_manager",
            executable="lifecycle_manager",
            name="lifecycle_manager_navigation",
            parameters=[{
                "use_sim_time": use_sim_time,
                "autostart": True,
                "node_names": node_names,
                "bond_timeout": lifecycle_bond_timeout,
                "attempt_respawn_reconnection": True,
            }],
            output="screen",
        )]

    return LaunchDescription([
        DeclareLaunchArgument(
            "map",
            default_value=default_map,
            description="Full path to the map YAML file",
        ),
        DeclareLaunchArgument("rviz", default_value="true"),
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        DeclareLaunchArgument(
            "navigation_mode",
            default_value="mapped_free_space",
            description="Goal policy: mapped_free_space, exploration, or future road_network_only.",
        ),
        DeclareLaunchArgument("enforce_mapped_space", default_value="true"),
        DeclareLaunchArgument("goal_clearance_m", default_value="0.25"),
        DeclareLaunchArgument("path_cost_threshold", default_value="95"),
        DeclareLaunchArgument("goal_request_topic", default_value="/evo/navigation/goal_request"),
        DeclareLaunchArgument("validated_goal_topic", default_value="/goal_pose_validated"),
        DeclareLaunchArgument("goal_status_topic", default_value="/evo/navigation/goal_status"),
        DeclareLaunchArgument("estop_status_topic", default_value="/e_stop_active"),
        DeclareLaunchArgument("goal_target_frame", default_value="map"),
        DeclareLaunchArgument("planner_action_name", default_value="/compute_path_to_pose"),
        DeclareLaunchArgument("nav2_action_name", default_value="/navigate_to_pose"),
        DeclareLaunchArgument("use_velocity_smoother", default_value="true"),
        DeclareLaunchArgument(
            "use_collision_monitor",
            default_value="false",
            description=(
                "Enable the additional all-direction stop polygon only after "
                "physical validation; Nav2 costmaps and controller collision "
                "checking remain active when false."
            ),
        ),
        DeclareLaunchArgument(
            "lifecycle_bond_timeout",
            default_value="10.0",
            description=(
                "Seconds before lifecycle heartbeat loss resets Nav2. "
                "The cmd_vel output watchdog remains the immediate motion fail-safe."
            ),
        ),

        # --- Goal gate: validate map/costmap/path before Nav2 receives a goal ---
        Node(
            package="evo_navigation",
            executable="navigation_goal_validator",
            name="navigation_goal_validator",
            parameters=[{
                "use_sim_time": use_sim_time,
                "navigation_mode": LaunchConfiguration("navigation_mode"),
                "enforce_mapped_space": LaunchConfiguration("enforce_mapped_space"),
                "goal_clearance_m": LaunchConfiguration("goal_clearance_m"),
                "path_cost_threshold": LaunchConfiguration("path_cost_threshold"),
                "goal_request_topic": LaunchConfiguration("goal_request_topic"),
                "validated_goal_topic": LaunchConfiguration("validated_goal_topic"),
                "status_topic": LaunchConfiguration("goal_status_topic"),
                "estop_status_topic": LaunchConfiguration("estop_status_topic"),
                "target_frame": LaunchConfiguration("goal_target_frame"),
                "planner_action_name": LaunchConfiguration("planner_action_name"),
                "nav2_action_name": LaunchConfiguration("nav2_action_name"),
            }],
            output="screen",
        ),

        # --- Final command gate / latched emergency stop ---
        Node(
            package="evo_navigation",
            executable="cmd_vel_safety_gate",
            name="cmd_vel_safety_gate",
            parameters=[{
                "use_sim_time": use_sim_time,
                "nav_cmd_topic": "/cmd_vel_nav",
                "teleop_cmd_topic": "/cmd_vel_teleop",
                "output_cmd_topic": "/cmd_vel_selected",
            }],
            output="screen",
        ),
        Node(
            package="evo_navigation",
            executable="cmd_vel_output_relay",
            name="cmd_vel_output_relay",
            parameters=[{
                "use_sim_time": use_sim_time,
                "input_cmd_topic": relay_input_topic,
                "fallback_cmd_topic": "",
                "output_cmd_topic": "/cmd_vel",
            }],
            output="screen",
        ),

        # --- Localization on the saved map ---
        Node(
            package="nav2_map_server",
            executable="map_server",
            name="map_server",
            parameters=[nav2_params, {
                "yaml_filename": LaunchConfiguration("map"),
                "use_sim_time": use_sim_time,
            }],
            output="screen",
        ),
        Node(
            package="nav2_amcl",
            executable="amcl",
            name="amcl",
            parameters=[nav2_params, {"use_sim_time": use_sim_time}],
            output="screen",
        ),
        Node(
            package="nav2_lifecycle_manager",
            executable="lifecycle_manager",
            name="lifecycle_manager_localization",
            parameters=[{
                "use_sim_time": use_sim_time,
                "autostart": True,
                "node_names": ["map_server", "amcl"],
                "bond_timeout": lifecycle_bond_timeout,
            }],
            output="screen",
        ),

        # --- Nav2 navigation servers ---
        Node(
            package="nav2_controller",
            executable="controller_server",
            name="controller_server",
            parameters=[nav2_params, {
                "use_sim_time": use_sim_time,
            }],
            remappings=[("cmd_vel", controller_cmd_topic)],
            output="screen",
        ),
        Node(
            package="nav2_smoother",
            executable="smoother_server",
            name="smoother_server",
            parameters=[nav2_params, {"use_sim_time": use_sim_time}],
            output="screen",
        ),
        Node(
            package="nav2_planner",
            executable="planner_server",
            name="planner_server",
            parameters=[nav2_params, {"use_sim_time": use_sim_time}],
            output="screen",
        ),
        Node(
            package="nav2_behaviors",
            executable="behavior_server",
            name="behavior_server",
            parameters=[nav2_params, {
                "use_sim_time": use_sim_time,
            }],
            remappings=[("cmd_vel", controller_cmd_topic)],
            output="screen",
        ),
        Node(
            package="nav2_bt_navigator",
            executable="bt_navigator",
            name="bt_navigator",
            parameters=[nav2_params, {"use_sim_time": use_sim_time}],
            output="screen",
        ),
        Node(
            package="nav2_waypoint_follower",
            executable="waypoint_follower",
            name="waypoint_follower",
            parameters=[nav2_params, {"use_sim_time": use_sim_time}],
            output="screen",
        ),
        Node(
            package="nav2_velocity_smoother",
            executable="velocity_smoother",
            name="velocity_smoother",
            parameters=[nav2_params, {"use_sim_time": use_sim_time}],
            remappings=[
                ("cmd_vel", "/cmd_vel_nav_raw"),
                ("cmd_vel_smoothed", "/cmd_vel_nav"),
            ],
            condition=IfCondition(use_velocity_smoother),
            output="screen",
        ),
        Node(
            package="nav2_collision_monitor",
            executable="collision_monitor",
            name="collision_monitor",
            parameters=[nav2_params, {"use_sim_time": use_sim_time}],
            condition=IfCondition(use_collision_monitor),
            output="screen",
        ),
        OpaqueFunction(function=navigation_lifecycle_nodes),

        # --- RViz ---
        Node(
            package="rviz2",
            executable="rviz2",
            arguments=["-d", rviz_path],
            condition=IfCondition(LaunchConfiguration("rviz")),
            output="screen",
        ),
    ])
