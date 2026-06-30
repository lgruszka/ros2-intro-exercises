# ROS2 Intro — ćwiczenia (LucsRobotics)

Pakiety ROS2 do kursu **„Wprowadzenie do robotyki przez pryzmat ROS2"** (Jazzy).
Każdy folder `mN_*` to jedno ćwiczenie powiązane z modułem kursu. Pracujesz na
**szkielecie** (`*_skeleton.py`, z `TODO`), a obok masz **rozwiązanie referencyjne**
(`*_solution.py`) na wypadek gdybyś utknął.

> Kurs i materiały interaktywne: **https://lucsrobotics.com/ros2-intro/**
> Te same ćwiczenia są wbudowane w sandbox kursu (code-server w przeglądarce) —
> to repo jest dla osób, które chcą pracować **na własnym Ubuntu**.

---

## Wymagania

- **Ubuntu 24.04 LTS** (natywnie lub WSL2)
- **ROS2 Jazzy** zainstalowany — instrukcja: sekcja „ROS2 u siebie" w kursie
  lub [docs.ros.org/en/jazzy/Installation](https://docs.ros.org/en/jazzy/Installation.html)
  (wariant `ros-jazzy-desktop` — zawiera `turtlesim`, `tf2`, `rviz2`, itd.)
- `git`, `python3-colcon-common-extensions`, `python3-rosdep` (instalka ROS2 zwykle to ciągnie)

Sprawdź, że ROS2 żyje:

```bash
source /opt/ros/jazzy/setup.bash
ros2 doctor --report | head -20
```

---

## Setup workspace (jednorazowo)

ROS2 buduje **cały workspace**, nie pojedynczy plik. Robisz to raz:

```bash
# 1. workspace + klon ćwiczeń do src/
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone https://github.com/lgruszka/ros2-intro-exercises.git

# 2. zależności (rosdep dociągnie czego brakuje)
cd ~/ros2_ws
sudo rosdep init 2>/dev/null; rosdep update
rosdep install --from-paths src --ignore-src -r -y

# 3. build (--symlink-install = edytujesz .py i nie musisz rebuildować)
colcon build --symlink-install

# 4. source overlay — RÓB TO W KAŻDYM NOWYM TERMINALU
source install/setup.bash
```

> 💡 Dopisz `source ~/ros2_ws/install/setup.bash` do `~/.bashrc`, żeby nie pamiętać.
> Pamiętaj że `/opt/ros/jazzy/setup.bash` (underlay) musi iść **przed** overlayem.

Buduj tylko jeden pakiet zamiast wszystkiego:

```bash
colcon build --symlink-install --packages-select intro_node
```

---

## Mapa ćwiczeń

| Folder | Moduł kursu | Pakiet ROS2 | Uruchom |
|---|---|---|---|
| `m0_first_steps`  | M0 · Czym jest ROS2        | — (tylko CLI)  | `ros2 doctor`, `ros2 run demo_nodes_cpp talker` |
| `m1_hello_node`   | M1 · Nodes & ros2 CLI      | `intro_node`   | `ros2 run intro_node hello` |
| `m2_pub_sub`      | M2 · Topics + QoS          | `intro_pubsub` | `ros2 launch intro_pubsub talker_listener.launch.py` |
| —                 | M3 · DDS (eksperymenty CLI)| —              | patrz „DDS na żywo" w module M3 |
| `m3_services`     | M4 · Services/Params/Actions | `intro_services` (+ `intro_actions`) | `ros2 run intro_services add_server` |
| `m4_launch`       | M5 · Pakiety, colcon & launch| `intro_demo`   | `ros2 launch intro_demo two_counters.launch.py` |
| `m5_tf2_turtle`   | M6 · TF2 i drzewo frames   | `m5_tf2_turtle`| `ros2 launch m5_tf2_turtle turtle_tf2.launch.py` |
| `m6_urdf`         | M7 · URDF + viz            | `m6_urdf`      | `ros2 launch m6_urdf display_arm.launch.py` |
| `m7_turtle_hunter`| W1 · Łowca żółwi           | `m7_turtle_hunter` | `ros2 launch m7_turtle_hunter turtle_hunter_launch.py` |
| `m7_turtle_choreo`| W2 · Choreografia + Race   | `m7_turtle_choreo` | `ros2 launch m7_turtle_choreo choreo.launch.py` |
| `m7_nav2_capstone`| W3 · Nawigacja & SLAM (Webots) | `m7_nav2_capstone` | wymaga Webots — patrz moduł W3 |
| `m8_gazebo`       | M8 · Gazebo na własnym komputerze | `m8_gazebo` (config-only) | `ros2 launch m8_gazebo slam.launch.py` (ROSbot XL w Gazebo, 3 tryby) |
| `rosbot_nav`      | W4 · Realny ROSbot XL (Husarion) | `rosbot_nav` (config-only) | `ros2 launch rosbot_nav slam.launch.py` (mapowanie/nawigacja/eksploracja na sprzęcie) |
| `go2_autonomy`    | W5/W6 · Unitree Go2        | `go2_bringup`/`go2_bridge`/… | patrz `go2_autonomy/README.md` (most ruchu sport API) |

Folder `mN_*` ma własny `README.md` (krok po kroku) i `validate.sh` (auto-sprawdzenie). Pakiety
config-only (`m8_gazebo`, `rosbot_nav`) i sprzętowe (`go2_autonomy`) mają własne README z pełną instrukcją.

---

## Skeleton vs solution

Domyślnie `ros2 run <pakiet> <exe>` uruchamia **szkielet** — i dopóki nie wypełnisz
`TODO`, nie zadziała tak jak trzeba. To celowe: to Twoja praca. Rozwiązanie jest pod
osobnym entry pointem:

```bash
ros2 run intro_node hello              # Twój szkielet (m1_hello_node/intro_node/...)
ros2 run intro_node hello_solution     # rozwiązanie referencyjne
```

Launch-e demonstracyjne (`*.launch.py`) odpalają **rozwiązania**, żeby demo działało
od razu po buildzie — kod do napisania znajdziesz w `*_skeleton.py`.

---

## Praca na wielu maszynach (kurs stacjonarny)

ROS2 nie ma „mastera" — nody same się wykrywają w sieci (DDS discovery). Jeśli kilka
osób jest w **tej samej sieci LAN/Wi-Fi** z **tym samym `ROS_DOMAIN_ID`**, zobaczą
nawzajem swoje topiki. To podstawa eksperymentów w module M3 i fajny pokaz na żywo:

```bash
export ROS_DOMAIN_ID=42       # ustaw TĘ SAMĄ wartość na obu laptopach
# laptop A:
ros2 run intro_pubsub talker_solution
# laptop B (ten sam DOMAIN_ID, ta sama sieć):
ros2 run intro_pubsub listener_solution     # odbiera wiadomości z laptopa A
```

Różne `ROS_DOMAIN_ID` = izolacja (nie widzą się). Szczegóły w module **M3 · DDS**.

---

## Native gotchas (rzeczy, które gryzą poza sandboxem)

- **`source install/setup.bash` w każdym nowym terminalu** — inaczej `ros2 run` nie znajdzie pakietu.
- **`colcon build` odpalasz z `~/ros2_ws`** (korzeń workspace), nie z `src/`.
- **`--symlink-install`** = edytujesz `.py` i wystarczy ponowny `ros2 run` (bez rebuildu). Zmiany w `setup.py`/`package.xml` wciąż wymagają `colcon build`.
- **`ros2 daemon stop`** gdy `ros2 node list` / `ros2 topic list` pokazują „duchy" po crashu.
- **`/cmd_vel` na Jazzy to `TwistStamped`**, nie `Twist` (dotyczy warsztatów z robotami).

---

*Materiały kursowe LucsRobotics · dr inż. Łukasz Gruszka · licencja: do użytku uczestników kursu.*
