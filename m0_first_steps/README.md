# Moduł 0 — Smoke test: pierwsze polecenia ROS 2

> Cel: sprawdzić, że ROS 2 Jazzy na Twoim Ubuntu 24.04 działa, i zobaczyć na żywo, jak wygląda graf nodów. **Nie piszemy własnego kodu** — używamy systemowych demo nodów.

## Setup (jednorazowo na początku kursu)

Potrzebujesz Ubuntu 24.04 z zainstalowanym ROS 2 Jazzy (natywnie, w maszynie wirtualnej albo w WSL2).
Instrukcja krok po kroku: sekcja **„ROS 2 u siebie”** w kursie (https://lucsrobotics.com/ros2-intro/#/instalacja).

Każdy nowy terminal musi znać ROS 2. Załaduj środowisko i dopisz je do `~/.bashrc`, żeby działo się to automatycznie:

```bash
source /opt/ros/jazzy/setup.bash
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
```

Szybkie sprawdzenie:

```bash
which ros2                          # /opt/ros/jazzy/bin/ros2
echo $ROS_DOMAIN_ID                 # puste = domena 0 (domyślna) - to w porządku
ros2 --help                         # lista komend
```

## Ćwiczenie

### Krok 1 — Doctor

```bash
ros2 doctor
```

Na końcu powinno pojawić się podsumowanie:

```
All 5 checks passed
```

Liczba testów może się różnić. Linie `UserWarning: ... has been updated to a new version` (informacja, że jest nowsza wersja pakietu) są normalne i nie oznaczają błędu. Jeśli widzisz `ERROR` albo `N/M checks failed` — zgłoś instruktorowi.

```bash
ros2 doctor --report               # pełen raport środowiska
```

### Krok 2 — Talker (terminal 1)

Otwórz terminal (`Ctrl+Alt+T`):

```bash
ros2 run demo_nodes_cpp talker
```

Co widzisz: co sekundę linijka typu:
```
[INFO] [talker]: Publishing: 'Hello World: 1'
[INFO] [talker]: Publishing: 'Hello World: 2'
...
```

Co to robi: node `talker` (C++ binarne z systemu) publikuje wiadomość typu `std_msgs/String` na topiku `/chatter` co 1 sekundę. To nie jest Twój kod — to demo wbudowane w ROS 2.

**Zostaw to działające.**

### Krok 3 — Listener (terminal 2)

Otwórz **nowe okno albo kartę terminala** (`Ctrl+Shift+T` w oknie terminala):

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

Pokaże (oprócz domyślnych ROS 2 topics):
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
# Drugi talker pod inną nazwą, publikujący na inny topic (remapowanie)
ros2 run demo_nodes_cpp talker --ros-args -r __node:=talker2 -r chatter:=/numbers

# w innym terminalu: pojawił się /talker2 i topic /numbers (typ nadal std_msgs/msg/String)
ros2 node list
ros2 topic list -t

# Sprawdź dostępne demo nody:
ros2 pkg executables demo_nodes_cpp
```

## Walidacja

Uruchom (katalog po `git clone` z „ROS 2 u siebie”, Krok 5):

```bash
cd ~/ros2_ws/src/ros2-intro-exercises/m0_first_steps
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
- **Moduł 1 — Nodes i narzędzia ros2** (https://lucsrobotics.com/ros2-intro/) — napiszesz własny node w Pythonie

## Materiał referencyjny

- Moduł 0 (lekcja w kursie): https://lucsrobotics.com/ros2-intro/
- [ROS 2 Jazzy CLI](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools.html)
- [Co to ROS 2](https://docs.ros.org/en/jazzy/Concepts.html)
