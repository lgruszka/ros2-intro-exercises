#!/usr/bin/env python3
"""Online kalibrator cloud→laserscan dla Go2 L1.

Własny pointcloud_to_laserscan z DYNAMICZNYMI parametrami: strojysz orientację
lidaru (roll/pitch/yaw), wysokość (z), pas wysokości (min/max_height) i zasięg
(range_min/max) przez `ros2 param set` i NATYCHMIAST widzisz /scan_calib w RViz —
bez restartu stacku. Gdy znajdziesz dobre wartości → wpisz je do:
  - static_tf_lidar (roll/pitch/yaw/z) w real.launch.py,
  - pointcloud_to_laserscan.yaml (min/max_height, range_min/max).

Subskrybuje /utlidar/cloud (surowa), publikuje /scan_calib (frame_id=base_link).
Node sam liczy transform — NIE potrzebuje TF ani stacku do strojenia kształtu
(w RViz ustaw Fixed Frame = base_link). Do nałożenia na mapę odpal też stack.

Użycie:
  python3 tools/go2_scan_calib_node.py
  # w drugim terminalu, na żywo:
  ros2 param set /scan_calib pitch -0.30
  ros2 param set /scan_calib yaw 0.78
  ros2 param set /scan_calib min_height 0.35
  ros2 param set /scan_calib max_height 0.60
  ros2 param set /scan_calib range_min 0.6
  ros2 param list /scan_calib            # wszystkie pokrętła
Node co ~1s wypisuje liczbę wiązek (czy pas daje dość punktów ścian).
"""
from __future__ import annotations
import math, time
import numpy as np
import rclpy
from rclpy.node import Node
from rcl_interfaces.msg import SetParametersResult
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2, LaserScan
from std_msgs.msg import Header


class ScanCalib(Node):
    def __init__(self):
        super().__init__('scan_calib')
        # pokrętła (dynamiczne)
        defs = dict(cloud_in='/utlidar/cloud', scan_out='/scan_calib',
                    out_frame='base_link',
                    roll=0.0, pitch=-0.285, yaw=0.0, z=0.4,
                    min_height=0.30, max_height=0.55,
                    range_min=0.55, range_max=10.0,
                    angle_increment=0.0087)
        for k, v in defs.items():
            self.declare_parameter(k, v)
        self.p = {k: self.get_parameter(k).value for k in defs}
        self.add_on_set_parameters_callback(self._on_set)

        self._pub = self.create_publisher(LaserScan, str(self.p['scan_out']), qos_profile_sensor_data)
        self.create_subscription(PointCloud2, str(self.p['cloud_in']), self._on_cloud, qos_profile_sensor_data)
        self._last_log = 0.0
        self.get_logger().info(f"scan_calib gotowy: {self.p['cloud_in']} -> {self.p['scan_out']} "
                               f"(frame {self.p['out_frame']}). Stroisz przez 'ros2 param set /scan_calib ...'")

    def _on_set(self, params):
        for pr in params:
            if pr.name in self.p:
                self.p[pr.name] = pr.value
        return SetParametersResult(successful=True)

    def _R(self):
        cr, sr = math.cos(self.p['roll']), math.sin(self.p['roll'])
        cp, sp = math.cos(self.p['pitch']), math.sin(self.p['pitch'])
        cy, sy = math.cos(self.p['yaw']), math.sin(self.p['yaw'])
        Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
        Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
        Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
        return Rz @ Ry @ Rx

    def _on_cloud(self, m: PointCloud2):
        a = np.frombuffer(m.data, dtype=np.uint8).reshape(-1, m.point_step)
        p = a[:, :12].copy().view(np.float32).reshape(-1, 3)
        p = p[np.isfinite(p).all(1)]
        b = (self._R() @ p.T).T
        b[:, 2] += self.p['z']
        rng = np.hypot(b[:, 0], b[:, 1])
        ang = np.arctan2(b[:, 1], b[:, 0])
        keep = ((b[:, 2] >= self.p['min_height']) & (b[:, 2] <= self.p['max_height']) &
                (rng >= self.p['range_min']) & (rng <= self.p['range_max']))
        rng, ang = rng[keep], ang[keep]
        inc = float(self.p['angle_increment']); amin, amax = -math.pi, math.pi
        n = int(round((amax - amin) / inc))
        scan = np.full(n, np.inf, dtype=np.float32)
        if len(rng):
            idx = np.clip(((ang - amin) / inc).astype(int), 0, n - 1)
            for i, r in zip(idx, rng):
                if r < scan[i]:
                    scan[i] = r
        msg = LaserScan()
        wn = time.time(); msg.header = Header()
        msg.header.stamp.sec = int(wn); msg.header.stamp.nanosec = int((wn - int(wn)) * 1e9)
        msg.header.frame_id = str(self.p['out_frame'])
        msg.angle_min = amin; msg.angle_max = amax; msg.angle_increment = inc
        msg.range_min = 0.0; msg.range_max = float(self.p['range_max']) + 1.0
        msg.ranges = scan.tolist()
        self._pub.publish(msg)
        if wn - self._last_log > 1.0:
            self._last_log = wn
            nb = int(np.isfinite(scan).sum())
            self.get_logger().info(
                f"wiązek={nb}/{n}  | roll={math.degrees(self.p['roll']):.0f} "
                f"pitch={math.degrees(self.p['pitch']):.0f} yaw={math.degrees(self.p['yaw']):.0f}° "
                f"z[{self.p['min_height']:.2f},{self.p['max_height']:.2f}] r_min={self.p['range_min']:.2f}")


def main():
    rclpy.init(); n = ScanCalib()
    try: rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally:
        n.destroy_node(); rclpy.shutdown()


if __name__ == '__main__':
    main()
