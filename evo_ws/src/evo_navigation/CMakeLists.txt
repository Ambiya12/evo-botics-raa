cmake_minimum_required(VERSION 3.8)
project(evo_navigation)

find_package(ament_cmake REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)

add_executable(cmd_vel_safety_gate src/cmd_vel_safety_gate.cpp)
ament_target_dependencies(cmd_vel_safety_gate
  geometry_msgs
  rclcpp
  std_msgs
)

install(TARGETS cmd_vel_safety_gate
  DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY config launch maps rviz
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
