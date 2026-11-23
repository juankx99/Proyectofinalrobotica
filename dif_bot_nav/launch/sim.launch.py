"""
Simulacion liviana del robot diferencial en Gazebo (gz sim).

Argumentos:
  use_ros2_control:=false|true  false (defecto): plugin DiffDrive de Gazebo.
                                true: gz_ros2_control + diff_drive_controller.
  gui:=true|false   Ventana de Gazebo (por defecto false: solo servidor, ahorra CPU)
  rviz:=true|false  Abre RViz (por defecto true)
  world:=<ruta.sdf> Mundo (por defecto worlds/casa.sdf)
  lidar_noise:=0.01 Desviacion estandar del ruido del lidar [m]
  x, y, yaw         Pose inicial del robot
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, ExecuteProcess,
                            IncludeLaunchDescription, RegisterEventHandler,
                            TimerAction)
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg = get_package_share_directory('dif_bot_nav')

    use_ros2_control = LaunchConfiguration('use_ros2_control')
    gui = LaunchConfiguration('gui')
    rviz = LaunchConfiguration('rviz')
    rviz_config = LaunchConfiguration('rviz_config')
    world = LaunchConfiguration('world')
    x = LaunchConfiguration('x')
    y = LaunchConfiguration('y')
    yaw = LaunchConfiguration('yaw')

    robot_description = ParameterValue(
        Command(['xacro ', os.path.join(pkg, 'urdf', 'dif_bot_lite.urdf.xacro'),
                 ' use_ros2_control:=', use_ros2_control,
                 ' lidar_noise:=', LaunchConfiguration('lidar_noise')]),
        value_type=str)

    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description,
                     'use_sim_time': True}])

    # Servidor de Gazebo (sin GUI): -r arranca en PLAY, -s solo servidor
    gz_server = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': ['-r -s -v 2 ', world],
                          'on_exit_shutdown': 'true'}.items())

    # Ventana de Gazebo opcional (proceso aparte)
    gz_gui = ExecuteProcess(
        cmd=['gz', 'sim', '-g', '-v', '2'],
        output='screen',
        condition=IfCondition(gui))

    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=['-topic', '/robot_description', '-name', 'dif_bot',
                   '-x', x, '-y', y, '-z', '0.2', '-Y', yaw])

    # Puente comun: reloj y sensores
    bridge_sensors = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='bridge_sensors',
        output='screen',
        parameters=[{'use_sim_time': True}],
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/imu@sensor_msgs/msg/Imu[gz.msgs.IMU',
        ])

    # Modo Gazebo DiffDrive: cmd_vel (ROS->GZ), odom, TF y joint_states (GZ->ROS)
    bridge_diffdrive = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='bridge_diffdrive',
        output='screen',
        parameters=[{'use_sim_time': True}],
        arguments=[
            '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            '/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model',
        ],
        condition=UnlessCondition(use_ros2_control))

    # Modo ros2_control: un solo spawner para los dos controladores
    controllers = Node(
        package='controller_manager',
        executable='spawner',
        output='screen',
        arguments=['joint_state_broadcaster', 'diff_drive_controller',
                   '--controller-manager', '/controller_manager',
                   '--controller-manager-timeout', '120',
                   '--switch-timeout', '30'],
        condition=IfCondition(use_ros2_control))

    load_controllers_after_spawn = RegisterEventHandler(
        OnProcessExit(target_action=spawn,
                      on_exit=[TimerAction(period=8.0, actions=[controllers])]))

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(rviz))

    return LaunchDescription([
        DeclareLaunchArgument('use_ros2_control', default_value='false'),
        DeclareLaunchArgument('lidar_noise', default_value='0.01'),
        DeclareLaunchArgument('gui', default_value='false'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('rviz_config',
                              default_value=os.path.join(pkg, 'rviz', 'sim.rviz')),
        DeclareLaunchArgument('world',
                              default_value=os.path.join(pkg, 'worlds', 'casa.sdf')),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        rsp,
        gz_server,
        gz_gui,
        spawn,
        bridge_sensors,
        bridge_diffdrive,
        load_controllers_after_spawn,
        rviz_node,
    ])
