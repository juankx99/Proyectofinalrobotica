"""
Proyecto final - Misiones autonomas.

Lanza Nav2 completo (simulacion + AMCL + navegacion) y el nodo de mision.
Uso:
  ros2 launch dif_bot_nav mission.launch.py gui:=true
  ros2 service call /start_mission std_srvs/srv/Trigger     # iniciar
  ros2 service call /cancel_mission std_srvs/srv/Trigger    # cancelar
  ros2 topic echo /mission_status                           # estado
Otro archivo de waypoints:
  ros2 launch dif_bot_nav mission.launch.py waypoints_file:=/ruta/waypoints.yaml
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('dif_bot_nav')

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg, 'launch', 'nav2.launch.py')),
        launch_arguments={
            'gui': LaunchConfiguration('gui'),
            'rviz_config': os.path.join(pkg, 'rviz', 'mission.rviz'),
        }.items())

    mission = Node(
        package='dif_bot_nav',
        executable='mission_node.py',
        name='mission_node',
        output='screen',
        parameters=[{'waypoints_file': LaunchConfiguration('waypoints_file'),
                     'use_sim_time': True}])

    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='false'),
        DeclareLaunchArgument('waypoints_file',
                              default_value=os.path.join(pkg, 'config', 'waypoints.yaml')),
        nav2,
        TimerAction(period=5.0, actions=[mission]),
    ])
