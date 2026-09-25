#!/usr/bin/env python3
"""Relay QoS dla LaserScan: best_effort IN → reliable OUT.

Po co: pointcloud_to_laserscan publikuje /scan jako BEST_EFFORT (SensorDataQoS).
Subskrybent RELIABLE (np. display LaserScan w RViz z domyślnym Reliability=Reliable
albo własny węzeł z domyślnym QoS) nie dostanie od takiego publishera nic - w logu
pojawi się WARN o niezgodnym QoS. Ten relay subskrybuje BEST_EFFORT i republikuje
jako RELIABLE.

slam_toolbox tego NIE wymaga: subskrybuje skan profilem sensor_data (BEST_EFFORT),
więc czytałby /scan bezpośrednio. mapping.launch.py podaje mu /scan_reliable, bo na
tej konfiguracji stack był walidowany na robocie - to wygoda, nie wymóg.

Użycie (w go2_bringup/launch/mapping.launch.py startuje automatycznie):
  ros2 run go2_bringup scan_qos_relay --in /scan --out /scan_reliable
"""
from __future__ import annotations
import argparse, sys
import rclpy
from rclpy.qos import qos_profile_sensor_data, QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import LaserScan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='in_topic', default='/scan')
    ap.add_argument('--out', dest='out_topic', default='/scan_reliable')
    # parsuj tylko znane (ros2 dorzuca --ros-args)
    args, _ = ap.parse_known_args()

    rclpy.init()
    node = rclpy.create_node('scan_qos_relay')
    out_qos = QoSProfile(depth=10)
    out_qos.reliability = QoSReliabilityPolicy.RELIABLE
    out_qos.history = QoSHistoryPolicy.KEEP_LAST
    pub = node.create_publisher(LaserScan, args.out_topic, out_qos)
    node.create_subscription(LaserScan, args.in_topic, lambda m: pub.publish(m),
                             qos_profile_sensor_data)
    node.get_logger().info(f'scan_qos_relay: {args.in_topic} (best_effort) -> '
                           f'{args.out_topic} (reliable)')
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node(); rclpy.shutdown()


if __name__ == '__main__':
    main()
