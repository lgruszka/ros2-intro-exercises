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
| MPPI (tryb 2) | 1000/40 | 1000/40 (+ `transform_tolerance` 0.3 na WiFi) |
| wariant RPP (tryb 2) | — | `nav.launch.py controller:=rpp` |
| `slam_rosbot.yaml`, `laser_filter.yaml` | — | **identyczne** z m8_gazebo (trzymaj w sync) |

## Wymagania wstępne (raz)

Bringup i driver lidaru działają **na robocie** (komputer pokładowy). SLAM, Nav2, filtr lasera i RViz
uruchamiasz **na laptopie** — to on buduje pakiet `rosbot_nav`.

```bash
# 1) [ROBOT] rosbot_ros zbudowany na komputerze pokładowym — patrz M8 / docs Husariona.

# 2) [LAPTOP] paczki z apt:
sudo apt install -y ros-jazzy-slam-toolbox ros-jazzy-nav2-bringup ros-jazzy-nav2-map-server \
                    ros-jazzy-teleop-twist-keyboard ros-jazzy-laser-filters

# 3) [LAPTOP] zbuduj ten pakiet (repo ćwiczeń sklonowane do ~/ros2_ws/src):
cd ~/ros2_ws && colcon build --symlink-install --packages-select rosbot_nav
source install/setup.bash
ros2 pkg prefix rosbot_nav         # wypisuje ścieżkę = pakiet gotowy

# 4) [ROBOT] driver lidaru: pakiet rplidar_ros. NIE wrapujemy go — odpalasz wprost (jak bringup).
#    Samo `ros2 pkg prefix rplidar_ros` nie wystarczy: paczka ros-jazzy-rplidar-ros z apt
#    NIE MA launcha rplidar_s3_launch.py. Sprawdź, czy launch dla S3 istnieje:
ros2 launch rplidar_ros rplidar_s3_launch.py --show-args
#    „file not found" / „package not found" → zbuduj driver ze źródeł (gałąź ros2):
git clone -b ros2 https://github.com/Slamtec/rplidar_ros.git ~/ros2_ws/src/rplidar_ros
cd ~/ros2_ws && colcon build --symlink-install --packages-select rplidar_ros
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
ros2 launch rplidar_ros rplidar_s3_launch.py serial_port:=/dev/ttyUSB1 frame_id:=rplidar_link
```

`frame_id:=rplidar_link` jest obowiązkowe: driver domyślnie podpisuje skan ramką `laser`, której nie ma
w drzewie TF ROSbota, a wtedy SLAM nie dopasuje skanu.

Sanity (to MUSI działać, inaczej SLAM nie ruszy):
```bash
ros2 topic hz /scan                                       # ~10 Hz, NIE 0 publisherów
ros2 topic echo /scan --field header.frame_id --once      # powinno być: rplidar_link
ros2 run tf2_ros tf2_echo base_link rplidar_link          # MUSI zwracać transform
```
> **Port:** na ROSbocie XL silniki/MCU siedzą na `/dev/ttyUSB0`, więc lidar to zwykle `/dev/ttyUSB1`
> (sprawdź `ls /dev/serial/by-id/`). Uprawnienia: grupa `dialout` lub `sudo chmod 666 /dev/ttyUSB1`.
> **Frame:** jeśli `/scan` ma frame `laser` zamiast `rplidar_link`, to w komendzie lidaru zabrakło
> `frame_id:=rplidar_link`.

## Warstwa 2 = Tryb 1 — Mapowanie

```bash
ros2 launch rosbot_nav slam.launch.py            # box-filter + slam_toolbox (use_sim_time:=false)
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true   # Jazzy: TwistStamped
ros2 run nav2_map_server map_saver_cli -f ~/maps/moja_mapa
```
Podgląd: RViz na laptopie (Fixed Frame `map`, `/map` z Durability **Transient Local**, `/scan`, TF).
Foxglove jest opcjonalny (`foxglove_bridge` na robocie, `ws://<ip-robota>:8765`).

## Warstwa 3 = Tryb 2 — Nawigacja po mapie (cele w RViz)

```bash
ros2 launch rosbot_nav nav.launch.py map:=$HOME/maps/moja_mapa.yaml                   # MPPI (domyślnie)
ros2 launch rosbot_nav nav.launch.py map:=$HOME/maps/moja_mapa.yaml controller:=rpp   # wariant RPP
rviz2                                                                                 # osobny terminal
```
RViz (Fixed Frame `map`): **2D Pose Estimate** (gdzie stoi robot, kierunek strzałki!) → **2D Goal Pose** (cel).

