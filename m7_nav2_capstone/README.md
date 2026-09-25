# Warsztat W3 — Nav2 w Webots z TurtleBot3

> Capstone części nawigacyjnej kursu. Format prowadzony krok po kroku: instruktor pokazuje każdy
> krok, a Ty powtarzasz go na swoim Ubuntu 24.04 z ROS 2 Jazzy (natywnie, w maszynie wirtualnej
> albo w WSL2). Checkpointy co ok. 15 minut. Ten sam scenariusz opisuje strona W3 kursu.

## Cel

Złożyć w jeden działający system wszystko z poprzednich modułów:
- symulator (Webots) z robotem (TurtleBot3),
- budowanie mapy w czasie rzeczywistym (slam_toolbox),
- lokalizację na gotowej mapie (AMCL),
- planowanie ścieżki i omijanie przeszkód (stos Nav2),
- podgląd całości w RViz (Foxglove jest opcjonalny).

## Co dostajesz

```
m7_nav2_capstone/
├── README.md                          # ten plik
├── params/
│   └── nav2_params.yaml               # parametry Nav2 = domyślne z Jazzy + enable_stamped_cmd_vel
├── launch/
│   └── capstone_bringup.launch.py     # opcjonalny launch: Webots + Nav2 naraz (po zbudowaniu mapy)
└── maps/                              # miejsce na kopię mapy (README zapisuje mapę w ~/maps)
```

To nie jest pakiet do budowania przez colcon: używasz gotowych pakietów z apt, a z tego katalogu
bierzesz plik parametrów i opcjonalny launch.

## Przygotowanie

Potrzebujesz Ubuntu 24.04 + ROS 2 Jazzy desktop (strona kursu „ROS2 u siebie”) oraz warstwy W3:
Webots R2025a, `webots_ros2`, Nav2, slam_toolbox, TurtleBot3 i teleop. Pełną listę komend
instalacji znajdziesz na stronie W3 w ramce „Instalacja warstwy W3”. Webots ma pakiety tylko dla
amd64 (x86_64), więc na Macu z Apple Silicon tego warsztatu nie uruchomisz.

W każdym nowym terminalu najpierw wykonaj:

```bash
source /opt/ros/jazzy/setup.bash
CAP=~/ros2_ws/src/ros2-intro-exercises/m7_nav2_capstone   # tu leży ten katalog po sklonowaniu repo ćwiczeń
```

## Checkpoint 1 — Webots + TurtleBot3 (15 min)

```bash
# Terminal 1
ros2 launch webots_ros2_turtlebot robot_launch.py
```

Co się dzieje:
- Webots startuje ze światem-mieszkaniem,
- `webots_ros2_driver` publikuje `/scan`, `/odom`, `/tf` i zegar symulacji `/clock`,
- sterownik jazdy subskrybuje `/cmd_vel` i przyjmuje **`TwistStamped`** (nie zwykły `Twist`).

```bash
# Terminal 2 — sanity check
ros2 topic list
ros2 topic hz /scan      # ~5 Hz (lidar LDS-01)
ros2 topic hz /odom      # ~50 Hz (diffdrive_controller)
ros2 run tf2_tools view_frames     # PDF z drzewem TF
```

## Checkpoint 2 — SLAM toolbox i RViz (15 min)

```bash
# Terminal 2 — SLAM (w symulacji ZAWSZE use_sim_time:=true)
ros2 launch slam_toolbox online_async_launch.py use_sim_time:=true

# Terminal 3 — RViz z gotową konfiguracją Nav2 (mapa, lidar, TF, narzędzia do celów)
ros2 launch nav2_bringup rviz_launch.py use_sim_time:=true
```

Po kilku sekundach w RViz zobaczysz szarą mapę, która rośnie, gdy robot jedzie. Zostaw to okno
otwarte, przyda się też w trybie nawigacji.

## Checkpoint 3 — sterowanie robotem (15 min)

```bash
# Terminal 4 — teleop; stamped:=true, bo TurtleBot3 w Webots przyjmuje TwistStamped
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true
```

Klawisze: `i` = przód, `,` = tył, `j` / `l` = obrót, `k` = stop, `q` / `z` = szybciej / wolniej.

