# dif_bot_nav

Navegación autónoma (SLAM, AMCL y Nav2) del robot diferencial
[`basic_dif_bot_description`](https://github.com/DanielPalominoS/basic_dif_bot_description)
en ROS 2 Kilted + Gazebo (gz sim). Proyecto final de Robótica, Escuela Colombiana de Ingeniería Julio Garavito.

## Dependencias

```bash
sudo apt install ros-kilted-ros-gz ros-kilted-gz-ros2-control ros-kilted-ros2-controllers \
  ros-kilted-xacro ros-kilted-teleop-twist-keyboard ros-kilted-slam-toolbox \
  ros-kilted-navigation2 ros-kilted-nav2-bringup
```

Clonar en el mismo workspace que `basic_dif_bot_description` y compilar con `colcon build --symlink-install`.

## Simulación

```bash
ros2 launch dif_bot_nav sim.launch.py            # servidor de Gazebo + RViz
ros2 launch dif_bot_nav sim.launch.py gui:=true  # además la ventana de Gazebo
```

Teleoperación:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
# con use_ros2_control:=true:
# ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true -r cmd_vel:=/diff_drive_controller/cmd_vel
```

## Práctica 3 — SLAM

```bash
ros2 launch dif_bot_nav slam.launch.py
# teleoperar para explorar y luego, en otra terminal:
ros2 run nav2_map_server map_saver_cli -f ~/rbtc_ws/src/dif_bot_nav/maps/mapa_casa
```

## Práctica 4 — AMCL

```bash
ros2 launch dif_bot_nav localization.launch.py
# pose inicial incorrecta (robot real en (3,-2), AMCL cree (0,0)):
ros2 launch dif_bot_nav localization.launch.py x:=3.0 y:=-2.0
# más ruido en el láser:
ros2 launch dif_bot_nav localization.launch.py lidar_noise:=0.10
```

## Práctica 5 — Nav2

```bash
ros2 launch dif_bot_nav nav2.launch.py
```
En RViz usar **2D Goal Pose** para enviar metas. Planner global NavFn, controlador Regulated Pure Pursuit.

## Proyecto final — Misión autónoma

Nodo `mission_node.py` (Python, `nav2_simple_commander`) que lee los waypoints de
`config/waypoints.yaml` y los recorre en orden cuando se llama al servicio `/start_mission`.

```bash
ros2 launch dif_bot_nav mission.launch.py gui:=true
ros2 service call /start_mission std_srvs/srv/Trigger    # iniciar
ros2 service call /cancel_mission std_srvs/srv/Trigger   # cancelar
ros2 topic echo /mission_status                          # estado
```

## Cambios respecto al paquete original

- Control por defecto con el plugin DiffDrive de Gazebo (`use_ros2_control:=false`); `ros2_control` queda como opción.
- Se quita la cámara de profundidad y el lidar baja a 10 Hz para que corra en WSL2.
- `gz_frame_id` en IMU y lidar para que los mensajes salgan en `imu_link` y `lidar_link`.
- `wheel_separation` corregido a 0.36 m (la geometría del URDF da ±0.18 m; el original usa 0.40 m).
- Mundo propio `worlds/casa.sdf` (12 m × 9 m).
