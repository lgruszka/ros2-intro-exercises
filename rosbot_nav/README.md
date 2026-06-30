# rosbot_nav — autonomia na REALNYM Husarion ROSbot XL (Jazzy)

Pakiet warsztatu **W4**: lidar + 3 tryby autonomii na fizycznym ROSbocie XL (ROS 2 Jazzy).
Symulację tych samych trzech trybów robisz w module **M8** (pakiet `m8_gazebo`) — tam jest pełna
instalacja `rosbot_ros` + Gazebo. **Nie masz robota? Zrób M8, wróć tu po sprzęt.**

## Trzy tryby (te same co w sim, na sprzęcie)

| # | Tryb | Polecenie (po bringupie + lidarze) | Efekt |
|---|------|-------------------------------------|-------|
| **1** | **Mapowanie (teleop)** | `ros2 launch rosbot_nav slam.launch.py` + teleop → `map_saver_cli` | mapa do pliku |
| **2** | **Nawigacja (cele w RViz)** | `ros2 launch rosbot_nav nav.launch.py map:=~/maps/moja_mapa.yaml` | jazda do `/goal_pose` |
| **3** | **Eksploracja (auto)** | `ros2 launch rosbot_nav explore.launch.py` | robot sam mapuje |

Wszystkie domyślnie `use_sim_time:=false` (realny robot = zegar systemowy). Cały stack czyta
**`/scan_filtered`** (box-filter wycina bryłę robota), a **`collision_monitor` jest WŁĄCZONY**
(bezpieczeństwo — robot hamuje przed kolizją; w sim był wyłączony jako obejście artefaktu).

## Różnice względem `m8_gazebo` (sim)

| | `m8_gazebo` (sim, M8) | `rosbot_nav` (real, W4) |
|---|---|---|
| lidar | z Gazebo (`configuration:=autonomy`) | **driver `rplidar_ros`** (`rplidar_s3_launch.py`, osobno) |
| `use_sim_time` | `true` | `false` |
| `collision_monitor` | OFF (obejście self-hitów sim) | **ON** (bezpieczeństwo) |
| skan dla AMCL/costmap/collision_monitor | `/scan` + min_range 0.2 | **`/scan_filtered`** wszędzie |
| MPPI (tryb 2) | 1000/40 (lekkie, CPU sim) | **2000/56** (pełne; Nav2 na laptopie) |
| `slam_rosbot.yaml`, `laser_filter.yaml` | — | **identyczne** z m8_gazebo (trzymaj w sync) |

## Wymagania wstępne (raz)

```bash
# 1) rosbot_ros zbudowany NA ROBOCIE (komputer pokładowy) — patrz M8 / docs Husariona.
# 2) Paczki z apt (na maszynie, gdzie odpalasz SLAM/Nav2):
sudo apt install -y ros-jazzy-slam-toolbox ros-jazzy-nav2-bringup ros-jazzy-nav2-map-server \
                    ros-jazzy-teleop-twist-keyboard ros-jazzy-laser-filters
# 3) Driver lidaru: pakiet rplidar_ros. NIE wrapujemy go — odpalasz wprost (jak bringup).
#    Sprawdź czy jest na robocie (zwykle Husarion go dorzuca, „już skompilowany"):
ros2 pkg prefix rplidar_ros        # jest ścieżka → masz; "Package not found" → zbuduj ze źródeł:
#    git clone -b ros2 https://github.com/Slamtec/rplidar_ros.git ~/ros2_ws/src/rplidar_ros
#    (nowszy driver Slamteca to sllidar_ros2 → wtedy launch sllidar_s3_launch.py). Potem colcon build.
```

## Warstwa 1 — bringup + LIDAR (fundament)

Bringup budzi koła/odometrię/TF, **ale NIE lidar** — to osobne urządzenie USB z osobnym driverem.
Dwa kroki (zwalidowane na żywo na ROSbocie XL):

```bash
# KROK 1 — bringup (na robocie). Czekaj na: "Configured and activated all parsed controllers:
# ['mecanum_drive_controller','imu_broadcaster','joint_state_broadcaster']":
cd ~/ros2_ws && source install/setup.bash
ros2 launch rosbot_bringup rosbot_xl.yaml          # kola, MCU, odometria, TF (BEZ /scan!)

# KROK 2 — driver lidaru RPLIDAR S3 (na robocie). WAŻNE: /dev/ttyUSB1 (USB0 to silniki/MCU!).
# Czekaj na: "RPLidar health status : OK." + "set lidar scan frequency to 10.0 Hz":
ros2 launch rplidar_ros rplidar_s3_launch.py serial_port:=/dev/ttyUSB1
```

