#!/usr/bin/env python3
"""Relay QoS dla LaserScan: best_effort IN → reliable OUT.

Po co: pointcloud_to_laserscan publikuje /scan jako BEST_EFFORT (SensorDataQoS,
zahardkodowane). slam_toolbox subskrybuje /scan jako RELIABLE → QoS incompatible →
slam NIE dostaje skanów → brak mapy. AMCL (best_effort) działa, ale slam nie.
Ten relay subskrybuje best_effort i republikuje jako reliable dla slam.

Użycie:
  ros2 run ... NIE — to skrypt:
  python3 tools/scan_qos_relay.py --in /scan --out /scan_reliable
Parametry ROS (gdy w launchu jako Node z executable nie zadziała — to plik):
  używamy w mapping_real.launch jako ExecuteProcess / python.
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
