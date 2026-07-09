#!/usr/bin/env python3
"""toy_camera — syntetyczna kamera do M10 (zero sprzętu).

Publikuje sensor_msgs/Image (bgr8, 320x240, 15 Hz) na /image_raw: szara scena
z ZIELONĄ kulą krążącą po okręgu. Deterministyczne — detektor zawsze ma co znaleźć.

To samo, co robi sterownik prawdziwej kamery (usb_cam): numpy → cv_bridge → Image.
"""
import math

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image

W, H = 320, 240
BALL_R = 22
ORBIT_R = 70          # promień okręgu, po którym krąży kula
BALL_BGR = (60, 200, 60)   # zielony (OpenCV używa BGR, nie RGB!)


class ToyCamera(Node):
    def __init__(self):
        super().__init__('toy_camera')
        self.pub = self.create_publisher(Image, '/image_raw', 10)
        self.bridge = CvBridge()
        self.theta = 0.0
        self.create_timer(1.0 / 15.0, self.tick)   # 15 Hz
        self.get_logger().info('toy_camera: publikuję /image_raw (bgr8, 320x240, 15 Hz)')

    def tick(self):
        # tło: szary gradient + delikatny szum (żeby progowanie nie było trywialne)
        frame = np.full((H, W, 3), 90, dtype=np.uint8)
        frame += np.random.randint(0, 12, (H, W, 3), dtype=np.uint8)

        # kula krąży po okręgu wokół środka kadru
        cx = int(W / 2 + ORBIT_R * math.cos(self.theta))
        cy = int(H / 2 + ORBIT_R * math.sin(self.theta) * 0.7)
        cv2.circle(frame, (cx, cy), BALL_R, BALL_BGR, -1)
        cv2.circle(frame, (cx, cy), BALL_R, (30, 120, 30), 2)
        self.theta += 0.08

        msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'toy_camera'   # frame TF kamery — jak w realnym sterowniku
        self.pub.publish(msg)


def main():
    rclpy.init()
    rclpy.spin(ToyCamera())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
