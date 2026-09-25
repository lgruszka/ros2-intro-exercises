# Warsztat W1 — Łowca żółwi

> Pakiet ROS2: `m7_turtle_hunter`. Cel: jeden żółw (hunter) poluje na ofiary, łapie je (`/kill`),
> a game_manager spawnuje nowe (`/spawn`) i pilnuje wyniku. Cały ROS2 w jednym ćwiczeniu:
> node, pub/sub, timer, service client/server, parametry.

## Co dostajesz

```
m7_turtle_hunter/
├── README.md                          # ten plik
├── launch/turtle_hunter_launch.py
└── m7_turtle_hunter/
    ├── hunter_node.py                  # P-controller: szuka najbliższej ofiary, jedzie, łapie (/kill)
    └── game_manager_node.py            # respawn ofiar (/spawn), propagacja stanu przez /captures
```

## Build i uruchomienie

```bash
cd ~/ros2_ws
colcon build --packages-select m7_turtle_hunter --symlink-install && source install/setup.bash

ros2 launch m7_turtle_hunter turtle_hunter_launch.py
```

Launch startuje turtlesim, hunter_node i game_manager_node. Hunter co tick (10 Hz) wybiera najbliższą
ofiarę, steruje się P-controllerem (`kp_linear`, `kp_angular` jako parametry), a po złapaniu woła `/kill`
i publikuje na `/captures`; game_manager odbiera to i spawnuje nową ofiarę.

## Strojenie

Launch nadaje węzłom nazwy `hunter` i `game_manager` (`name=` w launchu), więc parametry
ustawiasz na `/hunter` (sprawdzisz to przez `ros2 node list`):

```bash
ros2 param set /hunter kp_linear 2.0
ros2 param set /hunter kp_angular 6.0
```

## Pułapki

- **Subskrypcje per-ofiara**: jedna metoda obsługuje wiele żółwi przez `lambda msg, n=name: self.on_prey_pose(n, msg)`
  (domyślny argument `n=name` zamraża nazwę w chwili tworzenia lambdy — bez niego wszystkie subskrypcje
  w pętli widziałyby ostatnią nazwę).
- **Race condition `/kill`**: async kill + spóźniony `/preyN/pose` może dać podwójny capture; rozwiązanie to
  cooldown (`recently_killed` z timestampem) ignorujący pose'y tuż po killu.

## Podgląd

Grę widzisz w oknie turtlesim. Złapania i pozycje podejrzysz w drugim terminalu:

```bash
ros2 topic echo /captures
ros2 topic echo /prey1/pose
```
