#!/usr/bin/env python3
"""color_detector (ROZWIĄZANIE) — pełny pipeline percepcji z M10.

Subskrybuje /image_raw → cv_bridge → OpenCV (HSV, próg, kontur/momenty) →
publikuje /ball_position (PointStamped, piksele) + /image_annotated (podgląd).

Podgląd: ros2 run rqt_image_view rqt_image_view  (topic /image_annotated)
"""
import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import PointStamped
from rclpy.node import Node
from sensor_msgs.msg import Image

# Zakres ZIELONEGO w HSV (OpenCV: H 0-179, S/V 0-255).
# Zielony nie „zawija" huego jak czerwony — jeden zakres wystarcza.
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
        # 1) ROS Image -> numpy (BGR jak lubi OpenCV)
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        # 2) BGR -> HSV i próg koloru (maska 0/255)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, HSV_LO, HSV_HI)

        # 3) centroid maski z momentów obrazu
        m = cv2.moments(mask)
        if m['m00'] > 500:                      # próg: jest sensowna plama
            u = m['m10'] / m['m00']             # piksele: kolumna (x)
            v = m['m01'] / m['m00']             # piksele: wiersz (y)

            out = PointStamped()
            out.header = msg.header             # ten sam stamp i frame_id co klatka!
            out.point.x = float(u)
            out.point.y = float(v)
            out.point.z = 0.0                   # 2D — głębi tu nie znamy (patrz M10 sekcja 6)
            self.pub_pos.publish(out)

            cv2.circle(frame, (int(u), int(v)), 6, (0, 0, 255), 2)
            cv2.putText(frame, f'({u:.0f},{v:.0f})', (int(u) + 10, int(v)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # 4) opublikuj podgląd z adnotacją (numpy -> ROS Image)
        ann = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        ann.header = msg.header
        self.pub_img.publish(ann)


def main():
    rclpy.init()
    rclpy.spin(ColorDetector())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
