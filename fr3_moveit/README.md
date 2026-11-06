# fr3_moveit - Franka Research 3 + MoveIt 2 (warsztaty W7/W8)

Pakiet ćwiczeń do manipulacji na ramieniu **Franka Research 3 (FR3)**: MoveIt 2 w RViz (W7) i
**pick & place** z Pythona przez `moveit_py` (W8). Ubuntu 24.04 + ROS 2 Jazzy.

- **Bez robota:** fake hardware z `franka_ros2` (`use_fake_hardware:=true`, domyślnie).
- **Z robotem:** ten sam kod na prawdziwym FR3 (`robot_ip:=<IP_ROBOTA> use_fake_hardware:=false`).

Zastępuje pakiet `panda_moveit` (Panda z `moveit_resources`). Oficjalny `franka_ros2` dla Jazzy
wspiera FR3, a nie Pandę (FER).

## Instalacja

`franka_ros2` nie ma paczek w apt dla Jazzy. Budujesz go ze źródeł, dokładnie według README
(gałąź `jazzy`, https://github.com/frankarobotics/franka_ros2):

```bash
sudo apt install ros-jazzy-desktop ros-dev-tools
source /opt/ros/jazzy/setup.sh
mkdir -p ~/franka_ros2_ws/src
cd ~/franka_ros2_ws
git clone -b jazzy https://github.com/frankarobotics/franka_ros2.git src
vcs import src < src/dependency.repos --recursive --skip-existing
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y --skip-keys=zed_wrapper
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF
source install/setup.sh
```

Potem `moveit_py` i ten pakiet (w Twoim workspace z ćwiczeniami):

```bash
sudo apt install -y ros-jazzy-moveit-py
source ~/franka_ros2_ws/install/setup.bash      # najpierw franka_ros2
cd ~/ros2_ws
colcon build --symlink-install --packages-select fr3_moveit
source install/setup.bash
```

W każdym nowym terminalu: `source ~/franka_ros2_ws/install/setup.bash`, potem
`source ~/ros2_ws/install/setup.bash`.

## W7 - MoveIt interaktywnie w RViz

```bash
ros2 launch fr3_moveit moveit.launch.py
# RViz -> panel MotionPlanning (Planning Group: fr3_arm): Plan / Plan & Execute,
# Scene Objects -> Box -> Publish; grupa fr3_hand: open / close
```

## W8 - pick & place z Pythona

```bash
# Terminal 1 - infrastruktura (robot_state_publisher + ros2_control + chwytak + RViz, bez move_group):
ros2 launch fr3_moveit pick_place.launch.py

# Terminal 2 - sekwencja (scena: stół+klocek -> chwyt -> attach -> przeniesienie -> detach):
ros2 run fr3_moveit pick_place
```

Po udanej sekwencji (`✓ pick & place zakończony`) proces potrafi skończyć się komunikatem
`Segmentation fault` (exit 245). To błąd sprzątania moveit_py przy wyjściu, a nie Twojego kodu -
ruch jest już wykonany.

## Dlaczego nie sam oficjalny `franka_fr3_moveit_config moveit.launch.py` na fake hardware

Sprawdzone na żywo (docs/qa/fr3/fr3_verify.md w repo kursu):

1. Oficjalny `fr3_arm_controller` używa interfejsu **effort** (moment). Fake hardware
   (`mock_components/GenericSystem`) kopiuje komendę tylko do stanu tego samego typu, więc pozycje
   przegubów się nie zmieniają. MoveIt zgłasza udane wykonanie (`error_code 1`), a ramię stoi.
   Ten pakiet w trybie fake ładuje ten sam kontroler na interfejsie **position**
   (`config/fr3_fake_ros_controllers.yaml`). Z prawdziwym robotem używa oficjalnego pliku.
2. W fake hardware chwytak to tylko stały stan palców (`fake_gripper_state_publisher.py`),
   bez serwera akcji (`ros2 action info /franka_gripper/gripper_action` -> `Action servers: 0`).
   Ten pakiet uruchamia wtedy zastępczy chwytak (`fr3_moveit/fake_gripper.py`) z tym samym
   interfejsem co prawdziwy `franka_gripper_node`: `~/joint_states`, `~/gripper_action`,
   `~/move`, `~/grasp`. Zastępczy chwytak startuje z zamkniętymi palcami.

## Pliki

| Plik | Rola |
|---|---|
| `launch/moveit.launch.py` | W7: move_group + RViz (MotionPlanning) + ros2_control + chwytak |
| `launch/pick_place.launch.py` | W8: to samo bez move_group, RViz z `config/pick_place.rviz` |
| `config/moveit_controllers.yaml` | kontrolery dla MoveIt: `fr3_arm_controller` (FollowJointTrajectory), `franka_gripper` (GripperCommand, `max_effort` 20 N, `allow_failure`) |
| `config/fr3_fake_ros_controllers.yaml` | ros2_control w trybie fake: `fr3_arm_controller` na interfejsie position |
| `config/moveit_cpp.yaml` | MoveItPy: planning scene monitor + pipeline OMPL (3 próby, RRTConnect, skalowanie 0.5) |
| `config/moveit.rviz`, `config/pick_place.rviz` | widoki RViz dla W7 i W8 (na bazie oficjalnego `moveit.rviz`) |
| `fr3_moveit/pick_place.py` | pełna sekwencja pick & place (wzorzec: tutorial „Motion Planning Python API") |
| `fr3_moveit/fake_gripper.py` | zastępczy chwytak dla fake hardware |

URDF, SRDF (`fr3_arm`, `fr3_hand`, pozy `ready`/`extended`/`open`/`close`), kinematyka i limity
pochodzą z oficjalnych pakietów `franka_description`, `franka_bringup` i `franka_fr3_moveit_config`.

## Status weryfikacji

**Fake hardware: zweryfikowane end-to-end** (kontener `ros:jazzy`, amd64, 2026-11-06, franka_ros2
v3.6.1 / 8c94664, MoveIt 2.12.4): budowa wg README, `moveit.launch.py` (plan + execute rusza
ramieniem), `pick_place.launch.py` + `ros2 run fr3_moveit pick_place` -> kroki 1/8-8/8,
`✓ pick & place zakończony`. Szczegóły: `docs/qa/fr3/fr3_verify.md`.

**Prawdziwy FR3: niezweryfikowane.** Tryb `use_fake_hardware:=false` używa oficjalnych kontrolerów
i `franka_gripper_node`, ale nie był uruchomiony na robocie. Przed zajęciami sprawdź na stanowisku:
zwolnij ruchy (`max_velocity_scaling_factor: 0.1` w `config/moveit_cpp.yaml`), najpierw sam plan,
chwyt klocka (siła `max_effort`, zachowanie `allow_failure` przy chwycie).
