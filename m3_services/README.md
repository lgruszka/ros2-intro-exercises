# Moduł 3 — Ćwiczenie: services + actions

> Dwa pakiety: `intro_services` (obowiązkowy) i `intro_actions` (stretch).

## Co dostajesz

```
m3_services/
├── README.md
├── validate.sh                        # waliduje intro_services
├── intro_services/                    # ros2 package — Service
│   ├── package.xml
│   ├── setup.py
│   ├── setup.cfg
│   ├── resource/intro_services
│   └── intro_services/
│       ├── __init__.py
│       ├── add_two_ints_server_skeleton.py    # 3 TODO
│       ├── add_two_ints_server_solution.py
│       ├── add_two_ints_client_skeleton.py    # 2 TODO
│       └── add_two_ints_client_solution.py
└── intro_actions/                     # ros2 package — Action (stretch)
    ├── package.xml
    ├── setup.py
    ├── setup.cfg
    ├── resource/intro_actions
    └── intro_actions/
        ├── __init__.py
        └── fibonacci_server.py        # gotowy serwer (do uruchomienia)
```

## Setup w sandboxie

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src

# część obowiązkowa
cp -r /workspace/exercises/m3_services/intro_services .

# stretch
cp -r /workspace/exercises/m3_services/intro_actions .

cd ~/ros2_ws
colcon build --packages-select intro_services intro_actions
source install/setup.bash
```

## Część 1 — Service add_two_ints

### Twoje TODO

**Server** (`add_two_ints_server_skeleton.py`):

- **TODO 1**: `create_service(AddTwoInts, 'add_two_ints', self.handle_request)`
- **TODO 2**: w `handle_request` policz sumę: `response.sum = request.a + request.b`
- **TODO 3**: zaloguj request + sumę

**Client** (`add_two_ints_client_skeleton.py`):

- **TODO 1**: `create_client(AddTwoInts, 'add_two_ints')`
- **TODO 2**: w `call`: stwórz request, ustaw `a` i `b`, wywołaj `call_async` i `spin_until_future_complete`

### Build + uruchom

```bash
# Terminal 1 — serwer
ros2 run intro_services add_server
# → [INFO] Service /add_two_ints ready

# Terminal 2 — klient
ros2 run intro_services add_client 7 5
# → [INFO] 7 + 5 = 12

# Terminal 3 — tester CLI (bez pisania kodu klienta)
ros2 service call /add_two_ints example_interfaces/srv/AddTwoInts "{a: 10, b: 20}"
# → response: example_interfaces.srv.AddTwoInts_Response(sum=30)
```

### Inspekcja

```bash
ros2 service list                            # /add_two_ints powinien być
ros2 service type /add_two_ints              # → example_interfaces/srv/AddTwoInts
ros2 service info /add_two_ints              # serwer + klient w grafie
```

## Część 2 (stretch) — Fibonacci action

Serwer jest już zaimplementowany w `intro_actions/fibonacci_server.py` — po prostu go uruchom:

```bash
ros2 run intro_actions fibonacci_server
```

Wyślij goal z CLI (bez pisania klienta):

```bash
ros2 action send_goal /fibonacci \
    action_tutorials_interfaces/action/Fibonacci \
    "{order: 6}" \
    --feedback
```

Co powinieneś zobaczyć:

```
Sending goal:
   order: 6

Goal accepted with ID: ...
Feedback:
  partial_sequence: [0, 1]
Feedback:
  partial_sequence: [0, 1, 1]
Feedback:
  partial_sequence: [0, 1, 1, 2]
... (co 1 sekundę)

Result:
  sequence: [0, 1, 1, 2, 3, 5, 8]
```

## Walidacja

```bash
bash validate.sh
```

Skrypt sprawdza tylko część 1 (services). Stretch jest weryfikowany wizualnie przez `--feedback` w CLI.

## Pułapki

- **Klient wisi**: serwer nie biegnie (sprawdź `ros2 service list`) albo zła nazwa service (literówka).
- **`Service not ready`**: zwiększ timeout w `wait_for_service` albo upewnij się że serwer odpalony jako pierwszy.
- **Action: brak cancel handler** — w `intro_actions/fibonacci_server.py` jest minimalny przykład bez cancel. W produkcji (Nav2 itp.) zawsze dodajesz cancel_callback.

## Materiał referencyjny

- [Module 3 (lekcja w SPA)](../../app/src/modules/module3/Module3.jsx)
- [ROS2 Services tutorial](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Service-And-Client.html)
- [ROS2 Actions tutorial](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Writing-an-Action-Server-Client/Py.html)