Jeździj po świecie 5-10 minut, aż mapa w RViz będzie zamknięta.

## Checkpoint 4 — zapis mapy (5 min)

Podaj **ścieżkę bezwzględną**: slam_toolbox zapisuje plik w katalogu, z którego sam został
uruchomiony, a nie tam, gdzie wołasz service. Dlatego `cd` do katalogu z mapami nic tu nie daje.

```bash
# Terminal 5
mkdir -p ~/maps
ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap \
    "{name: {data: '$HOME/maps/my_map'}}"
ls ~/maps
```

Dostajesz dwa pliki:
- `my_map.pgm` — bitmapa,
- `my_map.yaml` — metadane (m.in. `image: my_map.pgm`, `resolution: 0.05`, `origin: [...]`).

## Checkpoint 5 — Nav2 z mapą i parametrami (15 min)

Plik `params/nav2_params.yaml` to domyślne parametry Nav2 z Jazzy z jedną zmianą:
`enable_stamped_cmd_vel: true` w `controller_server`, `velocity_smoother`, `collision_monitor`,
`behavior_server` i `docking_server`. W Jazzy Nav2 domyślnie publikuje zwykły `Twist`, więc bez
tej flagi Nav2 planuje trasę, a robot stoi. Ten sam plik generuje skrypt ze strony W3
(`~/nav2_w3.yaml`) — możesz użyć dowolnego z nich.

Zatrzymaj SLAM (Ctrl+C w terminalu 2). RViz z terminala 3 zostaw otwarty. Uruchom Nav2:

```bash
# Terminal 2
ros2 launch nav2_bringup bringup_launch.py \
    map:=$HOME/maps/my_map.yaml \
    params_file:=$CAP/params/nav2_params.yaml \
    use_sim_time:=true
```

## Checkpoint 6 — initial pose w RViz (od razu po starcie Nav2)

Ustaw pozycję startową **od razu**, gdy AMCL wypisze `Please set the initial pose...`. Nie czekaj
na `Managed nodes are active`: global_costmap czeka na transformację `map → odom` od AMCL ok. 60 s,
a bez niej bringup kończy się komunikatem `Failed to bring up all requested nodes. Aborting bringup`
(wtedy Ctrl+C i uruchom Nav2 jeszcze raz).

1. W RViz kliknij **2D Pose Estimate** na górnym pasku.
2. Kliknij na mapie tam, gdzie robot stoi, i przeciągnij w kierunku, w którym patrzy.

Po chwili w logu zobaczysz `lifecycle_manager_navigation: Managed nodes are active`. AMCL zbiega
w 2-3 s: chmurka cząstek (particle cloud) skupia się wokół robota.

Sprawdź, czy Nav2 i robot mówią tym samym typem wiadomości (wszędzie `TwistStamped`):

```bash
ros2 topic info /cmd_vel -v | grep -E "Node name|Topic type"
```

(Opcjonalnie w Foxglove: Publish pose na `/initialpose`.)

## Checkpoint 7 — cel (goal) (10 min)

1. W RViz kliknij **Nav2 Goal**.
2. Kliknij cel na mapie i przeciągnij kierunek, w którym robot ma się zatrzymać.

Co zobaczysz:
- ścieżkę globalną z planner_server,
- lokalną trajektorię controllera,
- local costmap wokół robota i global costmap na całej mapie,
- robota, który jedzie po ścieżce i dojeżdża w ok. 30-60 s.

(Opcjonalnie w Foxglove: Publish pose na `/goal_pose`.)

## Checkpoint 8 — debug i strojenie (15 min)

Wyślij trudniejszy cel (np. za rogiem) i obserwuj, jak behavior tree reaguje:
- planner przelicza ścieżkę,
- controller dobiera prędkość i skręt,
- gdy robot utknie, uruchamiają się zachowania ratunkowe (recoveries): obrót w miejscu, czyszczenie
  costmapy, cofanie.

Co warto zmienić w `params/nav2_params.yaml` (po edycji uruchom Nav2 ponownie):
- `inflation_radius` w `local_costmap` i `global_costmap` (domyślnie 0.7 m) — zwiększ, jeśli robot
  ociera się o ściany,