Sanity (to MUSI działać, inaczej SLAM nie ruszy):
```bash
ros2 topic hz /scan                                       # ~10 Hz, NIE 0 publisherów
ros2 topic echo /scan --field header.frame_id --once      # powinno być: rplidar_link
ros2 run tf2_ros tf2_echo base_link rplidar_link          # MUSI zwracać transform
```
> **Port:** na ROSbocie XL silniki/MCU siedzą na `/dev/ttyUSB0`, więc lidar to zwykle `/dev/ttyUSB1`
> (sprawdź `ls /dev/serial/by-id/`). Uprawnienia: grupa `dialout` lub `sudo chmod 666 /dev/ttyUSB1`.
> **Frame:** jeśli `/scan` ma frame `laser` zamiast `rplidar_link` (a TF ma `rplidar_link`) → SLAM nie
> dopasuje skanu. Dodaj `frame_id:=rplidar_link` do komendy lidaru, albo `static_transform_publisher`.

## Warstwa 2 = Tryb 1 — Mapowanie

```bash
ros2 launch rosbot_nav slam.launch.py            # box-filter + slam_toolbox (use_sim_time:=false)
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true   # Jazzy: TwistStamped
ros2 run nav2_map_server map_saver_cli -f ~/maps/moja_mapa
```
Podgląd: Foxglove (`foxglove_bridge`, `ws://<ip-robota>:8765`) albo RViz (`/map` Durability **Transient Local**).

## Warstwa 3 = Tryb 2 — Nawigacja po mapie (cele w RViz)

```bash
ros2 launch rosbot_nav nav.launch.py map:=$HOME/maps/moja_mapa.yaml
```
RViz (Fixed Frame `map`): **2D Pose Estimate** (gdzie stoi robot, kierunek strzałki!) → **2D Goal Pose** (cel).

## Warstwa 4 = Tryb 3 — Autonomiczna eksploracja

```bash
# raz: explore_lite ze źródeł (OBA pakiety!)
cd ~/ros2_ws && vcs import src < src/ros2-intro-exercises/rosbot_nav/explore.repos
rosdep install -i --from-path src --rosdistro jazzy -y
colcon build --packages-select explore_lite_msgs explore_lite && source install/setup.bash

# potem (po bringupie + lidarze) JEDNO polecenie składa slam+nav2+explore:
ros2 launch rosbot_nav explore.launch.py
ros2 run nav2_map_server map_saver_cli -f ~/maps/sala1   # gdy zwiedzi
```
Robot sam jeździ do granic znane/nieznane. Działa tylko w **zamkniętej** przestrzeni.

## Sieć i zegary (laptop osobno od robota)

- **Ten sam `ROS_DOMAIN_ID`** na robocie i laptopie (`echo 'export ROS_DOMAIN_ID=10' >> ~/.bashrc`,
  `export ROS_LOCALHOST_ONLY=0`). Rozjechany domain = 0 publisherów mimo działających węzłów.
- **Sync zegarów (chrony/NTP) — krytyczne.** Przy `use_sim_time=false` każda maszyna stempluje TF
  własnym zegarem; rozjechane = „extrapolation into the future". Test: `ros2 run tf2_ros tf2_echo
  map base_link` bez ostrzeżeń.
- **CPU:** odpalaj Nav2/RViz na laptopie (mocniejszym niż komputer pokładowy). „Jedzie i staje" =
  przeciążony CPU → zamknij RViz, ew. zejdź z MPPI 2000/56 → 1000/40 w `nav2_rosbot.yaml`.

## Pliki

| Plik | Tryb | Sedno |
|---|---|---|
| (driver lidaru) | 1,2,3 | **zewnętrzny** `rplidar_ros` → `ros2 launch rplidar_ros rplidar_s3_launch.py serial_port:=/dev/ttyUSB1` (nie nasz pakiet) |
| `config/laser_filter.yaml` | 1,2,3 | box-filter `/scan → /scan_filtered` (= m8_gazebo) |
| `config/slam_rosbot.yaml` | 1,3 | slam_toolbox `base_link`, `/scan_filtered` (= m8_gazebo) |
| `config/nav2_rosbot.yaml` | 2 | Nav2 REAL: collision_monitor ON, `/scan_filtered`, MPPI 2000/56 |
| `config/explore.yaml` | 3 | eksploracja REAL: RPP, collision_monitor ON, `/scan_filtered` |