- **Pozycję startową zaznacz w ~60 s** od startu. Inaczej `global_costmap` nie doczeka się ramki `map`
  i nawigacja nie wstanie („Failed to bring up all requested nodes. Aborting bringup") → Ctrl+C, od nowa.
- **Jeden Nav2 na domenę (`ROS_DOMAIN_ID`).** Nie odpalaj drugiego `nav.launch.py` „żeby mieć mapę w RViz" — mapa pojawi się
  sama, a dwa Nav2 o tych samych nazwach ładują sobie węzły i cele padają („unknown goal response",
  „Goal failed"). `nav.launch.py` sam to blokuje (sprawdza `/bt_navigator` w Twojej domenie; obejście `allow_duplicate:=true`).
  Nav2 sąsiedniej pary w innej domenie Ci nie przeszkadza.
- **MPPI czy RPP?** MPPI (domyślny) sam omija przeszkody — wygina tor na lokalnej costmapie. RPP jedzie
  prosto po ścieżce z planera z zadaną prędkością i przed przeszkodą **staje** (objazd tylko przez replan).

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

- **Ten sam `ROS_DOMAIN_ID` na robocie i laptopie — numer Twojej pary** (przydziela go instruktor, np. numer
  robota). Gdyby wszystkie pary zostały w domenie 0, teleop jednego kursanta sterowałby wszystkimi robotami,
  a drugi zespół nie uruchomiłby Nav2. Rozjechany numer domeny = 0 publisherów mimo działających węzłów.

  ```bash
  # [ROBOT] i [LAPTOP] - ten sam numer dla Twojej pary (przykład: robot nr 3):
  echo 'export ROS_DOMAIN_ID=3' >> ~/.bashrc && source ~/.bashrc
  # discovery nie może być ograniczone do localhost - ta komenda nie powinna nic wypisać
  # (albo tylko ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET, domyślne w Jazzy):
  printenv | grep -E 'ROS_LOCALHOST_ONLY=1|ROS_AUTOMATIC_DISCOVERY_RANGE'
  ```
- **Zegary (chrony/NTP):** przy `use_sim_time=false` każda maszyna stempluje TF własnym zegarem — trzymaj
  chrony na obu (najprościej: laptop bierze czas z robota). Sprawdzenie: `chronyc tracking` (System time
  rzędu ms = OK).
- **„extrapolation into the future" przy zsynchronizowanych zegarach = WiFi, nie zegar.** Dane z robota
  (TF, odometria, skan) idą przez WiFi do laptopa z Nav2; na 2.4 GHz widzieliśmy piki 0.3–0.8 s (tolerancje
  Nav2 to 0.1–0.3 s) → błędy TF, `collision_monitor` „Robot to stop due to invalid source", „Goal failed".
  Leczenie: **WiFi 5 GHz** + wyłączone oszczędzanie energii na robocie
  (`sudo nmcli connection modify <sieć> 802-11-wireless.powersave 2`). Diagnoza: `ping <robot>` (piki
  >100 ms?) i `ros2 topic delay /odometry/filtered` na laptopie. **`chronyc makestep` i restarty robota
  tego nie naprawią** (każdy skok zegara dodatkowo czyści bufor TF).
- **CPU:** odpalaj Nav2/RViz na laptopie (mocniejszym niż komputer pokładowy). „Jedzie i staje" przy
  dobrym WiFi = przeciążony CPU (`Control loop missed its desired rate`) → zamknij RViz.

## Najczęstsze problemy (realny ROSbot XL)

| Objaw | Przyczyna | Co zrobić |
|---|---|---|
| MPPI jedzie ≤ 0.3 m/s, `vx_max` nic nie zmienia | brak `odom_topic` w **`controller_server`** → Nav2 czyta pusty `odom`, MPPI widzi prędkość 0 | `controller_server: odom_topic: /odometry/filtered` (jest w naszym configu) + **restart Nav2** |
| robot nie przekracza 0.5 m/s mimo wyższego `vx_max` | `velocity_smoother` obcina każde polecenie do swojego `max_velocity` (pierwsza wartość = vx) | podnieś oba: `ros2 param set /controller_server FollowPath.vx_max 0.8` i `ros2 param set /velocity_smoother max_velocity "[0.8, 0.0, 2.0]"` |
| staje przy starcie / obrocie: „Robot to approach", „Failed to make progress" | lidar widzi antenę/maszt **wewnątrz** obrysu (filtr ich nie wyciął) | poszerz pudełko w `laser_filter.yaml` (`min_x`); sprawdź, czy w `/scan_filtered` nie ma punktów w promieniu `robot_radius` |
| „extrapolation into the future", przerwane cele | opóźnienia WiFi (patrz wyżej) | 5 GHz, powersave off |
| „unknown goal response", „Action server is inactive. Rejecting the goal" | dwa Nav2 naraz w tej samej domenie | jeden `nav.launch.py`, do podglądu samo `rviz2` |
| „Aborting bringup" zaraz po starcie | brak pozycji startowej w ~60 s | 2D Pose Estimate szybciej, restart launcha |

## Pliki

| Plik | Tryb | Sedno |
|---|---|---|
| (driver lidaru) | 1,2,3 | **zewnętrzny** `rplidar_ros` → `ros2 launch rplidar_ros rplidar_s3_launch.py serial_port:=/dev/ttyUSB1 frame_id:=rplidar_link` (nie nasz pakiet) |
| `config/laser_filter.yaml` | 1,2,3 | box-filter `/scan → /scan_filtered` (= m8_gazebo) |
| `config/slam_rosbot.yaml` | 1,3 | slam_toolbox `base_link`, `/scan_filtered` (= m8_gazebo) |
| `config/nav2_rosbot.yaml` | 2 | Nav2 REAL: collision_monitor ON, `/scan_filtered`, MPPI 1000/40, `odom_topic` w controller_server |
| `config/nav2_rosbot_rpp.yaml` | 2 | to samo z RPP zamiast MPPI (`controller:=rpp`) — różni się tylko blokiem FollowPath |
| `config/explore.yaml` | 3 | eksploracja REAL: RPP, collision_monitor ON, `/scan_filtered` |
