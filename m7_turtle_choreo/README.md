# Warsztat W2 — Choreografia żółwi

> Pakiet ROS2: `m7_turtle_choreo`. Cel: trzy żółwie rysują synchronicznie lemniskatę.
> Jeden node (choreographer) nadaje wspólną fazę, każdy dancer tańczy ją w przesunięciu fazowym.
> Pokazuje synchronizację przez topic i czyste sterowanie parametryczne.

## Co dostajesz

```
m7_turtle_choreo/
├── README.md                       # ten plik
├── launch/choreo.launch.py
└── m7_turtle_choreo/
    ├── choreographer_node.py        # timer 50 Hz -> publikuje fazę (Float64) na /choreo/phase
    └── dancer_node.py               # subskrybuje fazę + pose, liczy target z lemniskaty, P-controller
```

## Build i uruchomienie

```bash
cd ~/ros2_ws
colcon build --packages-select m7_turtle_choreo --symlink-install && source install/setup.bash

ros2 launch m7_turtle_choreo choreo.launch.py
```

Launch startuje turtlesim, spawnuje turtle2/turtle3, uruchamia choreographer i 3 dancery z offsetami
`0`, `2π/3`, `4π/3`. Każdy dancer dostaje tę samą fazę i przelicza ją na własny punkt na krzywej.

## Strojenie

```bash
ros2 param set /choreographer_node speed 0.3      # tempo
# offset/krzywa: argumenty launch / parametry dancera
```

## Pułapki

- **Dancer milczy / żółw nie rusza**: turtleN jeszcze nie zespawnowany (brak `/turtleN/pose`).
  Launch spawnuje je z `ExecuteProcess` (`/spawn`) z opóźnieniem — daj chwilę, sprawdź `ros2 topic list`.
- **Żółwie nie nadążają za fazą**: za małe `kp_lin` albo za duże `speed` choreographera (cel ucieka
  szybciej, niż żółw goni). To nie kwestia QoS/`depth` — to strojenie wzmocnień.

## Stretch

- Podmień lemniskatę na gwiazdę pięcioramienną: `r = 1 + 0.5·cos(5·t)`, `x = r·cos(t)`, `y = r·sin(t)`.
- Dodaj czwartego tancerza (offset `π/2` dla każdego z 4).
