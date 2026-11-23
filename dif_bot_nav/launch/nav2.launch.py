"""
Practica 5 - Navegacion autonoma con Nav2 (metas desde RViz).

Lanza la simulacion + map_server + AMCL + servidores de Nav2
(planner, controller, smoother, behaviors, bt_navigator, velocity_smoother,
waypoint_follower) con un solo lifecycle manager.

Uso:
  ros2 launch dif_bot_nav nav2.launch.py
  ros2 launch dif_bot_nav nav2.launch.py gui:=true     # con ventana de Gazebo
En RViz: "2D Goal Pose" para enviar metas.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('dif_bot_nav')

    params = LaunchConfiguration('params_file')
    map_yaml = LaunchConfiguration('map')
    common = [params, {'use_sim_time': True}]

    # Cadena de velocidad: controller/behaviors -> cmd_vel_nav -> velocity_smoother -> cmd_vel
    to_nav = [('cmd_vel', 'cmd_vel_nav')]

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg, 'launch', 'sim.launch.py')),
        launch_arguments={
            'gui': LaunchConfiguration('gui'),
            'rviz': 'true',
            'rviz_config': LaunchConfiguration('rviz_config'),
            'x': LaunchConfiguration('x'),
            'y': LaunchConfiguration('y'),
            'yaw': LaunchConfiguration('yaw'),
        }.items())

    nodes = [
        Node(package='nav2_map_server', executable='map_server', name='map_server',
             output='screen', parameters=common + [{'yaml_filename': map_yaml}]),
        Node(package='nav2_amcl', executable='amcl', name='amcl',
             output='screen', parameters=common),
        Node(package='nav2_controller', executable='controller_server', name='controller_server',
             output='screen', parameters=common, remappings=to_nav),
        Node(package='nav2_smoother', executable='smoother_server', name='smoother_server',
             output='screen', parameters=common),
        Node(package='nav2_planner', executable='planner_server', name='planner_server',
             output='screen', parameters=common),
        Node(package='nav2_behaviors', executable='behavior_server', name='behavior_server',
             output='screen', parameters=common, remappings=to_nav),
        Node(package='nav2_bt_navigator', executable='bt_navigator', name='bt_navigator',
             output='screen', parameters=common),
        Node(package='nav2_waypoint_follower', executable='waypoint_follower',
             name='waypoint_follower', output='screen', parameters=common),
        Node(package='nav2_velocity_smoother', executable='velocity_smoother',
             name='velocity_smoother', output='screen', parameters=common,
             remappings=[('cmd_vel', 'cmd_vel_nav'), ('cmd_vel_smoothed', 'cmd_vel')]),
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_navigation', output='screen',
             parameters=[{'use_sim_time': True,
                          'autostart': True,
                          'bond_timeout': 10.0,
                          'node_names': ['map_server', 'amcl',
                                         'controller_server', 'smoother_server',
                                         'planner_server', 'behavior_server',
                                         'velocity_smoother', 'bt_navigator',
                                         'waypoint_follower']}]),
    ]

    return LaunchDescription([
        DeclareLaunchArgument('map',
                              default_value=os.path.join(pkg, 'maps', 'mapa_casa.yaml')),
        DeclareLaunchArgument('params_file',
                              default_value=os.path.join(pkg, 'config', 'nav2_params.yaml')),
        DeclareLaunchArgument('gui', default_value='false'),
        DeclareLaunchArgument('rviz_config',
                              default_value=os.path.join(pkg, 'rviz', 'nav2.rviz')),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        sim,
    ] + nodes)
