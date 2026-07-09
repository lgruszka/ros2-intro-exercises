# Moduł 0 — Smoke test: pierwsze polecenia ROS2

> Cel: zweryfikować że sandbox działa, ROS2 jest gotowy, i że rozumiesz jak wygląda graf nodów na żywo. **Nie piszemy własnego kodu** — używamy systemowych demo nodów.

## Setup (jednorazowo na początku kursu)

W swoim sandboxie (VS Code w przeglądarce) wszystko już jest. ROS2 Jazzy zainstalowany, sourceowany przy każdym nowym terminalu, `ROS_DOMAIN_ID` ustawiony per student.

Quick sanity check:

```bash
echo $ROS_DOMAIN_ID                # Twój unikalny domain, np. 7
which ros2                          # /opt/ros/jazzy/bin/ros2
ros2 --help                         # lista komend
```

## Ćwiczenie

### Krok 1 — Doctor

```bash
ros2 doctor
```

Powinno wypisać listę testów z `:white_check_mark:` przy każdym. Jeden warning typu `QoS` jest OK (to wymaga uruchomionych nodów żeby zweryfikować). Jeśli widzisz `ERROR` — zgłoś instruktorowi.

```bash
ros2 doctor --report               # pełen raport środowiska
```

### Krok 2 — Talker (terminal 1)

Otwórz terminal w VS Code (Ctrl+\`):

```bash
ros2 run demo_nodes_cpp talker
```

Co widzisz: co sekundę linijka typu:
```
[INFO] [talker]: Publishing: 'Hello World: 1'
[INFO] [talker]: Publishing: 'Hello World: 2'
...
```

Co to robi: node `talker` (C++ binarne z systemu) publikuje wiadomość typu `std_msgs/String` na topiku `/chatter` co 1 sekundę. To nie jest Twój kod — to demo wbudowane w ROS2.

**Zostaw to działające.**

### Krok 3 — Listener (terminal 2)

Otwórz **nowy tab** w terminalu (klik `+` przy zakładce):

```bash
ros2 run demo_nodes_cpp listener
```

Powinieneś widzieć kolejne wiadomości:
```
[INFO] [listener]: I heard: [Hello World: 42]
[INFO] [listener]: I heard: [Hello World: 43]
...
```

Numerki w `listener` lecą od momentu jego startu — talker biegnie już wcześniej, więc nie zaczyna od 1.

### Krok 4 — Inspekcja grafu (terminal 3)

Trzeci terminal:

```bash
ros2 node list
```

Pokaże:
```
/listener
/talker
```

```bash
ros2 topic list
```

Pokaże (oprócz domyślnych ROS2 topics):
```
/chatter
/parameter_events
/rosout
```

```bash
ros2 topic info /chatter
```

Zobaczysz:
```
Type: std_msgs/msg/String
Publisher count: 1
Subscription count: 1
```

### Krok 5 — Streaming danych

```bash
ros2 topic echo /chatter
```

To samo co listener — ale z linii poleceń, nie potrzebujesz pisać node'a. `Ctrl+C` żeby zatrzymać.

### Krok 6 — Częstotliwość

```bash
ros2 topic hz /chatter
```

Po kilku sekundach wypisze:
```
average rate: 1.000
  min: 0.999s max: 1.001s std dev: 0.00033s window: 10
```

Czyli talker publikuje ~1 Hz. Stabilnie.

### Stretch — różne typy wiadomości

```bash
# Inny demo node — publikuje liczby
ros2 run demo_nodes_cpp talker --ros-args -r __node:=talker2 -r chatter:=/numbers
# Hmm, ten konkretny binarny i tak publikuje String. Zostawmy to.

# Sprawdź dostępne demo nody:
ros2 pkg executables demo_nodes_cpp
```

## Walidacja

Uruchom:

```bash
bash validate.sh
```

Skrypt:
- sprawdza `ros2 doctor` (oczekuje 0 errorów)
- uruchamia talker w tle
- czeka 3 sekundy
- sprawdza czy `/chatter` jest w `ros2 topic list`
- sprawdza czy `ros2 topic echo /chatter` daje przynajmniej 1 wiadomość
- czyści wszystko

Sukces:
```
✓ Module 0 smoke test — PASSED
```

## Po ćwiczeniu

Zostaw 1 terminal otwarty z `talker` — przyda się w module 1 (sprawdzimy ten sam graf z lifecycle perspective).

Następny moduł:
- **[Module 1 — Nodes & ros2 CLI](../../app/src/modules/module1/Module1.jsx)** — napiszemy własny node Pythonem

## Materiał referencyjny

- [Module 0 (lekcja w SPA)](../../app/src/modules/module0/Module0.jsx)
- [ROS2 Jazzy CLI](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools.html)
- [Co to ROS2](https://docs.ros.org/en/jazzy/Concepts.html)
