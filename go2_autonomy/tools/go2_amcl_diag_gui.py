#!/usr/bin/env python3
"""GUI diagnostyczne AMCL — czemu gubi się w ruchu / ściany rozjeżdżają ze scanem.

Liczy NA ŻYWO kluczowe metryki i pokazuje je z sparkline + auto-diagnozą:

  • scan-match score [%]  — ile promieni /scan ląduje na ZAJĘTYCH komórkach mapy
    (po transformacie przez aktualne TF map->base_link). To BEZPOŚREDNI wskaźnik
    "ściany pokrywają się ze scanem". Wysoki = dobra lokalizacja; spada w ruchu =
    AMCL gubi się.
  • AMCL covariance (x,y,yaw) — rośnie = filtr traci pewność/dywerguje.
  • |vyaw|, |vx| (z /cmd_vel) — by SKORELOWAĆ spadek score z prędkością obrotu.
  • TF latencja (now - scan.stamp) — duża + szybki obrót = scan "z tyłu".
  • odom vs amcl yaw-rate — czy model ruchu (odom) zgadza się z lokalizacją.
  • scan pts — gęstość (za rzadki = AMCL niepewny).

CSV log (przycisk) do offline korelacji score vs vyaw.

Uruchom (env go2 + stack działa, poza ustawiona):
  ros2 daemon stop; sleep 1
  python3 tools/go2_amcl_diag_gui.py
"""
from __future__ import annotations
import math, sys, time, threading, collections
import numpy as np
import rclpy
from rclpy.qos import qos_profile_sensor_data, QoSProfile, QoSDurabilityPolicy
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import OccupancyGrid, Odometry
from geometry_msgs.msg import Twist, PoseWithCovarianceStamped
import tf2_ros
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QGridLayout,
                             QPushButton, QPlainTextEdit)


class Spark(QWidget):
    def __init__(self, lo=0, hi=100, color='#2e9'):
        super().__init__(); self.buf = collections.deque(maxlen=240)
        self.lo, self.hi, self.color = lo, hi, color; self.setMinimumHeight(46)
    def push(self, v):
        self.buf.append(v); self.update()
    def paintEvent(self, e):
        p = QPainter(self); p.fillRect(self.rect(), QColor('#111'))
        if len(self.buf) < 2: return
        w, h = self.width(), self.height()
        p.setPen(QPen(QColor(self.color), 1.5))
        n = len(self.buf); span = max(1e-6, self.hi - self.lo)
        pts = []
        for i, v in enumerate(self.buf):
            x = w * i / (self.buf.maxlen - 1)
            y = h - h * (min(max(v, self.lo), self.hi) - self.lo) / span
            pts.append((x, y))
        for a, b in zip(pts, pts[1:]):
            p.drawLine(int(a[0]), int(a[1]), int(b[0]), int(b[1]))


