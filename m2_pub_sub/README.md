# Moduł 2 — Ćwiczenie: pierwszy pub/sub

> Pakiet ROS2: `intro_pubsub`. Cel: napisać `talker` i `listener` korzystające z topiku `/chatter` typu `std_msgs/String`.

## Co dostajesz

```
m2_pub_sub/
├── README.md                              # ten plik
├── validate.sh                            # sprawdza twoje rozwiązanie
└── intro_pubsub/                          # ros2 package
    ├── package.xml
    ├── setup.py
    ├── setup.cfg
    ├── resource/intro_pubsub
    └── intro_pubsub/
        ├── __init__.py
        ├── talker_skeleton.py             # ← TU WPISUJESZ KOD (3 TODO)
        ├── talker_solution.py             # ← podpowiedź (sneak peek)
        ├── listener_skeleton.py           # ← TU WPISUJESZ KOD (2 TODO)
        └── listener_solution.py
```

## Setup w sandboxie

Przy pierwszym ćwiczeniu w sandboxie potrzebujesz workspace:

```bash
# 1. utwórz workspace (raz)
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src

# 2. skopiuj pakiet (do każdego ćwiczenia)
cp -r /workspace/exercises/m2_pub_sub/intro_pubsub .

# 3. build + source
cd ~/ros2_ws
colcon build --packages-select intro_pubsub
source install/setup.bash
```

## Twoje TODO

### 1. Otwórz `intro_pubsub/intro_pubsub/talker_skeleton.py`

Wypełnij 3 TODO:
- **TODO 1**: utwórz publisher (typ `String`, topic `chatter`, depth 10)
- **TODO 2**: utwórz timer (period 0.5s, callback `self.tick`)
- **TODO 3**: w `tick()` zbuduj wiadomość, opublikuj, zaloguj

### 2. Otwórz `intro_pubsub/intro_pubsub/listener_skeleton.py`

Wypełnij 2 TODO:
- **TODO 1**: utwórz subscription (typ `String`, topic `chatter`, callback `self.on_message`, depth 10)
- **TODO 2**: w `on_message` zaloguj otrzymaną wiadomość

### 3. Build + uruchom

```bash
cd ~/ros2_ws
colcon build --packages-select intro_pubsub
source install/setup.bash

# Terminal 1
ros2 run intro_pubsub talker

# Terminal 2
ros2 run intro_pubsub listener

# Terminal 3 (kontrola)
ros2 topic echo /chatter
```

Powinieneś widzieć:
- Terminal 1: `[INFO] Published: Hello ROS2 #0`, `#1`, `#2`...
- Terminal 2: `[INFO] Received: Hello ROS2 #0`, `#1`, `#2`...
- Terminal 3: surowy stream YAML wiadomości

## Walidacja (opcjonalna)

```bash
bash validate.sh
```

Skrypt sprawdza:
- czy oba skeleton-y kompilują się bez błędów
- czy `talker` faktycznie publikuje na `/chatter`
- czy `listener` odbiera

Po sukcesie zobaczysz `✓ Module 2 exercise — PASSED`.

## Stretch (opcjonalne, po podstawie)

1. **Zmień typ wiadomości** na `geometry_msgs/Twist`:
   - publisher: ustaw `linear.x = 0.5`, `angular.z = 0.3`
   - obserwuj w Foxglove (3D panel → "Plot" → /chatter/linear/x)

2. **Dodaj QoS BEST_EFFORT**:
   - Zmień QoS w talker.py: `from rclpy.qos import qos_profile_sensor_data`
   - Sprawdź: czy listener nadal odbiera? (powinien — bo sam zmienisz też)
   - Co się stanie jak zostawisz listener na RELIABLE? (sprawdź `ros2 topic info -v /chatter`)

## Materiał referencyjny

- [Module 2 — Topics + QoS](../../../app/src/modules/module2/Module2.jsx) (treść lekcji)
- [Oficjalny tutorial ROS2](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.html)
- [rclpy QoS](https://docs.ros.org/en/jazzy/p/rclpy/rclpy.qos.html)