- `vx_max` w `controller_server` → `FollowPath` (kontroler MPPI, domyślnie 0.5 m/s) — zmniejsz, żeby
  robot jechał wolniej. Zwiększenie działa tylko razem z `max_velocity` w `velocity_smoother`
  (pierwsza wartość, też 0.5), bo smoother obcina prędkość.

Prędkość możesz też zmienić na żywo, bez restartu:

```bash
ros2 param set /controller_server FollowPath.vx_max 0.3
ros2 param set /velocity_smoother max_velocity "[0.3, 0.0, 2.0]"
```

## Checkpoint 9 — opcjonalnie: kilka celów po kolei (15 min)

Sekwencję celów wyślesz przez `waypoint_follower`:

```bash
# Działa równolegle z Nav2
ros2 action send_goal /follow_waypoints \
    nav2_msgs/action/FollowWaypoints \
    "{poses: [
        {header: {frame_id: 'map'}, pose: {position: {x: 1.0, y: 1.0}, orientation: {w: 1.0}}},
        {header: {frame_id: 'map'}, pose: {position: {x: 2.0, y: -1.0}, orientation: {w: 1.0}}}
    ]}"
```

Współrzędne dobierz tak, żeby leżały na wolnym polu Twojej mapy.

## Opcjonalny launch: Webots + Nav2 naraz

Gdy mapa już istnieje (`~/maps/my_map.yaml`), możesz iterować nad Nav2 jednym poleceniem zamiast
kilku terminali:

```bash
ros2 launch $CAP/launch/capstone_bringup.launch.py
# inna mapa:
ros2 launch $CAP/launch/capstone_bringup.launch.py map_file:=/pełna/ścieżka/do/mapy.yaml
```

Launch nie startuje RViz ani SLAM. Uruchom wcześniej RViz (Checkpoint 2) i ustaw initial pose od
razu po starcie, tak jak w Checkpoincie 6.

## Pułapki

**Ścieżka jest w RViz, ale robot stoi**: Nav2 publikuje `Twist`, a TurtleBot3 w Webots czeka na
`TwistStamped`. `ros2 topic info /cmd_vel -v` pokaże wtedy dwa różne typy. Uruchom Nav2 z
`params_file:=$CAP/params/nav2_params.yaml` (albo `~/nav2_w3.yaml` ze strony W3).

**Robot nie rusza po goal**: sprawdź, czy `use_sim_time:=true` podałeś we wszystkich launchach
(SLAM, Nav2, RViz): `ros2 param get /controller_server use_sim_time` → musi być `True`.

**`Failed to bring up all requested nodes. Aborting bringup`**: initial pose nie przyszedł w ciągu
ok. 60 s od startu. Uruchom Nav2 ponownie i ustaw „2D Pose Estimate” od razu po `Please set the
initial pose...`.

**`Could not transform from base_link to map`**: drzewo TF jest niekompletne. `ros2 run tf2_tools
view_frames` wygeneruje PDF. Brakuje `map → odom`? AMCL nie dostał initial pose. Brakuje
`odom → base_link`? Nie działa sterownik Webots.

**Robot ociera się o ściany**: najpierw sprawdź lokalizację (punkty lidaru w RViz muszą leżeć na
ścianach mapy). Jeśli jest dobra, zwiększ `inflation_radius` w `nav2_params.yaml`.

**`Cannot configure map_server: file not found`** albo brak pliku mapy: mapa zapisała się w innym
katalogu. Zapisuj ją ze ścieżką bezwzględną (Checkpoint 4) i podawaj `map:=$HOME/maps/my_map.yaml`.

## Materiał referencyjny

- [Strona W3 w kursie](https://lucsrobotics.com/ros2-intro/#/module/11)
- [Nav2 docs](https://docs.nav2.org/)
- [SLAM toolbox](https://github.com/SteveMacenski/slam_toolbox)
- [Webots ROS2](https://docs.ros.org/en/jazzy/p/webots_ros2/)
- [Foxglove docs (opcjonalnie)](https://docs.foxglove.dev/)