class Diag:
    def __init__(self, node):
        self.node = node
        self.map = None; self.scan_pts = 0; self.score = 0.0
        self.cov = (0, 0, 0); self.vx = 0.0; self.vyaw = 0.0
        self.tf_lat = 0.0; self.odom_yaw = None; self.amcl_yaw = None
        self.odom_rate = 0.0; self.amcl_rate = 0.0
        self._oprev = None; self._aprev = None
        mq = QoSProfile(depth=1); mq.durability = QoSDurabilityPolicy.TRANSIENT_LOCAL
        node.create_subscription(OccupancyGrid, '/map', self._map, mq)
        node.create_subscription(LaserScan, '/scan', self._scan, qos_profile_sensor_data)
        node.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self._amcl, 10)
        node.create_subscription(Odometry, '/utlidar/robot_odom', self._odom, qos_profile_sensor_data)
        node.create_subscription(Twist, '/cmd_vel', self._cmd, 10)
        self.tfb = tf2_ros.Buffer(); tf2_ros.TransformListener(self.tfb, node)

    def _map(self, m):
        self.map = (np.array(m.data, np.int16).reshape(m.info.height, m.info.width),
                    m.info.resolution, m.info.origin.position.x, m.info.origin.position.y,
                    m.info.width, m.info.height)

    def _cmd(self, m): self.vx = m.linear.x; self.vyaw = m.angular.z

    def _amcl(self, m):
        c = m.pose.covariance; self.cov = (c[0], c[7], c[35])
        q = m.pose.pose.orientation
        y = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        t = time.time()
        if self._aprev: self.amcl_rate = math.degrees(self._angdiff(y, self._aprev[0]))/max(1e-3, t-self._aprev[1])
        self._aprev = (y, t); self.amcl_yaw = math.degrees(y)

    def _odom(self, m):
        q = m.pose.pose.orientation
        y = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        t = time.time()
        if self._oprev: self.odom_rate = math.degrees(self._angdiff(y, self._oprev[0]))/max(1e-3, t-self._oprev[1])
        self._oprev = (y, t); self.odom_yaw = math.degrees(y)

    @staticmethod
    def _angdiff(a, b): return math.atan2(math.sin(a-b), math.cos(a-b))

    def _scan(self, m):
        self.tf_lat = time.time() - (m.header.stamp.sec + m.header.stamp.nanosec*1e-9)
        r = np.array(m.ranges); a = m.angle_min + np.arange(len(r))*m.angle_increment
        f = np.isfinite(r) & (r > m.range_min) & (r < m.range_max)
        r, a = r[f], a[f]; self.scan_pts = len(r)
        if self.map is None or not len(r): self.score = 0.0; return
        try:
            tr = self.tfb.lookup_transform('map', m.header.frame_id, rclpy.time.Time())
        except Exception:
            self.score = -1.0; return   # -1 = brak TF
        tx, ty = tr.transform.translation.x, tr.transform.translation.y
        q = tr.transform.rotation
        yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        wx = tx + r*np.cos(a+yaw); wy = ty + r*np.sin(a+yaw)
        grid, res, ox, oy, W, H = self.map
        gx = ((wx-ox)/res).astype(int); gy = ((wy-oy)/res).astype(int)
        ok = (gx >= 0)&(gx < W)&(gy >= 0)&(gy < H)
        hit = 0
        if ok.any():
            # trafienie = zajęta komórka lub sąsiad (tolerancja 1 px na grubość ściany)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    gxx = np.clip(gx[ok]+dx, 0, W-1); gyy = np.clip(gy[ok]+dy, 0, H-1)
                    hit = np.maximum(hit, (grid[gyy, gxx] > 50)) if isinstance(hit, np.ndarray) else (grid[gyy, gxx] > 50)
            hit = int(hit.sum())
        self.score = 100.0 * hit / len(r)


def spin(node):
    while rclpy.ok(): rclpy.spin_once(node, timeout_sec=0.05)


