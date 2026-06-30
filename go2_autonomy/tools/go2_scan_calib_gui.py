#!/usr/bin/env python3
"""GUI do online kalibracji cloud→laserscan dla Go2.

Suwaki/pola na żywo: źródło chmury, pas wysokości (min/max_height), zasięg
(range_min/max), oraz korekta rotacji (roll/pitch/yaw, z) — gdybyś użył surowej
chmury. DOMYŚLNIE /utlidar/cloud_base (już w base_link — firmware zna montaż
lidaru, więc rotacja = 0). Publikuje /scan_calib (frame base_link) — podglądasz
w RViz (Fixed Frame base_link lub map). Pokazuje liczbę wiązek na żywo.

Gdy scan zarysuje ściany → klik "Pokaż wartości do configu" i przepisz do
pointcloud_to_laserscan.yaml (cloud_in/height/range) [+ static_tf_lidar jeśli
zmieniałeś rotację].

Wymaga: pip install PyQt6 ; robot online (publikuje /utlidar/cloud_base).
Uruchom: python3 tools/go2_scan_calib_gui.py   (env go2 + ros2 daemon stop)
"""
from __future__ import annotations
import math, sys, threading
import numpy as np
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2, LaserScan
from std_msgs.msg import Header
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (QApplication, QWidget, QFormLayout, QDoubleSpinBox,
                             QComboBox, QLabel, QPushButton, QVBoxLayout, QPlainTextEdit)


class Calib:
    def __init__(self, node):
        self.node = node
        self.p = dict(cloud_in='/utlidar/cloud_base', roll=0.0, pitch=0.0, yaw=0.0,
                      z=0.0, min_height=-0.40, max_height=0.20, range_min=0.30, range_max=10.0,
                      angle_increment=0.0087)
        self.beams = 0; self.total = 0
        self.pub = node.create_publisher(LaserScan, '/scan_calib', qos_profile_sensor_data)
        self.sub = None
        self._resub()

    def _resub(self):
        if self.sub is not None:
            self.node.destroy_subscription(self.sub)
        self.sub = self.node.create_subscription(
            PointCloud2, self.p['cloud_in'], self._cb, qos_profile_sensor_data)

    def _R(self):
        cr, sr = math.cos(self.p['roll']), math.sin(self.p['roll'])
        cp, sp = math.cos(self.p['pitch']), math.sin(self.p['pitch'])
        cy, sy = math.cos(self.p['yaw']), math.sin(self.p['yaw'])
        Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
        Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
        Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
        return Rz @ Ry @ Rx

    def _cb(self, m):
        a = np.frombuffer(m.data, dtype=np.uint8).reshape(-1, m.point_step)
        p = a[:, :12].copy().view(np.float32).reshape(-1, 3)
        p = p[np.isfinite(p).all(1)]
        if (self.p['roll'] or self.p['pitch'] or self.p['yaw']):
            p = (self._R() @ p.T).T
        bz = p[:, 2] + self.p['z']
        rng = np.hypot(p[:, 0], p[:, 1]); ang = np.arctan2(p[:, 1], p[:, 0])
        keep = ((bz >= self.p['min_height']) & (bz <= self.p['max_height']) &
                (rng >= self.p['range_min']) & (rng <= self.p['range_max']))
        rng, ang = rng[keep], ang[keep]
        inc = self.p['angle_increment']; n = int(round(2 * math.pi / inc))
        scan = np.full(n, np.inf, dtype=np.float32)
        if len(rng):
            idx = np.clip(((ang + math.pi) / inc).astype(int), 0, n - 1)
            np.minimum.at(scan, idx, rng)
        self.beams = int(np.isfinite(scan).sum()); self.total = n
        msg = LaserScan(); import time as _t; w = _t.time()
        msg.header = Header(); msg.header.stamp.sec = int(w); msg.header.stamp.nanosec = int((w - int(w)) * 1e9)
        msg.header.frame_id = 'base_link'
        msg.angle_min = -math.pi; msg.angle_max = math.pi; msg.angle_increment = inc
        msg.range_min = 0.0; msg.range_max = float(self.p['range_max']) + 1.0
        msg.ranges = scan.tolist()
        self.pub.publish(msg)


def spin(node):
    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.1)


def main():
    rclpy.init()
    node = rclpy.create_node('scan_calib_gui')
    cal = Calib(node)
    threading.Thread(target=spin, args=(node,), daemon=True).start()

    app = QApplication(sys.argv)
    w = QWidget(); w.setWindowTitle('Go2 scan calib (/scan_calib)')
    form = QFormLayout()

    src = QComboBox(); src.addItems(['/utlidar/cloud_base', '/utlidar/cloud', '/utlidar/cloud_deskewed'])
    def on_src(t): cal.p['cloud_in'] = t; cal._resub()
    src.currentTextChanged.connect(on_src)
    form.addRow('źródło chmury', src)

    def mk(key, lo, hi, step, dec, deg=False):
        s = QDoubleSpinBox(); s.setRange(lo, hi); s.setSingleStep(step); s.setDecimals(dec)
        s.setValue(math.degrees(cal.p[key]) if deg else cal.p[key])
        def on(v): cal.p[key] = math.radians(v) if deg else v
        s.valueChanged.connect(on); return s

    form.addRow('min_height [m]', mk('min_height', -3, 3, 0.02, 2))
    form.addRow('max_height [m]', mk('max_height', -3, 3, 0.02, 2))
    form.addRow('range_min [m]', mk('range_min', 0, 5, 0.05, 2))
    form.addRow('range_max [m]', mk('range_max', 0.5, 30, 0.5, 1))
    form.addRow('roll [°]', mk('roll', -180, 180, 1, 1, deg=True))
    form.addRow('pitch [°]', mk('pitch', -180, 180, 1, 1, deg=True))
    form.addRow('yaw [°]', mk('yaw', -180, 180, 1, 1, deg=True))
    form.addRow('z offset [m]', mk('z', -2, 2, 0.02, 2))

    beams = QLabel('wiązek: …')
    out = QPlainTextEdit(); out.setReadOnly(True); out.setMaximumHeight(120)
    btn = QPushButton('Pokaż wartości do configu')
    def show_vals():
        out.setPlainText(
            f"# pointcloud_to_laserscan.yaml\n"
            f"    cloud_in: {cal.p['cloud_in']}   # (remap cloud_in w launchu)\n"
            f"    target_frame: base_link\n"
            f"    min_height: {cal.p['min_height']:.2f}\n    max_height: {cal.p['max_height']:.2f}\n"
            f"    range_min: {cal.p['range_min']:.2f}\n    range_max: {cal.p['range_max']:.1f}\n"
            f"# static_tf_lidar (tylko jeśli źródło = surowa cloud i zmieniałeś rotację):\n"
            f"  --roll {cal.p['roll']:.4f} --pitch {cal.p['pitch']:.4f} --yaw {cal.p['yaw']:.4f} --z {cal.p['z']:.2f}")
    btn.clicked.connect(show_vals)

    lay = QVBoxLayout(); lay.addLayout(form); lay.addWidget(beams); lay.addWidget(btn); lay.addWidget(out)
    w.setLayout(lay); w.resize(420, 520); w.show()

    t = QTimer(); t.timeout.connect(lambda: beams.setText(
        f"<b>wiązek: {cal.beams} / {cal.total}</b>  (źródło: {cal.p['cloud_in']})"))
    t.start(300)

    app.exec()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
