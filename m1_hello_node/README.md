# Moduł 1 — Ćwiczenie: pierwszy własny node

> Pakiet ROS2: `intro_node`. Cel: napisać minimalny node który co sekundę loguje "alive".

## Co dostajesz

```
m1_hello_node/
├── README.md                              # ten plik
├── validate.sh                            # sprawdza twoje rozwiązanie
└── intro_node/                            # ros2 package (ament_python)
    ├── package.xml
    ├── setup.py
    ├── setup.cfg
    ├── resource/intro_node
    └── intro_node/
        ├── __init__.py
        ├── hello_skeleton.py              # TU WPISUJESZ KOD (2 TODO)
        └── hello_solution.py              # podpowiedź
```

## Setup w sandboxie

```bash
# 1. utwórz workspace (raz, jeśli nie ma)
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src

# 2. skopiuj pakiet
cp -r /workspace/exercises/m1_hello_node/intro_node .

# 3. build + source
cd ~/ros2_ws
colcon build --packages-select intro_node
source install/setup.bash
```

## Twoje TODO

Otwórz `intro_node/intro_node/hello_skeleton.py`. Wypełnij 2 miejsca:

- **TODO 1**: w `__init__` utwórz timer 1.0 s wywołujący `self.tick`
  - Hint: `self.timer = self.create_timer(1.0, self.tick)`
- **TODO 2**: w `tick()` zaloguj wiadomość typu "alive #N"
  - Hint: `self.get_logger().info(f'alive #{self.count}')`
  - Pamiętaj o `self.count += 1` na końcu

## Build + uruchom

```bash
cd ~/ros2_ws
colcon build --packages-select intro_node
source install/setup.bash

# Terminal 1
ros2 run intro_node hello
```

Co powinieneś widzieć:

```
[INFO] [<timestamp>] [hello]: alive #0
[INFO] [<timestamp>] [hello]: alive #1
[INFO] [<timestamp>] [hello]: alive #2
...
```

W drugim terminalu — inspekcja grafu:

```bash
# Lista uruchomionych nodów
ros2 node list
# →  /hello

# Co publikuje /hello?
ros2 node info /hello
# → /hello
#     Subscribers:
#     Publishers:
#       /rosout: rcl_interfaces/msg/Log
#     Service Servers:
#       /hello/describe_parameters: ...
#       ...
```

Zwróć uwagę: `/hello` publikuje na `/rosout` (tam idą wszystkie logi z `get_logger()`). Reszta servisów to default parameter API które dostajesz za darmo z każdym nodem.

## Walidacja

```bash
bash validate.sh
```

Skrypt sprawdza:
- czy pakiet jest zbudowany
- czy `ros2 run intro_node hello` startuje
- czy `/hello` pojawia się w `ros2 node list`
- czy logi lecą na `/rosout`

Sukces: `✓ Module 1 exercise — PASSED`.

## Stretch (opcjonalne)

1. **Zmień severity**: zamiast `info` użyj `warn`. Sprawdź jak wygląda w terminalu (zwykle żółty).
2. **Throttling**: dodaj `throttle_duration_sec=2.0` do logu. Powinno wypisywać co 2 sekundy zamiast co 1.
3. **Logowanie raz**: w `__init__` dodaj `self.get_logger().info('startup', once=True)`. Powinno się pojawić raz na początku, nigdy więcej.
4. **Debug level**: spróbuj `self.get_logger().debug('not visible by default')`. Potem uruchom z `ros2 run intro_node hello --ros-args --log-level debug` — debug powinien się pojawić.

## Materiał referencyjny

- [Module 1 (lekcja w SPA)](../../app/src/modules/module1/Module1.jsx)
- [rclpy Node API](https://docs.ros.org/en/jazzy/p/rclpy/rclpy.node.html)
- [rclpy Logging](https://docs.ros.org/en/jazzy/Concepts/About-Logging.html)
