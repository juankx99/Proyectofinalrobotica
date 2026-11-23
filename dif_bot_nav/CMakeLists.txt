cmake_minimum_required(VERSION 3.8)
project(dif_bot_nav)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY launch config urdf worlds maps rviz
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS scripts/mission_node.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