def main():
    rclpy.init(); node = rclpy.create_node('amcl_diag'); d = Diag(node)
    threading.Thread(target=spin, args=(node,), daemon=True).start()
    app = QApplication(sys.argv)
    w = QWidget(); w.setWindowTitle('Go2 AMCL diag'); w.resize(560, 640)
    g = QGridLayout(); rows = {}
    def row(i, name):
        g.addWidget(QLabel(f'<b>{name}</b>'), i, 0); lab = QLabel('…'); g.addWidget(lab, i, 1)
        sp = Spark(); g.addWidget(sp, i, 2); rows[name] = (lab, sp); return sp
    s_score = row(0, 'scan-match %'); s_score.lo, s_score.hi, s_score.color = 0, 100, '#2e9'
    s_cov = row(1, 'cov yaw'); s_cov.lo, s_cov.hi, s_cov.color = 0, 0.3, '#e93'
    s_vyaw = row(2, '|vyaw| °/s'); s_vyaw.lo, s_vyaw.hi, s_vyaw.color = 0, 60, '#39e'
    s_lat = row(3, 'TF lat s'); s_lat.lo, s_lat.hi, s_lat.color = 0, 0.5, '#e39'
    s_pts = row(4, 'scan pts'); s_pts.lo, s_pts.hi, s_pts.color = 0, 200, '#9e3'
    s_drate = row(5, 'odom-amcl °/s'); s_drate.lo, s_drate.hi, s_drate.color = 0, 30, '#e33'

    diagbox = QPlainTextEdit(); diagbox.setReadOnly(True); diagbox.setMaximumHeight(150)
    csv = {'f': None}
    btn = QPushButton('Start CSV log')
    def toggle():
        if csv['f'] is None:
            csv['f'] = open('/tmp/amcl_diag.csv', 'w')
            csv['f'].write('t,score,cov_yaw,vyaw_dps,tf_lat,scan_pts,odom_rate,amcl_rate\n')
            btn.setText('Stop CSV (/tmp/amcl_diag.csv)')
        else:
            csv['f'].close(); csv['f'] = None; btn.setText('Start CSV log')
    btn.clicked.connect(toggle)

    lay = QVBoxLayout(); lay.addLayout(g); lay.addWidget(btn); lay.addWidget(QLabel('<b>Auto-diagnoza:</b>')); lay.addWidget(diagbox)
    w.setLayout(lay); w.show()

    def tick():
        vyaw_dps = abs(math.degrees(d.vyaw))
        drate = abs(d.odom_rate - d.amcl_rate)
        rows['scan-match %'][0].setText(f"{d.score:.0f}%" if d.score >= 0 else "BRAK TF map→base")
        rows['cov yaw'][0].setText(f"{d.cov[2]:.3f}  (x {d.cov[0]:.3f} y {d.cov[1]:.3f})")
        rows['|vyaw| °/s'][0].setText(f"{vyaw_dps:.0f}  (vx {d.vx:.2f})")
        rows['TF lat s'][0].setText(f"{d.tf_lat:.2f}")
        rows['scan pts'][0].setText(f"{d.scan_pts}")
        rows['odom-amcl °/s'][0].setText(f"{drate:.1f}  (odom {d.odom_rate:.0f} amcl {d.amcl_rate:.0f})")
        s_score.push(max(0, d.score)); s_cov.push(d.cov[2]); s_vyaw.push(vyaw_dps)
        s_lat.push(d.tf_lat); s_pts.push(d.scan_pts); s_drate.push(drate)
        # auto-diagnoza
        msgs = []
        if d.score < 0: msgs.append("✗ brak TF map→base_link — AMCL nie zlokalizowany / nie ustawiłeś pozy")
        elif d.score < 40: msgs.append(f"✗ niski scan-match ({d.score:.0f}%) — scan NIE pasuje do mapy TERAZ")
        if d.scan_pts < 40: msgs.append(f"⚠ scan rzadki ({d.scan_pts} pkt) — AMCL ma mało odniesień (poszerz height band)")
        if vyaw_dps > 35 and d.score < 60: msgs.append(f"⚠ score spada przy szybkim obrocie ({vyaw_dps:.0f}°/s) — zwolnij rotate_to_heading lub zmniejsz TF lat")
        if d.tf_lat > 0.25: msgs.append(f"⚠ duża latencja scanu ({d.tf_lat:.2f}s) — scan 'z tyłu' przy obrocie")
        if d.cov[2] > 0.2: msgs.append(f"⚠ cov yaw rośnie ({d.cov[2]:.2f}) — filtr traci pewność")
        if drate > 8: msgs.append(f"✗ odom vs amcl yaw-rate rozjazd ({drate:.0f}°/s) — model ruchu (odom) zły")
        if not msgs and d.score >= 60: msgs.append(f"✓ OK — scan-match {d.score:.0f}%, cov {d.cov[2]:.3f}")
        diagbox.setPlainText("\n".join(msgs))
        if csv['f']:
            csv['f'].write(f"{time.time():.2f},{d.score:.1f},{d.cov[2]:.4f},{vyaw_dps:.1f},{d.tf_lat:.3f},{d.scan_pts},{d.odom_rate:.1f},{d.amcl_rate:.1f}\n")
    t = QTimer(); t.timeout.connect(tick); t.start(200)
    app.exec(); rclpy.shutdown()


if __name__ == '__main__':
    main()
