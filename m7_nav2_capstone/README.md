# Warsztat praktyczny — Nav2 w Webots z TurtleBot3

> Capstone kursu. Format prowadzony krok po kroku. Instruktor demonstruje, uczestnicy próbują na własnym sandboxie. Checkpointy co ~15 minut.

## Cel

Złożyć w jeden działający system wszystko z poprzednich modułów:
- Symulator (Webots) z robotem (TurtleBot3)
- Budowanie mapy w czasie rzeczywistym (slam_toolbox)
- Lokalizacja w mapie (AMCL)
- Planowanie ścieżki i unikanie przeszkód (Nav2 stack)
- Wizualizacja przepływu w Foxglove
- (Opcjonalnie) Live demo Unitree Go2/G1 — ten sam stos na fizycznym robocie

## Co dostajesz

```
m7_nav2_capstone/
├── README.md                          # ten plik
├── params/
│   └── nav2_params.yaml               # konfiguracja Nav2 (planner, controller, costmaps)
├── launch/
│   └── capstone_bringup.launch.py     # opcjonalny launch który robi wszystko jednocześnie
└── maps/
    └── .gitkeep                       # tu wyląduje twoja zapisana mapa
```

## Setup w sandboxie

W sandboxie kursu wszystkie pakiety są już zainstalowane: `webots_ros2`, `slam_toolbox`, `nav2_bringup`, `teleop_twist_keyboard`, `turtlebot3*`.

```bash
mkdir -p ~/ros2_capstone
cd ~/ros2_capstone
cp -r /workspace/exercises/m7_nav2_capstone/* .
```

Nie musisz nic budować — używamy istniejących pakietów + naszych YAML/launch files.

## Checkpoint 1 — Webots + TurtleBot3 (15 min)

```bash
# Terminal 1
ros2 launch webots_ros2_turtlebot robot_launch.py
```

Co się dzieje:
- Webots startuje (świat: małe mieszkanie z meblami)
- TurtleBot3 spawnowany w (0, 0)
- `webots_ros2_driver` publikuje `/scan`, `/odom`, `/tf`
- Robot subskrybuje `/cmd_vel`

W Foxglove (drugi tab przeglądarki) — dodaj 3D panel, source `/tf` + `/scan` żeby zobaczyć lidar na żywo.

```bash
# Terminal 2 — sanity check
ros2 topic list
ros2 topic hz /scan      # ~5 Hz
ros2 topic hz /odom      # ~100 Hz
ros2 run tf2_tools view_frames     # PDF z drzewem TF
```

## Checkpoint 2 — SLAM toolbox (15 min)

```bash
# Terminal 2
ros2 launch slam_toolbox online_async_launch.py use_sim_time:=true
```

W Foxglove 3D panel dodaj source `/map`. Zobaczysz puste pole (białe = jeszcze nie zbadane).

## Checkpoint 3 — sterowanie robotem (15 min)

```bash
# Terminal 3
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Klawisze:
- `i` = forward, `,` = backward, `j` = left, `l` = right, `k` = stop
- `q` / `z` = zwiększ / zmniejsz prędkość

Jeźdź po świecie 5-10 minut. Cel: pokryć cały dostępny obszar. SLAM aktualizuje mapę live.

## Checkpoint 4 — zapis mapy (5 min)

Gdy mapa wygląda kompletna:

```bash
# Terminal 4
cd ~/ros2_capstone/maps
ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap \
    "{name: {data: 'my_map'}}"
```

Powinieneś dostać dwa pliki:
- `my_map.yaml` — metadane mapy
- `my_map.pgm` — bitmapa

Sprawdź: `cat my_map.yaml` powinien zawierać `image: ./my_map.pgm`, `resolution: 0.05`, `origin: [...]`.

## Checkpoint 5 — Nav2 stack (15 min)

Zatrzymaj SLAM (Ctrl+C w terminalu 2). Uruchom Nav2 z mapą:

```bash
# Terminal 2 (ten sam co wcześniej)
ros2 launch nav2_bringup bringup_launch.py \
    map:=$HOME/ros2_capstone/maps/my_map.yaml \
    params_file:=$HOME/ros2_capstone/params/nav2_params.yaml \
    use_sim_time:=true
