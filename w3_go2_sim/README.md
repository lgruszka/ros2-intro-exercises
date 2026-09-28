# w3_go2_sim - Unitree Go2 w Gazebo: SLAM, mapa i Nav2

Wariant warsztatu W3 z robotem kroczącym. Zamiast kołowego TurtleBota uruchamiasz
w Gazebo Harmonic czworonoga **Unitree Go2**, budujesz mapę sali przez SLAM
(slam_toolbox), zapisujesz ją, a potem wysyłasz robota do celów przez Nav2 z AMCL.

Robotem porusza kontroler chodu **CHAMP** z repo
[khaledgabr77/unitree_go2_ros2](https://github.com/khaledgabr77/unitree_go2_ros2).
Ten pakiet dokłada to, czego w tamtym repo brakuje do nawigacji: salę ze ścianami,
konwersję chmury 3D na 2D `/scan`, launch SLAM, launch Nav2 i parametry Nav2 dla Go2.

## Wymagania

- Ubuntu 24.04 + ROS 2 Jazzy, komputer x86_64 (amd64).
- Minimum: 4 rdzenie, 8 GB RAM. Zalecane: 8 rdzeni, 16 GB RAM.
  Karta graficzna nie jest wymagana, ale z nią Gazebo i RViz działają płynniej.
- Około 6 GB wolnego miejsca na pakiety ROS 2 i Gazebo.

## Instalacja (jednorazowo)

```bash
# ROS 2 Jazzy (jeśli jeszcze go nie masz) - instrukcja: docs.ros.org/en/jazzy/Installation
# Gazebo Harmonic + Nav2 + slam_toolbox + zależności symulacji Go2:
sudo apt update
sudo apt install -y ros-jazzy-desktop ros-jazzy-ros-gz \
  ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-slam-toolbox \
  ros-jazzy-pointcloud-to-laserscan ros-jazzy-teleop-twist-keyboard \
  ros-jazzy-gz-ros2-control ros-jazzy-ros2-control ros-jazzy-ros2-controllers \
  ros-jazzy-robot-localization ros-jazzy-xacro \
  ros-jazzy-velodyne ros-jazzy-velodyne-description \
  python3-colcon-common-extensions python3-rosdep
sudo rosdep init   # jeśli pokaże „already initialized” - to w porządku
rosdep update
```

## Budowanie

```bash
source /opt/ros/jazzy/setup.bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone https://github.com/khaledgabr77/unitree_go2_ros2.git
git clone https://github.com/lgruszka/ros2-intro-exercises.git   # jeśli jeszcze go nie masz
cd ~/ros2_ws
# --skip-keys: literówka w repo Go2 (zależność "unitree_applications", pakiet nazywa się unitree_application)
rosdep install -i -y --rosdistro jazzy \
  --from-paths src/unitree_go2_ros2 src/ros2-intro-exercises/w3_go2_sim \
  --skip-keys unitree_applications
# budujemy tylko Go2 + ten pakiet (reszta repo ćwiczeń ma inne zależności)
colcon build --symlink-install \
  --base-paths src/unitree_go2_ros2 src/ros2-intro-exercises/w3_go2_sim
source install/setup.bash
```

W każdym nowym terminalu: `source ~/ros2_ws/install/setup.bash`.

## Krok 1 - SLAM: budujesz mapę

```bash
# Terminal 1 - symulacja (Gazebo + Go2 + CHAMP). Poczekaj ok. 20-30 s, aż robot wstanie.
ros2 launch w3_go2_sim go2_sim.launch.py
# Terminal 2 - SLAM
ros2 launch w3_go2_sim slam.launch.py
# Terminal 3 - RViz (mapa, skan, robot)
rviz2 -d $(ros2 pkg prefix w3_go2_sim)/share/w3_go2_sim/rviz/go2_nav.rviz
# Terminal 4 - sterowanie z klawiatury (i/j/l/, - ruch; k - stop; Shift+J/L - krok w bok)
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Przejdź robotem całą salę, powoli, z przystankami w narożnikach. Go2 w symulacji
chodzi maksymalnie 0,3 m/s - nie podkręcaj prędkości w teleop powyżej `speed 0.3`.
Końce ścianek działowych i narożniki klocków omijaj z zapasem ok. 0,5 m: Go2, który zahaczy
o nie nogą, potrafi się przewrócić. Wtedy zamknij wszystko (także SLAM - sam restart symulacji
rozjechałby mapę) i zacznij krok 1 od nowa. Czy robot stoi, sprawdzisz poleceniem
`ros2 topic echo --once /odom/ground_truth --field pose.pose.position.z` (ok. 0,24 = stoi,
ok. 0,1 = leży).

## Krok 2 - zapis mapy

```bash
mkdir -p ~/maps
ros2 run nav2_map_server map_saver_cli -f ~/maps/go2_room
```

Powstają dwa pliki: `go2_room.pgm` (obraz) i `go2_room.yaml` (rozdzielczość, początek układu).
Potem zamknij wszystkie terminale (Ctrl+C) i sprawdź, że `pgrep -af "gz sim"` nic nie wypisuje
(jeśli wypisuje: `pkill -9 -f "gz sim"`). Nowa symulacja uruchomiona obok zamykającej się starej
potrafi zgubić robota.

## Krok 3 - Nav2 z AMCL na mapie

```bash
# Terminal 1 - symulacja od nowa (robot znów stoi w punkcie startu mapy)
ros2 launch w3_go2_sim go2_sim.launch.py
# Terminal 2 - Nav2 + AMCL + mapa (po ok. 30 s, gdy robot już stoi)
ros2 launch w3_go2_sim nav.launch.py map:=$HOME/maps/go2_room.yaml
# Terminal 3 - RViz
rviz2 -d $(ros2 pkg prefix w3_go2_sim)/share/w3_go2_sim/rviz/go2_nav.rviz
```

Zanim wyślesz cel, sprawdź w Gazebo, że Go2 stoi na czterech nogach. Jeśli leży na grzbiecie
(zdarza się sporadycznie przy przeciążonym komputerze), zrestartuj symulację i Nav2.

AMCL startuje z pozy (0, 0, 0), czyli z miejsca startu robota. Cel wyślesz:

- w RViz narzędziem **Nav2 Goal** (kliknij i przeciągnij w stronę, w którą robot ma patrzeć),
- z terminala:

```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: 2.0, y: -1.5}, orientation: {w: 1.0}}}}"
```

- albo trzy cele po kolei: `ros2 run w3_go2_sim send_goals`

## Co jest w środku

| Plik | Co robi |
|---|---|
| `launch/go2_sim.launch.py` | Gazebo + Go2 (tylko lidar Velodyne) + CHAMP + EKF + `pointcloud_to_laserscan`. Bez statycznego `map -> odom` z oryginalnego launcha (kłóci się z SLAM i AMCL). Argumenty: `gui:=false`, `rviz:=true`. |
| `launch/slam.launch.py` | slam_toolbox (online_async) z `params/slam.yaml` |
| `launch/nav.launch.py` | stockowy `nav2_bringup/bringup_launch.py` z mapą i `params/nav2_go2_sim.yaml` |
| `params/pointcloud_to_laserscan.yaml` | chmura 3D -> 2D `/scan` (pas wysokości 0,15-1,0 m nad podłogą) |
| `params/nav2_go2_sim.yaml` | Nav2 dla Go2: AMCL Omni, RotationShim + Regulated Pure Pursuit, footprint Go2, limity chodu CHAMP |
| `worlds/go2_room.sdf` | sala 12 x 10 m ze ścianami i przeszkodami |
| `w3_go2_sim/send_goals.py` | wysyła kolejne cele przez `nav2_simple_commander` i wypisuje wynik |

Ważne fakty o tej symulacji:

- odometria: topic `/odom` (EKF CHAMP-a), drzewo TF `map -> odom -> base_footprint -> base_link -> velodyne`,
- `/cmd_vel` to `geometry_msgs/Twist` (Nav2 Jazzy domyślnie też publikuje Twist),
- wszystkie nodes (węzły) używają `use_sim_time: true` (zegar `/clock` z Gazebo).
