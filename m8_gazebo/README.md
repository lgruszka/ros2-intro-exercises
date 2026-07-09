# m8_gazebo — ROSbot XL w Gazebo: mapowanie, nawigacja, eksploracja (Jazzy)

Gotowe configi + launche do prowadzenia ROSbota XL (Husarion) na **ROS 2 Jazzy** — w Gazebo
Harmonic na własnym komputerze **oraz na realnym robocie**. Uzupełnienie modułu **M8** i warsztatu
**W4**. Wszystko chodzi natywnie (bez playgroundu).

## Trzy tryby

Ten sam zestaw plików daje trzy tryby pracy. Sim ↔ realny robot różni się **tylko** flagą
`use_sim_time` (`true` w Gazebo, `false` na sprzęcie) plus bringupem realnego robota.

| # | Tryb | Polecenie (po starcie symulacji / bringupu) | Efekt |
|---|------|----------------------------------------------|-------|
| **1** | **Mapowanie (teleop)** | `ros2 launch m8_gazebo slam.launch.py use_sim_time:=true` + teleop → `map_saver_cli` | budujesz mapę ręcznie, zapisujesz do pliku |
| **2** | **Nawigacja (cele w RViz)** | `ros2 launch m8_gazebo nav.launch.py map:=~/maps/moja_mapa.yaml` | jeździsz do punktów klikanych w RViz2 (2D Goal Pose) |
| **3** | **Eksploracja (auto)** | `ros2 launch m8_gazebo explore.launch.py use_sim_time:=true` | robot sam mapuje zamkniętą przestrzeń |

> **Dlaczego SLAM czyta `/scan_filtered`, nie `/scan`:** lidar ROSbota XL — **także w Gazebo** —
> widzi własną konstrukcję ~5 cm (~100 pkt @ 0.066–0.2 m). Na surowym `/scan` SLAM wrysowuje je
> jako pierścień przeszkód wokół robota → komórka startowa „lethal" → planner nie ma jak
> wystartować → **robot kręci się w kółko**. Dlatego `slam.launch.py` (i `explore.launch.py`)
> odpala box-filter `/scan → /scan_filtered`. To NIE jest problem tylko realnego robota.

## Wymagania wstępne

1. Zbudowany `rosbot_ros` (klon + vcs + colcon — patrz moduł M8, sekcja 3).
2. Paczki z apt:
   ```bash
   sudo apt install -y ros-jazzy-slam-toolbox ros-jazzy-nav2-bringup ros-jazzy-nav2-map-server \
                       ros-jazzy-teleop-twist-keyboard ros-jazzy-laser-filters
   ```
3. Build tej paczki:
   ```bash
   cd ~/ros2_ws        # tam gdzie masz src/ z ćwiczeniami
   colcon build --symlink-install --packages-select m8_gazebo
   source install/setup.bash
   ```

Symulację (wspólna dla wszystkich trybów) ZAWSZE odpalaj z `configuration:=autonomy` — bez tego
ROSbot **nie ma lidaru**, `/scan` ma 0 publisherów i nic nie zadziała:
```bash
ros2 launch rosbot_gazebo simulation.yaml robot_model:=rosbot_xl configuration:=autonomy
```

---

## Tryb 1 — Mapowanie (teleop)

```bash
# 1) (osobny terminal) symulacja Z LIDAREM
ros2 launch rosbot_gazebo simulation.yaml robot_model:=rosbot_xl configuration:=autonomy

# 2) SLAM (box-filter + slam_toolbox; base_frame=base_link, scan_topic=/scan_filtered)
ros2 launch m8_gazebo slam.launch.py use_sim_time:=true

# 3) Jeźdź, żeby budować mapę  (Jazzy: stamped:=true KONIECZNE — /cmd_vel to TwistStamped)
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true

# 4) Zapisz mapę (powstaną moja_mapa.pgm + moja_mapa.yaml)
mkdir -p ~/maps
ros2 run nav2_map_server map_saver_cli -f ~/maps/moja_mapa
```

Sanity-check (drugi terminal) — to MUSI zwracać transform, nie „frame does not exist":
```bash
ros2 run tf2_ros tf2_echo map odom
ros2 topic hz /map
ros2 topic hz /scan_filtered     # filtr żyje? (mniej punktów niż /scan)
```

