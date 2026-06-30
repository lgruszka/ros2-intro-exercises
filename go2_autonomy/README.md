# go2_autonomy — autonomiczna nawigacja na realnym Unitree Go2

Gotowy stack do **mapowania (SLAM)** i **autonomicznej nawigacji (Nav2 + AMCL)** na
czworonogu **Unitree Go2**, na Ubuntu 24.04 / ROS 2 Jazzy. To materiał do warsztatu
**W5** kursu ROS2 Intro (LucsRobotics) — capstone „od surowego lidaru do robota
jeżdżącego samodzielnie po mapie".

> **Dla kogo:** dla kogoś, kto ma **fizycznego Go2** (większość kursantów ogląda to jako
> live-demo). Cały stos autonomii (slam_toolbox, Nav2, AMCL) to **standardowy ROS 2** —
> ten sam, który znasz z W3 (Webots) i W4 (Husarion). Go2-specyficzny jest tylko *klej*:
> odczyt firmware Unitree, spłaszczenie lidaru 3D do `/scan`, i most `/cmd_vel` → sport API.

> ⚠️ **Ten bundle ma `COLCON_IGNORE`** — colcon pomija go domyślnie, żeby NIE psuł builda
> prostych ćwiczeń `m1`–`m8` (wymaga `unitree_ros2` + msgs Unitree, których one nie mają).
> Żeby go zbudować, patrz „Setup" niżej (vcs import + usuń COLCON_IGNORE).

---

## Co jest w środku

| pakiet | rola |
|---|---|
| `go2_description` | URDF Go2 (slim — sam URDF dla TF; mesh-e opcjonalne, patrz niżej) |
| `go2_bringup` | percepcja (`pointcloud_to_laserscan`), relaye TF/QoS, launche `mapping` + `nav`, configi (Nav2/SLAM/p2l/DDS) |
| `go2_bridge` | most sprzętowy: `/cmd_vel` → **sport API Unitree** (`unitree_cmd_vel_bridge_node`), `lowstate_to_joint_states`, `cmd_vel_arbiter` |
| `go2_msgs` | `srv/SetFreeze` dla arbitra |
| `tools/` | `go2_env.sh`, `go2_scan_calib_gui.py` (strojenie scanu), `go2_amcl_diag_gui.py` (scan-match %), `clean_map.py` |

**Zewnętrzne (vcs/apt):** `unitree_ros2` (SDK firmware + msgs), `nav2`, `slam_toolbox`,
`pointcloud_to_laserscan`.

---

## Prereki

```bash
sudo apt install -y \
  ros-jazzy-slam-toolbox ros-jazzy-navigation2 ros-jazzy-nav2-bringup \
  ros-jazzy-pointcloud-to-laserscan ros-jazzy-rmw-cyclonedds-cpp \
  ros-jazzy-teleop-twist-keyboard python3-vcstool python3-colcon-common-extensions
```
Plus **`unitree_ros2`** — oficjalny SDK Unitree (most firmware + msgs). Buduje się wg
**jego README** (osobny `cyclonedds_ws` + source env): https://github.com/unitreerobotics/unitree_ros2

## Setup

```bash
# 1. workspace + klon ćwiczeń
mkdir -p ~/go2_ws/src && cd ~/go2_ws/src
git clone https://github.com/lgruszka/ros2-intro-exercises.git

# 2. zewnętrzne zależności (unitree_ros2) do src/
cd ~/go2_ws
vcs import src < src/ros2-intro-exercises/go2_autonomy/go2_deps.repos

# 3. odblokuj bundle (domyślnie COLCON_IGNORE)
rm src/ros2-intro-exercises/go2_autonomy/COLCON_IGNORE

# 4. zależności + build
rosdep install -i --from-path src --rosdistro jazzy -y
colcon build --symlink-install
source install/setup.bash
```
> Jeśli `unitree_ros2` wymaga osobnego builda/env (cyclonedds_ws) — zrób to wg jego README
> **przed** krokiem 4. `go2_bridge` zależy od msgs `unitree_api`/`unitree_go`/`unitree_hg`.

## Sieć / DDS

Robot łączy się przez Ethernet (host `192.168.123.x/24`, robot `…161`/`…18`). Ustaw interfejs
w `go2_bringup/config/cyclonedds_go2.xml` (`ip -br addr` → np. `enxXXXX`). Potem w każdym terminalu:
```bash
source tools/go2_env.sh        # ws + CycloneDDS + restart daemona DDS
ros2 topic hz /utlidar/cloud_base --qos-profile sensor_data   # ~15 Hz = robot gada
```

---

## 1) Mapowanie (SLAM)

```bash
ros2 launch go2_bringup mapping.launch.py
# Jeźdź PILOTEM (RC) wolno po całej sali, WRÓĆ w okolicę startu (loop closure).
# RViz wstaje sam (Fixed Frame=map). Gdy mapa gotowa:
ros2 run nav2_map_server map_saver_cli -f ~/maps/sala1     # → sala1.yaml + sala1.pgm
```

## 2) Nawigacja (Nav2 + AMCL)

```bash
ros2 launch go2_bringup nav.launch.py map:=$HOME/maps/sala1.yaml
```
W RViz/Foxglove:
1. **2D Pose Estimate** — KIERUNEK strzałki krytyczny (błąd ~90° = scan się rozjeżdża).
2. **Przejedź ~1 m** — AMCL konwerguje w ruchu.
3. **Nav2 Goal** — robot fizycznie pojedzie. Miej **E-Stop (pilot RC)** pod ręką.

> Gdy `Move` odbija **code 3202** (robot nie w trybie chodu, np. po jeździe pilotem):
> `nav.launch.py … switch_to_normal:=true` (robot WSTANIE na starcie).

---

## Pułapki Go2 (skrót — pełne omówienie w W5)

- **`/utlidar/cloud_base`, nie `/utlidar/cloud`** — firmware daje chmurę już w `base_link`
  (zna montaż lidaru), bez ręcznej kalibracji rotacji.
- **QoS:** lidar publikuje `BEST_EFFORT` → `ros2 topic echo … --qos-profile sensor_data`.
  slam_toolbox chce `RELIABLE` → `scan_qos_relay` robi `/scan` → `/scan_reliable`.
- **slam_toolbox na Jazzy = lifecycle** → `lifecycle_manager` z autostart (już w launchu).
- **`base_frame: base_link`** (Go2 ma base_link, nie base_footprint).
- **Most ruchu:** Go2 sport API chce `{x,y,z}` → zły format = `3202` na każdy Move.
- **floor ≠ regulator obrotu:** min-velocity floor kompensuje deadband; za wysoki = oscylacja.

## Strojenie / diagnostyka (tools)

```bash
python3 tools/go2_scan_calib_gui.py    # pas wysokości scanu na żywo (ściany, nie podłoga)
python3 tools/go2_amcl_diag_gui.py     # scan-match % — czy AMCL trzyma lokalizację
./tools/clean_map.py ~/maps/sala1.yaml # usuń szum z mapy
```

## Notatki / ograniczenia

- **Mesh-e robota:** vendored `go2_description` ma sam URDF (TF/nav działają). Model w RViz
  (bryła) → odkomentuj `unitree_ros` w `go2_deps.repos` (patrz tam) lub dociągnij upstream.
- Stack zwalidowany na realnym Go2 przez autora; tu jest **wycięty z większego projektu**
  (usunięto LIO oraz warstwę kurierską: dokowanie/misja/ramię). Pełen build potwierdź u siebie
  z `unitree_ros2`.
- `use_sim_time:=false` wszędzie (realny robot, zegar systemowy — pilnuj NTP).
