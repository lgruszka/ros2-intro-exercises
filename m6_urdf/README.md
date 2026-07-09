# Moduł 7 (URDF) — Ćwiczenie: 3-DoF manipulator

> Pakiet ROS2: `m6_urdf`. Cel: opisać prosty 3-DoF arm w URDF/xacro i zobaczyć go animowanego
> w Foxglove 3D (ten sam model co interaktywny URDFViewer w treści modułu).

## Co dostajesz

```
m6_urdf/
├── README.md                       # ten plik
├── urdf/simple_arm.urdf.xacro       # base_link + 3 segmenty (makro cyl_link), 3 jointy revolute
├── launch/display_arm.launch.py     # robot_state_publisher (xacro.process_file) + joint_oscillator
└── m6_urdf/joint_oscillator.py       # publikuje /joint_states sinusoidalnie (headless, bez GUI)
```

## Build i uruchomienie

```bash
cd ~/ros2_ws
colcon build --packages-select m6_urdf --symlink-install && source install/setup.bash

ros2 launch m6_urdf display_arm.launch.py
```

Launch rozwija xacro przez `xacro.process_file(...).toxml()` (NIE `open().read()` — robot_state_publisher
nie rozumie surowego xacro), publikuje URDF jako `/robot_description`, a `joint_oscillator` animuje jointy
przez `/joint_states`.

## Podgląd

Foxglove (ws://localhost:8765) -> panel 3D: model wczyta się automatycznie z `/robot_description` przy
połączeniu live; dodaj TF. Model porusza się sam (joint_oscillator). Na natywnym desktopie możesz zamiast
oscylatora odpalić `joint_state_publisher_gui` (okno z suwakami).

## Stretch

- Zmień `joint_3` na `prismatic` (teleskop) — zobacz różnicę ruchu.
- Dodaj parametr `arm_length` w xacro i wygeneruj 4-DoF zamiast 3-DoF.
- Walidacja: `xacro simple_arm.urdf.xacro > /tmp/arm.urdf && check_urdf /tmp/arm.urdf`
  (`check_urdf` z pakietu `liburdfdom-tools`; działa na ROZWINIĘTYM URDF, nie na .xacro).