**Podgląd w RViz** (`rviz2 --ros-args -p use_sim_time:=true` — RViz na zegarze symulacji!):
- *Global Options → Fixed Frame* = `map` (albo `odom`, zanim slam ruszy).
- *Add → By topic → `/map` → Map*; jeśli mapa się nie rysuje → panel Map → *Durability Policy →
  Transient Local* (mapa jest „zatrzaśnięta"/latched).
- *Add → By topic → `/scan_filtered` → LaserScan*, Style → `Points`.

Jeźdź powoli, trzymaj ściany w polu lidaru, **obejdź pomieszczenie i wróć do startu** — zamknięcie
pętli (loop closure) zlepi mapę w spójną całość.

---

## Tryb 2 — Nawigacja po zapisanej mapie (cele w RViz)

```bash
# 1) (osobny terminal) symulacja
ros2 launch rosbot_gazebo simulation.yaml robot_model:=rosbot_xl configuration:=autonomy

# 2) Nav2 na zapisanej mapie (map_server + AMCL + planner + controller + lifecycle)
ros2 launch m8_gazebo nav.launch.py map:=$HOME/maps/moja_mapa.yaml use_sim_time:=true
```

W RViz (`rviz2 --ros-args -p use_sim_time:=true`), *Fixed Frame* = `map`:
1. **2D Pose Estimate** → kliknij gdzie stoi robot i przeciągnij w kierunku patrzenia (kierunek
   strzałki krytyczny). Publikuje `/initialpose`, AMCL się lokalizuje.
2. **2D Goal Pose** → kliknij cel (publikuje `/goal_pose`). Robot pojedzie.

Dodaj panele: Map (`/map`, Durability **Transient Local**), Path (`/plan`), LaserScan (`/scan`).

> Sam stockowy `nav2_bringup` **NIE zlokalizuje ROSbota** — jego AMCL ma `base_frame_id:
> base_footprint`, a ROSbot ma `base_link`. Nasz `nav2_rosbot.yaml` to naprawia (+ `enable_stamped_cmd_vel`,
> `obstacle_min_range 0.2`, MPPI). Ten config jest zweryfikowany na żywo — nie ruszaj go bez powodu.

---

## Tryb 3 — Autonomiczna eksploracja (robot mapuje się sam)

`explore_lite` (frontier-based): robot sam jeździ do granic znane/nieznane i mapuje, aż zwiedzi
**zamkniętą** przestrzeń. Jeden launch składa cały stos (SLAM + Nav2 + explore) — wystarczą **2 terminale**.

**Jednorazowo** dociągnij `explore_lite` ze źródeł (NIE ma go w apt):
```bash
cd ~/ros2_ws && vcs import src < src/ros2-intro-exercises/m8_gazebo/explore.repos
rosdep install -i --from-path src --rosdistro jazzy -y
colcon build --packages-select explore_lite_msgs explore_lite && source install/setup.bash
```
> `explore_lite` zależy od własnych komunikatów `explore_lite_msgs` — buduj **oba** (sama
> `explore_lite` rzuci „package not found").

Potem za każdym razem (2 terminale):
```bash
# T1 — symulacja
ros2 launch rosbot_gazebo simulation.yaml robot_model:=rosbot_xl configuration:=autonomy

# T2 — cały stos eksploracji (slam + nav2 + explore)
ros2 launch m8_gazebo explore.launch.py use_sim_time:=true

# gdy robot zwiedzi pomieszczenie — zapisz mapę:
ros2 run nav2_map_server map_saver_cli -f ~/maps/sala1
```

> **Config eksploracji = `config/explore.yaml`** (a NIE `nav2_rosbot.yaml`). To **pełny, zwalidowany
> na żywo** plik params (port z tutoriala 10 Husariona / `tutorial_pkg`, dostosowany do Jazzy):
> controller **RegulatedPurePursuit** + komplet sekcji Nav2 + `explore_node` + `collision_monitor` +
> `docking_server`, costmapy na `/scan_filtered`. `explore.launch.py` podaje go i do `navigation_launch.py`,
> i do węzła explore_lite. (Tryb 2 — nawigacja po mapie — używa `nav2_rosbot.yaml` z MPPI; to świadomie
> dwa controllery: lekki RPP do eksploracji, MPPI do jazdy po gotowej mapie — jak w tutorialu Husariona.)

> **Gotcha Jazzy:** stockowy `navigation_launch.py` na Jazzy startuje WIĘCEJ węzłów niż na Humble
> (`collision_monitor`, `docking_server`, `route_server`). Każdy wymaga swojej sekcji w params —
> brak → bringup pada („observation_sources is not initialized" / „Charging dock plugins not given").
> `explore.yaml` (i `nav2_rosbot.yaml`) mają już te sekcje, dlatego stack wstaje za pierwszym razem.

---

## Realny robot (laptop z natywnym ROS 2 Jazzy)

Wszystkie trzy tryby działają tak samo — różnice:

1. **Bringup robota** zamiast symulacji:
   ```bash
   ros2 launch rosbot_bringup rosbot_xl.yaml      # sanity: ros2 topic hz /scan, tf2_echo odom base_link
   ```
2. **`use_sim_time:=false`** WSZĘDZIE (slam/nav/explore/rviz) — realny robot chodzi na zegarze
   systemowym, nie `/clock`. Np.:
   ```bash
   ros2 launch m8_gazebo slam.launch.py use_sim_time:=false        # tryb 1
   ros2 launch m8_gazebo nav.launch.py map:=$HOME/maps/realna.yaml use_sim_time:=false   # tryb 2
   ros2 launch m8_gazebo explore.launch.py use_sim_time:=false     # tryb 3
   ```
3. **Sieć (jeśli Nav2/RViz na laptopie, robot to osobny komputer):**
   - Ten sam `ROS_DOMAIN_ID` na robocie i laptopie (np. `export ROS_DOMAIN_ID=10` + `export
     ROS_LOCALHOST_ONLY=0` w `~/.bashrc` na obu). Rozjechany domain = terminale się nie widzą
     (0 publisherów mimo działających węzłów).
   - **Synchronizacja zegarów (chrony/NTP) — krytyczne.** Przy `use_sim_time=false` każda maszyna
     stempluje TF własnym zegarem; rozjechane zegary = błędy „extrapolation into the future".
     ROSboty mają `chrony`; zsynchronizuj laptop do tego samego serwera NTP co robot. Sprawdzenie:
     `ros2 run tf2_ros tf2_echo map base_link` ma działać bez ostrzeżeń o ekstrapolacji.
4. **Filtr lasera** jest potrzebny też na sprzęcie (RPLIDAR montowany nisko widzi konstrukcję) —
   i tak jest w `slam.launch.py`/`explore.launch.py`, więc nic nie robisz.

---

## Wydajność (gdy „jedzie kawałek i staje")

Gazebo (serwer+GUI) + RViz + SLAM + Nav2 razem potrafią przeciążyć 8 rdzeni (load >20) — pętla
sterowania gubi takt, `/cmd_vel` leci zrywami, `velocity_smoother` zeruje prędkość → robot
jedzie–staje–jedzie. Ratunek (od najtańszego):
- **Zamknij RViz, gdy robot ma jechać** — to ~cały rdzeń. Robot nawiguje bez RViz tak samo.
- Zminimalizuj okno Gazebo (GUI rendering).
- Po wielu restartach **ubij zombie procesy**: `pkill -f gz; pkill -f nav2; pkill -f slam` przed
  ponownym uruchomieniem (zostają i kumulują obciążenie).
- W `nav2_rosbot.yaml` MPPI jest już odchudzone (`batch_size 1000`, `time_steps 40`).

## Pliki configów

| Plik | Tryb | Sedno |
|---|---|---|
| `config/laser_filter.yaml` | 1, 3 | BoxFilter `base_link`, `/scan → /scan_filtered` (wycina bryłę robota) |
| `config/slam_rosbot.yaml` | 1, 3 | slam_toolbox: `base_frame: base_link`, `scan_topic: /scan_filtered` |
| `config/nav2_rosbot.yaml` | 2 | Nav2 nawigacji po mapie (Jazzy): `base_link`, `enable_stamped_cmd_vel`, `obstacle_min_range 0.2`, **MPPI**, collision_monitor+docking_server |
| `config/explore.yaml` | 3 | PEŁNY config eksploracji (zwalidowany, port tutorial_pkg): **RPP** + Nav2 + explore_node + collision_monitor + docking_server, costmapy `/scan_filtered` |
| `explore.repos` | 3 | źródło explore_lite (m-explore-ros2, robo-friends/main) |
