# Moduł 6 (TF2) — Ćwiczenie: follower przez TF

> Pakiet ROS 2: `m5_tf2_turtle`. Cel: turtle2 jedzie za turtle1, używając wyłącznie transformacji TF
> (zero ręcznej trygonometrii — `lookup_transform` zwraca pozycję celu już w układzie followera).

## Co dostajesz

```
m5_tf2_turtle/
├── README.md                  # ten plik
├── launch/turtle_tf2.launch.py
└── m5_tf2_turtle/
    ├── tf_broadcaster.py       # publikuje pose każdego żółwia jako frame TF względem world
    └── tf_follower.py          # lookup_transform('turtle2','turtle1') -> cmd_vel dla turtle2
```

## Build i uruchomienie

```bash
cd ~/ros2_ws
colcon build --packages-select m5_tf2_turtle --symlink-install && source install/setup.bash

# Wszystko naraz (turtlesim + broadcastery + follower):
ros2 launch m5_tf2_turtle turtle_tf2.launch.py

# W drugim terminalu steruj turtle1 - turtle2 podąży:
ros2 run turtlesim turtle_teleop_key
```

## Podgląd w RViz

```bash
rviz2
```

W RViz ustaw **Global Options → Fixed Frame** na `world`, potem **Add → TF** i zaznacz
**Show Names**. Zobaczysz ramki `turtle1` i `turtle2` poruszające się na żywo względem `world`.

Z terminala:

```bash
ros2 run tf2_tools view_frames              # PDF z drzewem world -> turtle1 / turtle2
ros2 run tf2_ros tf2_echo turtle2 turtle1   # położenie turtle1 w układzie turtle2
```

Opcjonalnie możesz też użyć Foxglove (panel 3D z warstwą TF), ale RViz wystarcza.

## Uwaga (Jazzy)

`lookup_transform(target, source)` — target PIERWSZY. Tu `('turtle2','turtle1')`: pozycja turtle1
w układzie turtle2. Kolejność w CLI jest taka sama: `tf2_echo A B` = `lookup_transform(A, B)`,
czyli położenie B wyrażone w układzie A. Nie sugeruj się nazwami `source`/`target` w komunikacie
usage narzędzia.

## Stretch

- Dodaj turtle3 i drugi follower (turtle3 śledzi turtle2) — kaskada.
- Dodaj stały offset (follower trzyma dystans 1 m za celem zamiast wjeżdżać na niego).
