"""scan_fix: odwraca LaserScan z Webots, żeby slam_toolbox zbudował prostą mapę.

Lidar TurtleBot3 w webots_ros2 publikuje /scan „od tyłu”: pomiary idą od kąta
+π do -π (angle_min = +3.14, angle_max = -3.14, angle_increment < 0).
Standard dla LaserScan zakłada kąty rosnące (increment > 0). slam_toolbox źle
radzi sobie z ujemnym krokiem i rysuje wygięte, podwójne ściany.

Ten node robi tylko jedno: dostaje skan z 'scan' i publikuje ten sam pomiar
na 'scan_fixed', ale ułożony od -π do +π:
  - zamienia angle_min z angle_max,
  - zmienia znak angle_increment na dodatni,
  - odwraca kolejność ranges i intensities.
Punkty w przestrzeni zostają dokładnie tam, gdzie były; zmienia się tylko
kolejność, w jakiej są zapisane. Gdy skan już jest „w dobrą stronę”
(increment > 0), node przekazuje go bez zmian.

Uruchomienie (samodzielnie):
    ros2 run m7_nav2_capstone scan_fix --ros-args -p use_sim_time:=true
Zwykle startuje go launch slam_w3.launch.py razem z slam_toolbox.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


class ScanFix(Node):

    def __init__(self):
        super().__init__('scan_fix')
        self.pub = self.create_publisher(LaserScan, 'scan_fixed', qos_profile_sensor_data)
        self.create_subscription(LaserScan, 'scan', self.on_scan, qos_profile_sensor_data)
        self.reported = False

    def on_scan(self, msg):
        if msg.angle_increment < 0.0:
            if not self.reported:
                self.get_logger().info(
                    f'/scan jest odwrócony (angle_min={msg.angle_min:.2f}, '
                    f'angle_increment={msg.angle_increment:.4f}), publikuję poprawiony na /scan_fixed')
                self.reported = True
            msg.angle_min, msg.angle_max = msg.angle_max, msg.angle_min
            msg.angle_increment = -msg.angle_increment
            msg.ranges = list(reversed(msg.ranges))
            msg.intensities = list(reversed(msg.intensities))
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ScanFix()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
