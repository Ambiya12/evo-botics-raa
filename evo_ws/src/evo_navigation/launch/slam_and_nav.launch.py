"""
Launch SLAM + Nav2 simultaneously for explore-while-navigating.

The robot builds the map with slam_toolbox while Nav2 handles
obstacle avoidance and goal navigation. Perfect for autonomous exploration.

Prerequisites: Yahboom bringup must already be running.

NOTE: We rely on the Yahboom bringup's robot_state_publisher for TF.
Do not launch a second one — the microcontroller clock offset causes conflicts.

Usage:
  ros2 launch evo_navigation slam_and_nav.launch.py
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
    slam_params = PathJoinSubstitution([nav_share, "config", "slam_toolbox_params.yaml"])
    nav2_params = PathJoinSubstitution([nav_share, "config", "nav2_params.yaml"])
    use_sim_time = LaunchConfiguration("use_sim_time")
    use_velocity_smoother = LaunchConfiguration("use_velocity_smoother")
    use_collision_monitor = LaunchConfiguration("use_collision_monitor")
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
            }],
            output="screen",
        )]

    return LaunchDescription([
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
        DeclareLaunchArgument("use_collision_monitor", default_value="true"),

        # --- SLAM Toolbox (provides map + map->odom TF) ---
        Node(
            package="slam_toolbox",
            executable="async_slam_toolbox_node",
            name="slam_toolbox",
            parameters=[
                slam_params,
                {"use_sim_time": use_sim_time},
            ],
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

        # --- Nav2 controller + planner (no AMCL needed, SLAM provides localization) ---
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
