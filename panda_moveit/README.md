# panda_moveit — Franka Panda + MoveIt 2 (warsztaty W7/W8)

Pakiet ćwiczeń do manipulacji: **pick & place** na ramieniu Franka Emika Panda w symulacji
(ros2_control **mock hardware** — bez Gazebo, bez fizycznego robota). Ubuntu 24.04 + ROS 2 Jazzy.

## Instalacja

```bash
sudo apt install -y ros-jazzy-moveit ros-jazzy-moveit-py ros-jazzy-moveit-resources-panda-moveit-config
cd ~/ros2_ws
colcon build --symlink-install --packages-select panda_moveit
source install/setup.bash
```

## W7 — MoveIt interaktywnie (bez tego pakietu)

```bash
ros2 launch moveit_resources_panda_moveit_config demo.launch.py
# RViz -> panel MotionPlanning: Plan / Plan & Execute, Scene Objects -> Box -> Publish
```

## W8 — pick & place z Pythona (ten pakiet)

```bash
# Terminal 1 — infrastruktura (robot_state_publisher + ros2_control mock + kontrolery + RViz):
ros2 launch panda_moveit pick_place.launch.py

# Terminal 2 — sekwencja (scena: stół+klocek -> chwyt -> attach -> przeniesienie -> detach):
ros2 run panda_moveit pick_place
```

W RViz dodaj display **PlanningScene**, żeby widzieć stół, klocek i moment „attach"
(klocek podróżuje z chwytakiem).

## Pliki

| Plik | Rola |
|---|---|
| `launch/pick_place.launch.py` | rsp + ros2_control (mock) + spawnery kontrolerów + RViz |
| `config/moveit_cpp.yaml` | konfiguracja MoveItPy: planning scene monitor + pipeline OMPL (3 próby, RRTConnect) |
| `panda_moveit/pick_place.py` | pełna sekwencja pick & place (wzorzec: tutorial „Motion Planning Python API") |

## ✅ Status weryfikacji

**Zweryfikowane end-to-end na czystym ROS2 Jazzy (kontener, headless):** apt install → colcon build →
launch `rviz:=false` (3 kontrolery active) → `ros2 run panda_moveit pick_place` → wszystkie 8 kroków
sekwencji ✓ („pick & place zakończony"). Przed zajęciami odpal raz z RViz dla pewności wizualnej.

Dwie pułapki znalezione (i naprawione) podczas weryfikacji — omawiane w W8:
1. zamknięte palce przy zjeździe = goal w kolizji z klockiem → `open` przed zjazdem;
2. po attach klocek staje się częścią ROBOTA — kontakt z blatem to od tej chwili kolizja
   robot↔świat → klocek startuje 5 mm nad stołem.
