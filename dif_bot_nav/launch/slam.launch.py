"""
Practica 3 - Mapeo con SLAM Toolbox (online async).

Lanza la simulacion (Gazebo + robot + RViz con el mapa) y slam_toolbox.
Uso:
  ros2 launch dif_bot_nav slam.launch.py            # sin ventana de Gazebo
  ros2 launch dif_bot_nav slam.launch.py gui:=true  # con ventana de Gazebo
Guardar el mapa (otra terminal):
  ros2 run nav2_map_server map_saver_cli -f ~/rbtc_ws/src/dif_bot_nav/maps/mapa_casa
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg = get_package_share_directory('dif_bot_nav')
    slam_pkg = get_package_share_directory('slam_toolbox')

    gui = LaunchConfiguration('gui')
    slam_params = LaunchConfiguration('slam_params_file')

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg, 'launch', 'sim.launch.py')),
        launch_arguments={
            'gui': gui,
            'use_ros2_control': LaunchConfiguration('use_ros2_control'),
            'rviz': 'true',
            'rviz_config': os.path.join(pkg, 'rviz', 'slam.rviz'),
        }.items())

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(slam_pkg, 'launch', 'online_async_launch.py')),
        launch_arguments={
            'use_sim_time': 'true',
            'slam_params_file': slam_params,
        }.items())

    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='false'),
        DeclareLaunchArgument('use_ros2_control', default_value='false'),
        DeclareLaunchArgument(
            'slam_params_file',
            default_value=os.path.join(pkg, 'config', 'slam_toolbox.yaml')),
        sim,
        slam,
    ])
