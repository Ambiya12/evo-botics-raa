cmake_minimum_required(VERSION 3.8)
project(evo_navigation)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(std_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(tf2_ros REQUIRED)

ament_python_install_package(${PROJECT_NAME})

add_executable(cmd_vel_safety_gate src/cmd_vel_safety_gate.cpp)
ament_target_dependencies(cmd_vel_safety_gate
  geometry_msgs
  rclcpp
  std_msgs
)

add_executable(cmd_vel_output_relay src/cmd_vel_output_relay.cpp)
ament_target_dependencies(cmd_vel_output_relay
  geometry_msgs
  rclcpp
)

add_executable(navigation_goal_validator src/navigation_goal_validator.cpp)
target_include_directories(navigation_goal_validator PRIVATE include)
ament_target_dependencies(navigation_goal_validator
  geometry_msgs
  nav2_msgs
  nav_msgs
  rclcpp
  rclcpp_action
  std_msgs
  tf2
  tf2_geometry_msgs
  tf2_ros
)

install(TARGETS
  cmd_vel_safety_gate
  cmd_vel_output_relay
  navigation_goal_validator
  DESTINATION lib/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/nav_readiness_checker
  scripts/navigation_orchestrator_node
  DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY config launch maps rviz
  DESTINATION share/${PROJECT_NAME}
)

install(
  DIRECTORY include/
  DESTINATION include
)

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  find_package(ament_cmake_pytest REQUIRED)

  ament_add_gtest(test_occupancy_grid_utils test/test_occupancy_grid_utils.cpp)
  if(TARGET test_occupancy_grid_utils)
    target_include_directories(test_occupancy_grid_utils PRIVATE include)
    ament_target_dependencies(test_occupancy_grid_utils
      geometry_msgs
      nav_msgs
      tf2
      tf2_geometry_msgs
    )
  endif()

  ament_add_gtest(test_navigation_action_status test/test_navigation_action_status.cpp)
  if(TARGET test_navigation_action_status)
    target_include_directories(test_navigation_action_status PRIVATE include)
    ament_target_dependencies(test_navigation_action_status
      rclcpp_action
    )
  endif()

  ament_add_pytest_test(
    test_navigation_orchestrator
    test/test_navigation_orchestrator.py
  )
  ament_add_pytest_test(
    test_nav_readiness_checker
    test/test_nav_readiness_checker.py
  )
  ament_add_pytest_test(
    test_waypoints
    test/test_waypoints.py
  )
endif()

ament_export_include_directories(include)

ament_package()