```

Po ~10 sekundach w logach zobaczysz lifecycle aktywację:
```
[lifecycle_manager-1] Configuring map_server
[lifecycle_manager-1] Activating map_server
[lifecycle_manager-1] Configuring amcl
[lifecycle_manager-1] Activating amcl
... aż do bt_navigator
```

## Checkpoint 6 — Initial pose w Foxglove (10 min)

W Foxglove panel 3D dodaj layery: `/map`, `/tf`, robot model (z URDF).

Robot pewnie stoi w złym miejscu. AMCL nie wie gdzie zaczyna:
1. Wybierz narzędzie **Publish → Pose** w 3D panel
2. Topic: `/initialpose`
3. Kliknij na mapie tam gdzie robot fizycznie jest, przeciągnij w kierunku jego orientacji

AMCL skonwerguje w 2-3 sekundy. Zobaczysz „chmurę cząsteczek" wokół robota w 3D — z czasem się zacieśni.

## Checkpoint 7 — Send goal (10 min)

Wyślij robotowi cel:
1. Narzędzie **Publish → Pose**
2. Topic: `/goal_pose`
3. Kliknij na mapie gdzie chcesz dotrzeć

Co zobaczysz:
- Niebieska linia: globalna ścieżka (z planner_server)
- Zielona/żółta: trajektoria controller-a
- Pomarańczowy obrys wokół robota: local costmap
- Robot rusza po linii. Powinien dotrzeć w ~30-60 sekund

## Checkpoint 8 — debug i tweaking (15 min)

Zatrzymaj robota, wyślij trudniejszy goal (np. za rogiem). Obserwuj jak BT decyduje:
- Planner przelicza ścieżkę
- Controller dobiera prędkość/zwrot
- Gdy utknie — recoveries odpalają (spin in place, clear costmap, backup)

Testuj różne tweaki w `params/nav2_params.yaml`:
- `inflation_radius` (zwiększ jeśli ociera się o ściany)
- `max_vel_x` w `controller_server` (zwolnij robota dla bezpieczeństwa)
- `desired_linear_vel` w `controller_server`

Po edycji YAML — restart Nav2.

## Checkpoint 9 — opcjonalnie, multiple waypoints (15 min)

Możesz wysłać sekwencję celów przez `nav2_waypoint_follower`:

```bash
# Działa równolegle z Nav2
ros2 action send_goal /follow_waypoints \
    nav2_msgs/action/FollowWaypoints \
    "{poses: [
        {header: {frame_id: 'map'}, pose: {position: {x: 1.0, y: 1.0}, orientation: {w: 1.0}}},
        {header: {frame_id: 'map'}, pose: {position: {x: 2.0, y: -1.0}, orientation: {w: 1.0}}}
    ]}"
```

## Checkpoint 10 — Live demo Unitree Go2/G1 (opcjonalnie)

Jeśli warunki logistyczne pozwolą, instruktor pokaże ten sam Nav2 stack działający na realnym robocie Unitree Go2 albo G1. Ta sama mapa, ta sama konfiguracja, ta sama Foxglove. Różnica: zamiast Webots, driver realnego robota.

Jeśli demo na żywo nie będzie możliwe (transport, network setup), zastępujemy pre-recorded video tego samego scenariusza.

## Co dalej

Skończyłeś 2-dniowy kurs. Materiał do dalszej pracy:

- **Appendix A**: Parameters i dynamic reconfigure
- **Appendix B**: Custom interfaces (msg/srv/action)
- **Appendix C**: ros2 bag — record / replay topiców
- **Appendix D**: Foxglove vs rqt cheat-sheet

Te tematy mają osobne sekcje w PDF workbooku. Twój passcode do platformy działa jeszcze 30 dni — możesz wracać i ćwiczyć.

Dla zespołów, które chcą iść dalej: dedykowane kursy zaawansowane Unitree EDU dla G1 i Go2 (manipulation, RL, VLA, multi-robot fleet). Zapytaj instruktora.

## Pułapki

**Robot nie rusza po goal**: 99% przypadków `use_sim_time:=true` nie wszędzie. Sprawdź: `ros2 param get /controller_server use_sim_time` → musi być `True`.

**`Could not transform from base_link to map`**: TF tree niekompletne. `ros2 run tf2_tools view_frames` wygeneruje PDF. Brakuje `map → odom`? AMCL nie skonwergował.

**Robot ociera się o ściany**: `inflation_radius` w `nav2_params.yaml` za mały. Zwiększ do `0.6 m`.

**`Cannot configure map_server: file not found`**: Absolute path do mapy: `map:=$HOME/ros2_capstone/maps/my_map.yaml`.

## Materiał referencyjny

- [Module 7 (lekcja w SPA)](../../app/src/modules/module7/Module7.jsx)
- [Nav2 docs](https://docs.nav2.org/)
- [SLAM toolbox](https://github.com/SteveMacenski/slam_toolbox)
- [Webots ROS2](https://docs.ros.org/en/jazzy/p/webots_ros2/)
- [Foxglove Studio docs](https://docs.foxglove.dev/)
