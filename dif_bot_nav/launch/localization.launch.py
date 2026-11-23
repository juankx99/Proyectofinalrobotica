"""
Practica 4 - Localizacion con AMCL sobre el mapa del estudiante.

Lanza la simulacion, map_server, amcl y el lifecycle manager.
Uso:
  ros2 launch dif_bot_nav localization.launch.py
Pruebas:
  # Pose inicial incorrecta: el robot real nace en (x, y) pero AMCL cree que esta en (amcl_x, amcl_y)
  ros2 launch dif_bot_nav localization.launch.py x:=3.0 y:=-2.0 amcl_x:=0.0 amcl_y:=0.0
  # Mas ruido en el laser
  ros2 launch dif_bot_nav localization.launch.py lidar_noise:=0.10
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg = get_package_share_directory('dif_bot_nav')

    map_yaml = LaunchConfiguration('map')
    amcl_params = LaunchConfiguration('amcl_params')

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg, 'launch', 'sim.launch.py')),
        launch_arguments={
            'gui': LaunchConfiguration('gui'),
            'rviz': 'true',
            'rviz_config': os.path.join(pkg, 'rviz', 'amcl.rviz'),
            'lidar_noise': LaunchConfiguration('lidar_noise'),
            'x': LaunchConfiguration('x'),
            'y': LaunchConfiguration('y'),
            'yaw': LaunchConfiguration('yaw'),
        }.items())

    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{'yaml_filename': map_yaml, 'use_sim_time': True}])

    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[
            amcl_params,
            {
                'use_sim_time': True,
                'initial_pose.x': ParameterValue(LaunchConfiguration('amcl_x'), value_type=float),
                'initial_pose.y': ParameterValue(LaunchConfiguration('amcl_y'), value_type=float),
                'initial_pose.yaw': ParameterValue(LaunchConfiguration('amcl_yaw'), value_type=float),
            }])

    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters=[{'use_sim_time': True,
                     'autostart': True,
                     'node_names': ['map_server', 'amcl']}])

    return LaunchDescription([
        DeclareLaunchArgument('map',
                              default_value=os.path.join(pkg, 'maps', 'mapa_casa.yaml')),
        DeclareLaunchArgument('amcl_params',
                              default_value=os.path.join(pkg, 'config', 'amcl.yaml')),
        DeclareLaunchArgument('gui', default_value='false'),
        DeclareLaunchArgument('lidar_noise', default_value='0.01'),
        # Pose real donde nace el robot en Gazebo
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        # Pose inicial que se le da a AMCL
        DeclareLaunchArgument('amcl_x', default_value='0.0'),
        DeclareLaunchArgument('amcl_y', default_value='0.0'),
        DeclareLaunchArgument('amcl_yaw', default_value='0.0'),
        sim,
        map_server,
        amcl,
        lifecycle_manager,
    ])
