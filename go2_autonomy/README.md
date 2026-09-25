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
  ros-jazzy-teleop-twist-keyboard python3-vcstool python3-colcon-common-extensions \
  ros-jazzy-rosidl-generator-dds-idl python3-pyqt6
```
- `ros-jazzy-rosidl-generator-dds-idl` — wymaga go `unitree_ros2`, a rosdep nie zainstaluje go sam
  (bez niego build `unitree_api`/`unitree_go` pada).
- `python3-pyqt6` — dla narzędzi GUI z `tools/`. Instaluj z apt, nie przez `pip` (Ubuntu 24.04
  blokuje systemowy `pip install`, PEP 668).
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

# 4. zależności + build (tylko pakiety potrzebne Go2 — pełny build ciągnie też
#    przykłady G1/H1/B2 z unitree_ros2 i na słabszej maszynie potrafi zabraknąć RAM)
rosdep install -i --from-path src --rosdistro jazzy -y
colcon build --symlink-install --packages-up-to go2_bringup go2_bridge
source install/setup.bash
```
> Jeśli `unitree_ros2` wymaga osobnego builda/env (cyclonedds_ws) — zrób to wg jego README
> **przed** krokiem 4. `go2_bridge` zależy od msgs `unitree_api`/`unitree_go`/`unitree_hg`.

## Sieć / DDS

Robot łączy się przez Ethernet (host `192.168.123.x/24`, robot `…161`/`…18`). Raz na sesję nadaj
interfejsowi adres w sieci robota i wpisz ten sam interfejs w `go2_bringup/config/cyclonedds_go2.xml`
(domyślnie stoi tam `enp2s0`):
```bash
ip -br addr                                          # znajdź interfejs Ethernet (np. enxXXXX)
sudo ip addr add 192.168.123.99/24 dev <iface>       # tymczasowo, do restartu
cd ~/go2_ws/src/ros2-intro-exercises/go2_autonomy
sed -i 's/<NetworkInterface name="[^"]*"/<NetworkInterface name="<iface>"/' \
    go2_bringup/config/cyclonedds_go2.xml
```
Potem w **każdym** terminalu (ścieżki `tools/…` są względne — wołaj je z katalogu `go2_autonomy`):
```bash
cd ~/go2_ws/src/ros2-intro-exercises/go2_autonomy
source tools/go2_env.sh        # ws + CycloneDDS + restart daemona DDS
ros2 topic hz /utlidar/cloud_base   # ~15 Hz = robot gada (topic hz sam dopasowuje QoS)
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
> **Zanim robot ruszy:** most NIE stawia robota — postaw go pilotem, zanim uruchomisz launch.
> Jedna osoba trzyma pilota i cały czas patrzy na robota, strefa 1,5–2 m wokół trasy jest wolna,
> pierwsze cele blisko i wolno (prędkości obniżysz w `nav2_params.yaml`, `safety.yaml`
> i parametrach mostu w `nav.launch.py` — szczegóły w W6, sekcja 7). Programowy stop:
> ```bash
> ros2 topic pub --once /emergency_stop/active std_msgs/msg/Bool "{data: true}"    # stop
> ros2 topic pub --once /emergency_stop/active std_msgs/msg/Bool "{data: false}"   # zwolnij
> ```
> Najpierw zatrzymaj robota, dopiero potem zamykaj procesy (Ctrl+C na moście wysyła StopMove,
> ale zabity proces nie wyśle już nic).

W RViz/Foxglove:
1. **Poza startowa** — AMCL sam startuje z (0, 0, 0), czyli z miejsca startu mapowania. Jeśli robot
   stoi gdzie indziej, popraw ją przez **2D Pose Estimate** — KIERUNEK strzałki krytyczny
   (błąd ~90° = scan się rozjeżdża).
2. **Przejedź ~1 m** — AMCL konwerguje w ruchu.
3. **Nav2 Goal** — robot fizycznie pojedzie. Miej **pilota RC** w ręku.

> Gdy `Move` odbija **code 3202**, firmware odrzucił komendę — najczęściej przez zły format
> parametrów (sport API chce `{x,y,z}`), nie przez tryb robota. Robot, który nie stoi w trybie
> chodu, objawia się inaczej: Move zwraca `code 0`, a robot stoi — wtedy postaw go pilotem.

---

## Pułapki Go2 (skrót — pełne omówienie w W5)

- **`/utlidar/cloud_base`, nie `/utlidar/cloud`** — firmware daje chmurę już w `base_link`
  (zna montaż lidaru), bez ręcznej kalibracji rotacji.
- **QoS:** lidar i `/scan` publikują `BEST_EFFORT`. Twój węzeł subskrybujący `RELIABLE` (domyślny
  QoS) nic nie dostanie, a w logu pojawi się WARN „offering incompatible QoS” — subskrybuj profilem
  `sensor_data`. `ros2 topic echo`/`hz` na Jazzy same dopasowują QoS, więc to, że widzisz dane
  w terminalu, nie dowodzi, że dostanie je Twój węzeł.
- **slam_toolbox na Jazzy = lifecycle** → `lifecycle_manager` z autostart (już w launchu).
- **`base_frame: base_link`** (Go2 ma base_link, nie base_footprint).
- **Most ruchu:** Go2 sport API chce `{x,y,z}` → zły format = `3202` na każdy Move.
- **`collision_monitor` jest wyłączony** — przed przeszkodami chronią robota tylko costmapy
  i controller. Jeździj wolno i z pilotem w ręku (jak go włączyć: komentarz w `nav2_params.yaml`).
- **floor ≠ regulator obrotu:** min-velocity floor kompensuje deadband; za wysoki = oscylacja.

## Strojenie / diagnostyka (tools)

```bash
# z katalogu go2_autonomy, po source tools/go2_env.sh (GUI wymagają python3-pyqt6)
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
