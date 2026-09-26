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

## Setup (Ubuntu 24.04 + ROS 2 Jazzy)

Pakiet masz już w workspace po `git clone` repo ćwiczeń (kurs: „ROS2 u siebie”, Krok 5 —
https://lucsrobotics.com/ros2-intro/#/instalacja). **Nie kopiuj** go w inne miejsce `~/ros2_ws/src` — dwie kopie tego
samego pakietu kończą się błędem colcon `Duplicate package names`.

```bash
# pakiet leży w: ~/ros2_ws/src/ros2-intro-exercises/m4_launch/
cd ~/ros2_ws
colcon build --packages-select intro_demo --symlink-install
source install/setup.bash
```

Nie masz jeszcze workspace'u? Jednorazowo:

```bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone https://github.com/lgruszka/ros2-intro-exercises.git
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

## Pakiet `intro_launch`: drabinka „Launch w przeglądarce” na Ubuntu

W module M5 piszesz w przeglądarce plik `turtle.launch.py` (etapy L1-L3). Ten sam plik uruchomisz na
Ubuntu 24.04 + ROS 2 Jazzy z pakietem `intro_launch`, który leży obok `intro_demo`:

```
m4_launch/intro_launch/
├── package.xml, setup.py, setup.cfg, resource/intro_launch
├── launch/turtle.launch.py          # szkielet z TODO L1 - wklej tu swój plik z przeglądarki
└── intro_launch/circle_driver.py    # gotowy node (entry point circle_driver), jak w przeglądarce
```

```bash
sudo apt install ros-jazzy-turtlesim          # jeśli jeszcze go nie masz
cd ~/ros2_ws
colcon build --packages-select intro_launch --symlink-install
source install/setup.bash
ros2 launch intro_launch turtle.launch.py speed:=2.0
```

Argument `speed:=2.0` działa dopiero po etapie L3 (`DeclareLaunchArgument` + `LaunchConfiguration`).
Sprawdź wynik w drugim terminalu: `ros2 node list` pokazuje `/sim` i `/driver_alfa`, a
`ros2 param get /driver_alfa speed` zwraca `Double value is: 2.0`. Po zmianie pliku launch uruchom
`colcon build` ponownie albo zbuduj pakiet z `--symlink-install` (jak wyżej).

## Materiał referencyjny

- Module 4 (lekcja w SPA): https://lucsrobotics.com/ros2-intro/
- [ROS2 Launch tutorial](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Creating-Launch-Files.html)
- [launch_ros API](https://docs.ros.org/en/jazzy/p/launch_ros/index.html)
