#!/usr/bin/env python3
"""color_detector (SZKIELET) — Twoje zadanie z M10.

Cel: znaleźć zieloną kulę w obrazie z /image_raw i publikować jej pozycję
(w pikselach) na /ball_position + obraz z adnotacją na /image_annotated.

Wypełnij cztery TODO. Sprawdzian:
  ros2 topic hz /ball_position     # ~15 Hz
  ros2 topic echo /ball_position   # x/y zmieniają się (kula krąży!)
Utknąłeś? Podejrzyj color_detector_solution.py.
"""
import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import PointStamped
from rclpy.node import Node
from sensor_msgs.msg import Image

# Zakres ZIELONEGO w HSV (OpenCV: H 0-179, S/V 0-255)
HSV_LO = (45, 80, 80)
HSV_HI = (85, 255, 255)


class ColorDetector(Node):
    def __init__(self):
        super().__init__('color_detector')
        self.bridge = CvBridge()
        self.sub = self.create_subscription(Image, '/image_raw', self.on_image, 10)
        self.pub_pos = self.create_publisher(PointStamped, '/ball_position', 10)
        self.pub_img = self.create_publisher(Image, '/image_annotated', 10)
        self.get_logger().info('color_detector: czekam na /image_raw...')

    def on_image(self, msg: Image):
        # TODO 1: zamień ROS Image na obraz numpy w BGR
        #   frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        frame = None  # <- podmień

        # TODO 2: BGR -> HSV (cv2.cvtColor) i maska koloru (cv2.inRange z HSV_LO/HSV_HI)
        mask = None   # <- podmień

        # TODO 3: centroid maski z momentów (cv2.moments); publikuj tylko gdy m['m00'] > 500
        #   u = m['m10']/m['m00'] (kolumna), v = m['m01']/m['m00'] (wiersz)
        #   PointStamped: header = msg.header (ten sam stamp+frame!), point.x=u, point.y=v
        # ...

        # TODO 4: narysuj kółko w (u,v) na frame (cv2.circle) i opublikuj
        #   na /image_annotated przez self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        # ...


def main():
    rclpy.init()
    rclpy.spin(ColorDetector())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
