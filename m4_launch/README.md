# Moduł 4 — Ćwiczenie: workspace + launch file

> Pakiet `intro_demo` z dwoma nodami (counter, monitor) plus launch file uruchamiający 3 nody jednocześnie z parametrem `rate`.

## Co dostajesz

```
m4_launch/
├── README.md
├── validate.sh
└── intro_demo/
    ├── package.xml
    ├── setup.py
    ├── setup.cfg
    ├── resource/intro_demo
    ├── launch/
    │   └── two_counters.launch.py     # TU WYPEŁNIASZ TODO
    └── intro_demo/
        ├── __init__.py
        ├── counter.py                 # gotowy publisher /count_X
        └── monitor.py                 # gotowy subscriber wszystkich /count_*
```

## Setup w sandboxie

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
cp -r /workspace/exercises/m4_launch/intro_demo .

cd ~/ros2_ws
colcon build --packages-select intro_demo --symlink-install
source install/setup.bash
```

## Co robi pakiet

- **`counter`** — publikuje `Int32` na topiku zadanym argumentem `--ros-args -r topic:=...`. Czas między wiadomościami sterowany parametrem `rate` (Hz).
- **`monitor`** — subskrybuje wszystkie topiki `/count_*` (wildcard), loguje sumę otrzymanych wartości.
- **`two_counters.launch.py`** — uruchamia dwa countery + jeden monitor jednocześnie.

## Twoje TODO

Otwórz `launch/two_counters.launch.py`. Wypełnij 3 sekcje:

- **TODO 1**: `DeclareLaunchArgument('rate', default_value='1.0')`
- **TODO 2**: `Node()` dla countera A — package `intro_demo`, executable `counter`, name `counter_a`, parameters `{'rate': LaunchConfiguration('rate')}`, remappings `[('count', 'count_a')]`
- **TODO 3**: drugi `Node()` analogicznie dla countera B z remappings `[('count', 'count_b')]`

(monitor jest już gotowy w launch file)

## Build + uruchom

```bash
cd ~/ros2_ws
colcon build --packages-select intro_demo --symlink-install
source install/setup.bash

# Default
ros2 launch intro_demo two_counters.launch.py

# Z argumentem (3 Hz)
ros2 launch intro_demo two_counters.launch.py rate:=3.0
```

W drugim terminalu — inspekcja:

```bash
ros2 node list
# /counter_a
# /counter_b
# /monitor

ros2 topic list
# /count_a
# /count_b
# /parameter_events
# /rosout

ros2 topic echo /count_a
# data: 0
# ---
# data: 1
# ---
# ...

ros2 launch intro_demo two_counters.launch.py --show-args
# Arguments (pass arguments as '<name>:=<value>'):
#   rate    Częstotliwość publikowania w Hz
#           (default: '1.0')
```

## Stretch

1. **Trzeci counter**: dodaj `counter_c` z osobnym argumentem `name_c` (default `'c'`) i remappings do `count_<name_c>`.
2. **Per-node rate**: zamiast jednego argumentu `rate`, daj `rate_a` i `rate_b` z różnymi defaultami (1.0 i 2.5 Hz). Każdy counter dostaje swój.
3. **Output to log**: zmień `output='screen'` na `output='log'` dla countera B. Logi trafią do `~/.ros/log/<timestamp>/counter_b/stdout.log`.

## Walidacja

```bash
bash validate.sh
```

Skrypt sprawdza:

- pakiet zbudowany
- `ros2 launch ...` startuje bez błędu
- `/counter_a` i `/counter_b` widoczne w `ros2 node list`
- `/count_a` publikuje wartości

## Pułapki

- **Launch file not found**: zapomniany wpis w `setup.py` `data_files` dla `launch/`. Sprawdź konfigurację — w naszym pakiecie jest już dodane.
- **Argument nie działa**: pamiętaj o `LaunchConfiguration('rate')` zamiast literalnego stringa `'rate'`.
- **Monitor nic nie loguje**: countery używają topiku `count` (relative). Musisz remappować do `count_a`/`count_b` w launch.

## Materiał referencyjny

- [Module 4 (lekcja w SPA)](../../app/src/modules/module4/Module4.jsx)
- [ROS2 Launch tutorial](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Creating-Launch-Files.html)
- [launch_ros API](https://docs.ros.org/en/jazzy/p/launch_ros/index.html)
