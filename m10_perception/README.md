# m10_perception — kamera i obraz w ROS 2 (moduł M10)

Pipeline percepcji bez sprzętu: syntetyczna kamera (`toy_camera`) publikuje obraz
z **zieloną kulą krążącą po okręgu**, a Ty piszesz detektor koloru
(cv_bridge + OpenCV), który znajduje jej środek.

## Wymagania

```bash
sudo apt install -y ros-jazzy-cv-bridge python3-opencv ros-jazzy-rqt-image-view
```

## Szybki start (demo z rozwiązaniem)

```bash
cd ~/ros2_ws && colcon build --symlink-install --packages-select m10_perception
source install/setup.bash
ros2 launch m10_perception toy_pipeline.launch.py
```

W drugim terminalu:

```bash
ros2 topic hz /ball_position          # ~15 Hz
ros2 topic echo /ball_position        # x/y krążą (piksele)
ros2 run rqt_image_view rqt_image_view   # wybierz /image_annotated — czerwone kółko na kuli
```

## Twoje zadanie

Wypełnij 4 TODO w `m10_perception/color_detector_skeleton.py`
(konwersja cv_bridge → HSV+inRange → momenty/centroid → adnotacja):

```bash
ros2 run m10_perception toy_camera            # terminal 1
ros2 run m10_perception color_detector        # terminal 2 — Twój szkielet
```

Sprawdzian: `/ball_position` publikuje ~15 Hz, a x/y zmieniają się sinusoidalnie.

## Stretch

1. Podmień `toy_camera` na **prawdziwą kamerę**: `sudo apt install ros-jazzy-usb-cam`,
   `ros2 run usb_cam usb_cam_node_exe` i przemapuj topic (`--ros-args -r /image_raw:=/image_raw`).
   Dostrajaj HSV_LO/HSV_HI do swojego obiektu (najpierw wydrukuj wartości HSV piksela środka).
2. Publikuj też `/ball_found` (std_msgs/Bool) i loguj utratę kuli.
3. Czerwony obiekt: hue „zawija się" przez 0 — potrzebujesz DWÓCH zakresów i `cv2.bitwise_or`.
