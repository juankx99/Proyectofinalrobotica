#!/usr/bin/env python3
"""
Proyecto final - Nodo de misiones autonomas con nav2_simple_commander.

- Lee una secuencia de waypoints desde un archivo YAML (parametro waypoints_file).
- Expone el servicio /start_mission (std_srvs/Trigger) para iniciar la mision
  y /cancel_mission (std_srvs/Trigger) para cancelarla.
- Publica el estado en /mission_status (std_msgs/String) y los waypoints como
  marcadores en /mission_waypoints (visualization_msgs/MarkerArray) para RViz.

Uso:
  ros2 launch dif_bot_nav mission.launch.py
  ros2 service call /start_mission std_srvs/srv/Trigger
"""
import math
import threading
import time

import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import String
from std_srvs.srv import Trigger
from visualization_msgs.msg import Marker, MarkerArray


def yaw_to_quaternion(yaw):
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)


class MissionNode(Node):

    def __init__(self):
        super().__init__('mission_node')
        default_file = get_package_share_directory('dif_bot_nav') + '/config/waypoints.yaml'
        self.declare_parameter('waypoints_file', default_file)

        self.mission = self.load_mission(self.get_parameter('waypoints_file').value)
        self.frame = self.mission.get('frame_id', 'map')
        self.waypoints = self.mission['waypoints']

        # Navegador de Nav2 (es un nodo aparte, se usa desde un hilo propio)
        self.nav = BasicNavigator(node_name='mission_navigator')
        self.nav.set_parameters([Parameter('use_sim_time', Parameter.Type.BOOL, True)])

        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.status_pub = self.create_publisher(String, 'mission_status', latched)
        self.marker_pub = self.create_publisher(MarkerArray, 'mission_waypoints', latched)
        self.create_service(Trigger, 'start_mission', self.on_start)
        self.create_service(Trigger, 'cancel_mission', self.on_cancel)

        self.ready = False
        self.running = False
        self.cancel_requested = False
        self.publish_markers()
        self.set_status(f'Cargados {len(self.waypoints)} waypoints. Esperando a Nav2...')
        threading.Thread(target=self.wait_for_nav2, daemon=True).start()

    # ------------------------------------------------------------------ utilidades
    def load_mission(self, path):
        with open(path, 'r') as f:
            data = yaml.safe_load(f)['mission']
        if not data.get('waypoints'):
            raise RuntimeError(f'El archivo {path} no tiene waypoints')
        self.get_logger().info(f'Mision leida de {path}')
        return data

    def make_pose(self, x, y, yaw):
        p = PoseStamped()
        p.header.frame_id = self.frame
        p.pose.position.x = float(x)
        p.pose.position.y = float(y)
        qx, qy, qz, qw = yaw_to_quaternion(float(yaw))
        p.pose.orientation.x, p.pose.orientation.y = qx, qy
        p.pose.orientation.z, p.pose.orientation.w = qz, qw
        return p

    def set_status(self, text):
        self.get_logger().info(text)
        self.status_pub.publish(String(data=text))

    def publish_markers(self):
        arr = MarkerArray()
        for i, wp in enumerate(self.waypoints):
            m = Marker()
            m.header.frame_id = self.frame
            m.ns, m.id, m.type, m.action = 'waypoints', i, Marker.ARROW, Marker.ADD
            m.pose = self.make_pose(wp['x'], wp['y'], wp['yaw']).pose
            m.scale.x, m.scale.y, m.scale.z = 0.45, 0.10, 0.10
            m.color.r, m.color.g, m.color.b, m.color.a = 1.0, 0.55, 0.0, 1.0
            arr.markers.append(m)
            t = Marker()
            t.header.frame_id = self.frame
            t.ns, t.id, t.type, t.action = 'labels', i, Marker.TEXT_VIEW_FACING, Marker.ADD
            t.pose.position.x, t.pose.position.y, t.pose.position.z = \
                float(wp['x']), float(wp['y']) + 0.35, 0.5
            t.pose.orientation.w = 1.0
            t.scale.z = 0.28
            t.color.r = t.color.g = t.color.b = t.color.a = 1.0
            t.text = f"{i + 1}. {wp['name']}"
            arr.markers.append(t)
        self.marker_pub.publish(arr)

    # ------------------------------------------------------------------ arranque
    def wait_for_nav2(self):
        ip = self.mission.get('initial_pose', {'x': 0.0, 'y': 0.0, 'yaw': 0.0})
        self.nav.setInitialPose(self.make_pose(ip['x'], ip['y'], ip['yaw']))
        self.nav.waitUntilNav2Active(navigator='bt_navigator', localizer='amcl')
        self.ready = True
        self.set_status('Nav2 activo. Llama al servicio /start_mission para iniciar.')

    # ------------------------------------------------------------------ servicios
    def on_start(self, request, response):
        if not self.ready:
            response.success, response.message = False, 'Nav2 todavia no esta activo'
        elif self.running:
            response.success, response.message = False, 'Ya hay una mision en curso'
        else:
            self.running, self.cancel_requested = True, False
            threading.Thread(target=self.run_mission, daemon=True).start()
            response.success = True
            response.message = f'Mision iniciada con {len(self.waypoints)} waypoints'
        self.get_logger().info(f'/start_mission -> {response.message}')
        return response

    def on_cancel(self, request, response):
        if not self.running:
            response.success, response.message = False, 'No hay mision en curso'
        else:
            # El hilo de la mision es quien llama a cancelTask() (el navegador
            # no se debe girar desde dos hilos a la vez)
            self.cancel_requested = True
            response.success, response.message = True, 'Cancelando mision'
        return response

    # ------------------------------------------------------------------ mision
    def run_mission(self):
        wait_s = float(self.mission.get('wait_at_waypoint', 0.0))
        loop = bool(self.mission.get('loop', False))
        lap = 0
        while True:
            lap += 1
            results = []
            t0 = time.time()
            for i, wp in enumerate(self.waypoints):
                if self.cancel_requested:
                    break
                n = len(self.waypoints)
                self.set_status(f'[{i + 1}/{n}] Navegando a "{wp["name"]}" '
                                f'({wp["x"]:.2f}, {wp["y"]:.2f})')
                self.nav.goToPose(self.make_pose(wp['x'], wp['y'], wp['yaw']))
                last_log = 0.0
                while not self.nav.isTaskComplete():
                    if self.cancel_requested:
                        self.nav.cancelTask()
                        break
                    fb = self.nav.getFeedback()
                    if fb and time.time() - last_log > 3.0:
                        last_log = time.time()
                        self.get_logger().info(
                            f'    distancia restante: {fb.distance_remaining:.2f} m, '
                            f'recuperaciones: {fb.number_of_recoveries}')
                    time.sleep(0.2)
                result = self.nav.getResult()
                ok = result == TaskResult.SUCCEEDED
                results.append(ok)
                estado = {TaskResult.SUCCEEDED: 'ALCANZADO',
                          TaskResult.CANCELED: 'CANCELADO',
                          TaskResult.FAILED: 'FALLIDO'}.get(result, 'DESCONOCIDO')
                if result == TaskResult.FAILED:
                    code, msg = self.nav.getTaskError()
                    estado += f' (error {code}: {msg})'
                self.set_status(f'[{i + 1}/{n}] "{wp["name"]}": {estado}')
                if ok and wait_s > 0.0:
                    time.sleep(wait_s)
            dt = time.time() - t0
            self.set_status(f'Mision terminada (vuelta {lap}): {sum(results)}/'
                            f'{len(self.waypoints)} waypoints alcanzados en {dt:.0f} s')
            if not loop or self.cancel_requested:
                break
        self.running = False


def main():
    rclpy.init()
    node = MissionNode()
    # Executor propio para este nodo: BasicNavigator usa internamente el executor
    # global de rclpy (spin_until_future_complete) desde el hilo de la mision,
    # asi que este nodo no debe girar en ese mismo executor.
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.nav.destroy_node()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
