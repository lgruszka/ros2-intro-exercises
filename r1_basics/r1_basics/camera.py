#!/usr/bin/env python3
"""camera - obraz z głowy R1 (strumień RTP H.264 po UDP) -> sensor_msgs/Image na /r1/camera/image_raw.

Usługa wideo R1 EDU (docs/r1_plan.md §6) wysyła H.264 RTP/UDP: port 5001 obraz 1280x720, 5002/5003
lewe/prawe oko. Węzeł odbiera go przez OpenCV VideoCapture z potokiem GStreamer i publikuje bgr8
w ramie camera_link. Uruchom go tam, dokąd dochodzi strumień UDP (domyślnie dock EDU).
Głębia (opcjonalnie): `sudo unitree_depth_start` -> /dev/video-dep (16 bit, mm) -> /r1/camera/depth (16UC1).
"""
import sys
import threading
import time

import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Image

FRAME_ID = 'camera_link'
DEFAULT_PIPELINE = (
    'udpsrc port={port} ! application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,payload=96 '
    '! rtph264depay ! avdec_h264 ! videoconvert ! video/x-raw,format=BGR '
    '! appsink drop=true sync=false max-buffers=1')
NO_FRAME_WARN_S = 3.0


def opencv_has_gstreamer():
    """Sprawdź, czy OpenCV zbudowano z GStreamerem (linia 'GStreamer: YES' w getBuildInformation)."""
    for line in cv2.getBuildInformation().splitlines():
        if 'GStreamer' in line:
            return 'YES' in line
    return False


class R1Camera(Node):
    def __init__(self):
        super().__init__('camera')
        self.port = int(self.declare_parameter('port', 5001).value)
        pipeline = self.declare_parameter('pipeline', '').value
        self.depth_device = self.declare_parameter('depth_device', '').value
        self.pipeline = (pipeline or DEFAULT_PIPELINE).replace('{port}', str(self.port))

        self.bridge = CvBridge()
        self.image_pub = self.create_publisher(Image, '/r1/camera/image_raw', 10)
        self.depth_pub = self.create_publisher(Image, '/r1/camera/depth', 10) if self.depth_device else None
        self.running = True
        self.failed = None            # opis błędu z wątku odczytu -> koniec programu
        self.frames = 0
        self.last_frame = None
        self.started = time.monotonic()
        self.create_timer(NO_FRAME_WARN_S, self.check_frames)
        self.create_timer(0.5, self.check_failed)

        self.get_logger().info(
            f'camera: potok GStreamer -> /r1/camera/image_raw ({FRAME_ID}):\n  {self.pipeline}')
        # VideoCapture z udpsrc blokuje już przy otwarciu, aż przyjdą pierwsze dane - dlatego otwieramy
        # w wątku. Główny wątek kręci executor, więc Ctrl+C działa także bez strumienia.
        threading.Thread(target=self.read_loop, daemon=True).start()
        if self.depth_device:
            threading.Thread(target=self.depth_loop, daemon=True).start()

    def stamp(self, msg):
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = FRAME_ID
        return msg

    def read_loop(self):
        cap = cv2.VideoCapture(self.pipeline, cv2.CAP_GSTREAMER)   # blokuje do pierwszych danych
        if not cap.isOpened():
            self.failed = ('nie udało się otworzyć potoku GStreamer (sprawdź wtyczki: rtph264depay z '
                           'gstreamer1.0-plugins-good, avdec_h264 z gstreamer1.0-libav)')
            return
        while self.running:
            ok, frame = cap.read()               # blokuje do następnej klatki
            if not ok or frame is None:
                time.sleep(0.05)
                continue
            if self.frames == 0:
                self.get_logger().info(f'pierwsza klatka: {frame.shape[1]}x{frame.shape[0]}')
            self.frames += 1
            self.last_frame = time.monotonic()
            self.image_pub.publish(self.stamp(self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')))

    def depth_loop(self):
        cap = cv2.VideoCapture(self.depth_device, cv2.CAP_V4L2)
        if not cap.isOpened():
            self.get_logger().error(f'nie mogę otworzyć {self.depth_device} - uruchomiono `sudo unitree_depth_start`?')
            return
        cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)     # surowe 16 bit, bez konwersji do BGR
        self.get_logger().info(f'głębia: {self.depth_device} -> /r1/camera/depth (16UC1, mm)')
        warned = False
        while self.running:
            ok, depth = cap.read()
            if not ok or depth is None:
                time.sleep(0.05)
                continue
            if depth.dtype != 'uint16' or depth.ndim != 2:
                if not warned:
                    self.get_logger().warning(
                        f'głębia: oczekiwano 16 bit 1 kanał, jest {depth.dtype} {depth.shape} - '
                        'format urządzenia do sprawdzenia na robocie')
                    warned = True
                continue
            self.depth_pub.publish(self.stamp(self.bridge.cv2_to_imgmsg(depth, encoding='16UC1')))

    def check_frames(self):
        silent = time.monotonic() - (self.last_frame or self.started)
        if silent > NO_FRAME_WARN_S:
            self.get_logger().warning(
                f'brak klatek od {silent:.0f} s na porcie {self.port}: czy usługa wideo działa '
                '(aplikacja: Ustawienia -> Stan usług), video_hub zatrzymany i strumień dochodzi do tej maszyny?')
        else:
            self.get_logger().info(f'klatek: {self.frames}', throttle_duration_sec=30.0)

    def check_failed(self):
        if self.failed:
            raise RuntimeError(self.failed)

    def close(self):
        self.running = False


def main(args=None):
    if not opencv_has_gstreamer():
        print('camera: OpenCV bez wsparcia GStreamer (cv2.getBuildInformation: GStreamer NO).\n'
              'Użyj python3-opencv z apt (Ubuntu), nie opencv-python z pip - wersja z pip nie ma GStreamera.',
              file=sys.stderr)
        return 1
    rclpy.init(args=args)
    node = None
    try:
        node = R1Camera()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RuntimeError as exc:
        print(f'camera: {exc}', file=sys.stderr)
        return 1
    finally:
        if node is not None:
            node.close()
            node.destroy_node()
        rclpy.try_shutdown()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
