# Moduł 7 (URDF) — Ćwiczenie: 3-DoF manipulator

> Pakiet ROS 2: `m6_urdf`. Cel: opisać prosty 3-DoF arm w URDF/xacro i zobaczyć go w ruchu w RViz
> (ten sam model co interaktywny URDFViewer w treści modułu).

## Co dostajesz

```
m6_urdf/
├── README.md                       # ten plik
├── urdf/simple_arm.urdf.xacro       # base_link + 3 segmenty (makro cyl_link), 3 jointy revolute
├── launch/display_arm.launch.py     # robot_state_publisher (xacro.process_file) + joint_oscillator
│                                    #   (argumenty: gui:=true -> suwaki, rviz:=true -> rviz2)
└── m6_urdf/joint_oscillator.py       # publikuje /joint_states sinusoidalnie (bez okien)
```

## Build i uruchomienie

```bash
cd ~/ros2_ws
colcon build --packages-select m6_urdf --symlink-install && source install/setup.bash
```

**Opcja A - ramię porusza się samo:**

```bash
ros2 launch m6_urdf display_arm.launch.py
```

Launch rozwija xacro przez `xacro.process_file(...).toxml()` (NIE `open().read()` — robot_state_publisher
nie rozumie surowego xacro), publikuje URDF jako `/robot_description`, a `joint_oscillator` animuje jointy
przez `/joint_states`.

**Opcja B - ręcznie, suwakami.** Nie uruchamiaj jej równolegle z Opcją A: na `/joint_states` może
publikować tylko jedno źródło naraz, inaczej model skacze między wartościami.

```bash
# jednorazowo: okno z suwakami nie jest częścią każdej instalacji ROS 2
sudo apt install ros-jazzy-joint-state-publisher-gui

# terminal 1: robot_state_publisher z rozwiniętym xacro
ros2 run robot_state_publisher robot_state_publisher --ros-args \
  -p robot_description:="$(xacro $(ros2 pkg prefix --share m6_urdf)/urdf/simple_arm.urdf.xacro)"

# terminal 2: okno z trzema suwakami (joint1, joint2, joint3)
ros2 run joint_state_publisher_gui joint_state_publisher_gui
```

To samo jednym poleceniem: `ros2 launch m6_urdf display_arm.launch.py gui:=true`.

## Podgląd w RViz

W nowym terminalu uruchom `rviz2` (albo dodaj `rviz:=true` do launcha), a potem w oknie RViz:

1. **Global Options → Fixed Frame** ustaw na `base_link` (domyślne `map` tu nie istnieje).
2. **Add → RobotModel**, w ustawieniach: **Description Source: Topic**,
   **Description Topic: `/robot_description`**. Pojawi się model ramienia.
3. **Add → TF** (opcjonalnie **Show Names**), żeby zobaczyć ramki `base_link`, `link1`..`link3`.

Model porusza się sam (Opcja A) albo za suwakami (Opcja B). Konfigurację zapiszesz przez
**File → Save Config As** i wczytasz poleceniem `rviz2 -d plik.rviz`.

Opcjonalnie ten sam model pokaże Foxglove (panel 3D, `sudo apt install ros-jazzy-foxglove-bridge`),
ale do tego ćwiczenia wystarczy RViz.

## Stretch

- Zmień `joint3` na `prismatic` (teleskop): `axis xyz="0 0 1"`, `limit lower="0" upper="0.2"`
  i zobacz różnicę ruchu.
- 4-DoF: dodaj `link4` (makro `cyl_link`) i `joint4` (parent `link3`), a potem steruj suwakami
  `joint_state_publisher_gui` (`joint_oscillator` publikuje tylko 3 jointy).
- Walidacja: `xacro simple_arm.urdf.xacro > /tmp/arm.urdf && check_urdf /tmp/arm.urdf`
  (`check_urdf` z pakietu `liburdfdom-tools`; działa na ROZWINIĘTYM URDF, nie na .xacro).
