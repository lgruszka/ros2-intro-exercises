cmake_minimum_required(VERSION 3.8)
project(go2_description)

find_package(ament_cmake REQUIRED)

# Slim: instalujemy tylko URDF (mesh .dae celowo pominięte — patrz package.xml/README).
install(
  DIRECTORY urdf
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
