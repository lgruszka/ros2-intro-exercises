# r1_basics - Unitree R1 EDU w ROS 2 Jazzy (warsztaty W9-W12)

Pakiet ćwiczeń do humanoida **Unitree R1 EDU**: chód z `/cmd_vel` i dojazd do punktu (W9) oraz ręce,
talia i głowa przez `arm_sdk` plus obraz z kamery w głowie (W10). Ubuntu 24.04 + ROS 2 Jazzy.

- **Tylko R1 EDU.** R1 AIR i R1 bez EDU nie dają dostępu developerskiego (Unitree: rozwój własny tylko EDU).
- **Bez robota:** makieta `r1_mock` odtwarza zachowanie API robota (sport API, `/lowstate`, `arm_sdk`),
  a nie fizykę chodu. Ten sam kod uruchamiasz potem na robocie.
- **Jazzy nie jest oficjalnie wspierany przez Unitree** (testowane Foxy i Humble). Pakiety wiadomości
  `unitree_api` i `unitree_hg` z `unitree_ros2` budujemy na Jazzy tak samo jak w W5/W6 (Go2).
- Robot korzysta z wbudowanego sterownika ruchu Unitree (chód i równowaga). **Nie używamy trybu
  debug** (L2+R2): po wejściu w niego sport API i `arm_sdk` przestają działać.

## Co jest w środku

| Węzeł (`ros2 run r1_basics ...`) | Rola | Wejścia → wyjścia | Parametry (domyślne) |
|---|---|---|---|
| `cmd_vel_bridge` | most `/cmd_vel` → sport API (SetVelocity 7105) | `/cmd_vel`, `/r1/estop`, `/api/sport/response` → `/api/sport/request`, `/r1/cmd_vel_sent` | `max_vx 0.3`, `max_vy 0.2`, `max_wz 0.5`, `duration_s 0.5`, `rate_hz 10.0`, `cmd_timeout_s 0.5` |
| `sport_cli` | jednorazowe komendy: `get_fsm`, `stand`, `start`, `stop` | `/api/sport/request` ↔ `/api/sport/response` | `--timeout 3` |
| `dead_reckoning` | odometria zliczeniowa: prędkość zadana + kurs z IMU | `/r1/cmd_vel_sent`, `/lowstate` → `/r1/odom` (+ TF `odom` → `base_link`) | `rate_hz 20.0`, `publish_tf true` |
| `goto_point` | dojazd do punktu, regulator P (holonomiczny) | `/r1/odom`, `/goal_pose` → `/cmd_vel` | `odom_topic /r1/odom`, `goal_x`/`goal_y`, `k_lin 0.8`, `k_yaw 1.5`, `tol 0.10`, `max_v 0.3`, `max_wz 0.5` |
| `arm_sequence` | ręce + talia + głowa przez `arm_sdk` (machanie, rozglądanie, skinienie) | `/lowstate` → `/arm_sdk` (100 Hz, waga w `mode_pr`) | `ramp_s 1.0`, `move_s 2.0`, `rate_hz 100.0`, `max_joint_speed 1.0`, `check_fsm true` |
| `camera` | strumień RTP H.264 (UDP) → obraz | port UDP 5001 → `/r1/camera/image_raw` (`camera_link`), opcj. `/r1/camera/depth` | `port 5001`, `pipeline`, `depth_device` |
| `r1_mock` | makieta robota | `/api/sport/request`, `/arm_sdk` → `/api/sport/response`, `/lowstate`, `/r1/mock/ground_truth` | `fsm 811`, `reply_code 0`, `imu_yaw_bias 0.0` |
| `r1_sim` | W11: R1 w fizyce MuJoCo z polityką chodu z RL (kontrakt jak `r1_mock`); W12: `interface:=lowcmd` = jak tryb debug, wirtualna szubienica | W11: `/api/sport/request` → `/api/sport/response`, `/lowstate`; W12: `/lowcmd`, `/r1/sim/gantry`, `/r1/sim/remote` → `/lowstate`; oba: `/r1/mock/ground_truth`, `/r1/sim/reset` | `model`, `policy`, `meta`, `interface`, `gantry`, `cmd_delay_ms` |
| `r1_policy` | W12: polityka jako sterownik niskiego poziomu, stany PASSIVE / FIXSTAND / WALK. **Na robocie tylko na szubienicy** | `/cmd_vel`, `/lowstate` (w tym pilot), `/r1/policy/mode` → `/lowcmd`, `/r1/policy/state` | `policy`, `max_vx 0.3`, `max_vy 0.2`, `max_wz 0.5`, `lowstate_timeout_s 0.1`, `cmd_rate_hz 500` |

Wszystkie parametry z opisami: `config/r1_basics.yaml`. Nazwy węzłów, tematów i parametrów są takie same
jak w drabinkach przeglądarkowych kursu („ten sam kod na robocie”).

## Instalacja

Paczki systemowe (to samo co dla Go2 plus OpenCV i GStreamer dla kamery):

```bash
sudo apt install -y ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-rosidl-generator-dds-idl \
  ros-jazzy-cv-bridge python3-opencv python3-colcon-common-extensions \
  gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav \
  ros-jazzy-teleop-twist-keyboard ros-jazzy-rqt-image-view
```
- `ros-jazzy-rosidl-generator-dds-idl` jest potrzebne do budowy `unitree_api`/`unitree_hg`, a rosdep go
  nie zainstaluje.
- OpenCV instaluj z apt (`python3-opencv`), nie przez `pip install opencv-python`: wersja z pip nie ma
  GStreamera i węzeł `camera` się nie uruchomi.

Workspace: ćwiczenia + `unitree_ros2` (z niego budujemy tylko wiadomości `unitree_api` i `unitree_hg`
z `cyclonedds_ws/src/unitree`):

```bash
mkdir -p ~/r1_ws/src && cd ~/r1_ws/src
git clone https://github.com/lgruszka/ros2-intro-exercises.git
git clone https://github.com/unitreerobotics/unitree_ros2.git
cd ~/r1_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-up-to r1_basics      # buduje też unitree_api i unitree_hg, bez przykładów G1/H1
source install/setup.bash
```

Sprawdzenie bez robota: `colcon test --packages-select r1_basics && colcon test-result --verbose`
(testy CRC i logiki, patrz „Status weryfikacji”).

## Sieć i DDS (tylko z robotem)

Kabel z komputera do switcha R1 (gniazdo RJ45 na górze robota albo port użytkownika w docku EDU).
Wi-Fi robota służy aplikacji; DDS po Wi-Fi nie jest opisany, więc pracujesz po kablu.

```bash
ip -br addr                                          # znajdź interfejs Ethernet (np. enxXXXX)
sudo ip addr add 192.168.123.99/24 dev <iface>       # tymczasowo, do restartu
ping -c 3 192.168.123.161                            # komputer ruchu robota
cp ~/r1_ws/src/ros2-intro-exercises/r1_basics/config/cyclonedds_r1.xml ~/cyclonedds_r1.xml
sed -i 's/<NetworkInterface name="[^"]*"/<NetworkInterface name="<iface>"/' ~/cyclonedds_r1.xml
```

W **każdym** terminalu:
```bash
source /opt/ros/jazzy/setup.bash && source ~/r1_ws/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://$HOME/cyclonedds_r1.xml
export ROS_DOMAIN_ID=0                               # robot jest w domenie 0
ros2 daemon stop                                     # po zmianie DDS zawsze restart daemona
```
Dock EDU (Jetson, plecak): `ssh unitree@192.168.123.164` (hasło fabryczne 123).

## Bez robota: makieta `r1_mock`

Wystarczy zwykły terminal z workspace (bez `CYCLONEDDS_URI`). Jeśli na tej samej sieci ćwiczy więcej
osób, ustaw każdemu inny `ROS_DOMAIN_ID`, żeby makiety się nie mieszały.

**W9 - dojazd do punktu.** Makieta startuje w trybie chodu (FSM 811):
```bash
ros2 launch r1_basics walk.launch.py use_mock:=true goal_x:=1.5 goal_y:=0.8
# po ok. 6 s: goto_point: cel osiągnięty: (1.50, 0.80), odom (..), błąd 0.09 m
ros2 topic echo --once /r1/odom --field pose.pose.position              # odometria zliczeniowa
ros2 topic echo --once /r1/mock/ground_truth --field pose.pose.position # „prawda” makiety
```
Robot zatrzymuje się na granicy tolerancji (`tol 0.10`), więc błąd końcowy jest bliski 0,1 m.
Z dryfem IMU (`imu_yaw_bias:=0.02`, rad/s) odometria rozjeżdża się z prawdą (w teście ok. 8 cm
po 1,7 m). Tak samo, tylko gorzej, będzie na robocie.

Nowy cel w trakcie: `ros2 topic pub --once /goal_pose geometry_msgs/msg/PoseStamped "{header: {frame_id: odom}, pose: {position: {x: 0.5, y: -0.5}}}"`
albo RViz („2D Goal Pose”, Fixed Frame `odom`).

**Ręcznie (teleop)** - `goto_point` bez celu nie publikuje nic, więc `/cmd_vel` jest wolny:
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard     # z Shift: ruch w bok (vy)
ros2 topic pub --once /r1/estop std_msgs/msg/Bool "{data: true}"    # programowy stop
ros2 topic pub --once /r1/estop std_msgs/msg/Bool "{data: false}"   # zwolnij
```

**FSM i sport_cli.** Makieta w stanie „stanie zablokowane” ignoruje prędkość (założenie kursu: prędkość działa w trybie chodu 811):
```bash
ros2 launch r1_basics mock.launch.py fsm:=4
ros2 run r1_basics sport_cli get_fsm      # FSM = 4 (stanie zablokowane)
ros2 run r1_basics sport_cli start        # FSM 811 - dopiero teraz /cmd_vel rusza robotem
ros2 run r1_basics sport_cli stop         # StopMove
```
`ros2 launch r1_basics mock.launch.py reply_code:=127` - makieta odpowiada na 7105 kodem 127, jak
w zgłoszeniach społeczności (xr_teleoperate #319, unitree_sdk2_python #182); most loguje to raz i działa dalej.

**W10 - ręce.** Makieta startuje w FSM 4 (robot stoi):
```bash
ros2 launch r1_basics arm.launch.py use_mock:=true       # ok. 25 s, potem launch się kończy
ros2 topic echo /arm_sdk --field mode_pr                 # w drugim terminalu: waga 0 -> 100 -> 0
```
Testy bezpieczeństwa na makiecie: Ctrl+C w trakcie (rampa wagi do 0 przez 1 s),
`ros2 param set /r1_mock pause_lowstate true` (nieświeży `/lowstate` → natychmiastowe oddanie),
`ros2 run r1_basics r1_mock --ros-args -p fsm:=4 -p inject_fault_s:=6.0` (błąd silnika → oddanie).
Gdy uruchomisz `arm_sequence` przy makiecie w FSM 811, węzeł odmówi (exit 3). Z `check_fsm:=false`
makieta przejdzie w FSM 816 i zablokuje chód, tak jak opisują to zgłoszenia społeczności.

**Kamera bez robota** - testowy nadawca RTP H.264 na tym samym komputerze:
```bash
gst-launch-1.0 videotestsrc is-live=true ! video/x-raw,width=1280,height=720,framerate=30/1 ! videoconvert \
  ! x264enc tune=zerolatency speed-preset=ultrafast key-int-max=30 ! rtph264pay config-interval=1 pt=96 \
  ! udpsink host=127.0.0.1 port=5001
ros2 launch r1_basics camera.launch.py
ros2 run rqt_image_view rqt_image_view /r1/camera/image_raw
```

Czego makieta nie robi: nie ma fizyki chodu (prędkość dochodzi do zadanej z opóźnieniem 0,15 s,
bez poślizgów i bez upadków), nie ma kolizji rąk, FSM jest uproszczony (wszystkie przejścia dozwolone,
oprócz 811 przy aktywnym `arm_sdk`).

## W11: fizyka MuJoCo z polityką chodu (`r1_sim`)

Zamiast makiety: R1 w MuJoCo (CPU), nogami i rękami steruje polityka wytrenowana metodą RL w
`unitree_rl_mjlab` (zadanie `Unitree-R1-Flat`). Węzły z W9 działają bez zmian. **To nasza polityka,
nie wbudowany sterownik Unitree - tylko do symulacji** (na robocie wymagałaby trybu debug).

```bash
pip install --break-system-packages mujoco==3.5.0 onnxruntime   # mujoco jak w treningu (sim_meta.json)
# a) gotowa polityka z repo (sim/): najpierw siatki R1 z unitree_rl_mjlab (ok. 22 MB)
./tools/get_meshes.sh
ros2 launch r1_basics walk.launch.py sim_dir:=$(pwd)/sim goal_x:=1.5 goal_y:=0.8
# b) Twoja polityka z W11: katalog z policy.onnx, sim_meta.json i scene/ (tools/export_sim.py na maszynie z GPU)
ros2 launch r1_basics walk.launch.py sim_dir:=$HOME/r1_policy goal_x:=1.5 goal_y:=0.8
# prawda z symulacji vs odometria zliczeniowa:
ros2 topic echo /r1/mock/ground_truth --field pose.pose.position
# upadek (np. po FSM 1): ros2 service call /r1/sim/reset std_srvs/srv/Trigger
```

Pliki: `r1_basics/policy_sim.py` (MuJoCo + ONNX Runtime bez ROS: 83 obserwacje -> 24 cele przegubów co 20 ms),
`r1_basics/r1_sim.py` (węzeł ROS 2), `tools/export_sim.py` (eksport sceny i opcji fizyki z mjlab),
`tools/get_meshes.sh`, `sim/` (nasza polityka i scena; licencja siatek i modelu: Apache-2.0, © Unitree Robotics).

## W12: sim2real (`r1_policy`) - NA ROBOCIE TYLKO NA SZUBIENICY

> **Uruchomienie na prawdziwym R1 musi się odbyć na szubienicy, z robotem podwieszonym i asekurowanym przez cały
> czas próby, z instruktorem.** `r1_policy` działa w trybie debug Unitree: wbudowany sterownik równowagi jest
> wyłączony, robot trzyma się wyłącznie na polityce. Nic z W12 nie było jeszcze uruchamiane na prawdziwym R1.

```bash
# 1. polityka odporna na opóźnienie (maszyna z GPU, w katalogu unitree_rl_mjlab; instalacja jak w W11)
python tools/train_delay.py Unitree-R1-Flat-Delay --env.scene.num-envs=4096 --agent.logger=tensorboard --agent.max-iterations=2200
# 2. test odporności bez ROS (opóźnienia, KP ±20%, tarcie, masa) - polityka musi przejść 20 ms
python3 tools/robust_lowcmd.py ~/r1_policy
# 3. procedura na wirtualnej szubienicy (r1_sim interface:=lowcmd + r1_policy)
ros2 launch r1_basics policy.launch.py sim_dir:=$HOME/r1_policy use_sim:=true cmd_delay_ms:=20
ros2 topic pub --once /r1/sim/remote std_msgs/msg/String "{data: L2+UP}"     # FIXSTAND
ros2 topic pub --once /r1/sim/gantry std_msgs/msg/Float64 "{data: 0.0}"      # stopy na podłodze
ros2 topic pub --once /r1/sim/remote std_msgs/msg/String "{data: R2+A}"      # WALK, komenda zero
ros2 topic pub --once /r1/sim/gantry std_msgs/msg/Float64 "{data: -0.15}"    # lina luźna
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1}}"
ros2 topic pub --once /r1/sim/remote std_msgs/msg/String "{data: L2+B}"      # PASSIVE, robot na linie
# 4. robot: TYLKO na szubienicy, tryb debug (L2+R2 w damping/zero torque, robot zawieszony), etapy z W12
ros2 launch r1_basics policy.launch.py sim_dir:=$HOME/r1_policy use_sim:=false
```

Pilot (czytany z `/lowstate.wireless_remote`): L2+B → PASSIVE, L2+UP → FIXSTAND, R2+A → WALK. Zabezpieczenia
węzła: brak `/lowstate` > 0,1 s albo przechył > 1 rad → PASSIVE; `/cmd_vel` starszy niż 0,5 s → zero; Ctrl+C → PASSIVE.

## Na prawdziwym R1 EDU

### Zasady bezpieczeństwa (przeczytaj przed pierwszym uruchomieniem)

- Podczas developmentu robot wisi w **ramie ochronnej** albo na stojaku (zalecenie Unitree).
- Jedna osoba trzyma **pilota** i patrzy tylko na robota, druga obsługuje komputer. Wolna strefa
  1,5-2 m wokół robota, nikt w zasięgu rąk robota przy W10.
- Przećwicz oba zatrzymania, zanim cokolwiek uruchomisz: **miękkie** L2+B przytrzymane > 5 s
  (damping - **robot upadnie**, dlatego rama) i **twarde** - przycisk E-Stop (silniki bez zasilania).
- Start ze stojaka: L2+UP (stanie zablokowane), opuść robota i **nie puszczaj** (sam nie balansuje),
  po postawieniu obu stóp R2+A (chód). Z leżenia: L2+UP, potem długie L2+X.
- Pierwszy kontakt **bez ruchu**: `ros2 topic hz /lowstate`, `ros2 run r1_basics sport_cli get_fsm`.
- Zostaw **niskie limity** z `config/r1_basics.yaml` (vx 0,3, vy 0,2 m/s, wz 0,5 rad/s). Unitree nie
  podaje limitów prędkości; podnoś je stopniowo.
- **Nie** używaj trybu debug. `sport_cli` celowo nie ma komend Damp ani ZeroTorque (robot by upadł).
- **W10 tylko na stojącym robocie (FSM 4), nigdy razem z chodem (W9).** `arm_sdk` przy wadze ≥ 0,02
  w trybie chodu przełącza robota w FSM 816 i blokuje chód (zgłoszenia społeczności; wyjście z 816 jest
  nieopisane).
- Najpierw zatrzymaj robota, potem zamykaj procesy. Ctrl+C na moście wysyła StopMove. Gdy proces
  padnie bez tego, komenda wygaśnie po `duration_s` (0,5 s), bo most przestał ponawiać komendę. Że robot
  wtedy staje, to wniosek z opisu SetVelocity (czas trwania komendy) - sprawdź to na robocie (krok 2 niżej).

### W9: chód i dojazd do punktu

```bash
# 1. robot stoi w ramie/na stojaku, sieć jak wyżej
ros2 topic list | grep -E "lowstate|api/sport"
ros2 run r1_basics sport_cli get_fsm                 # 811 = chód; 4 i robot w ramie: sport_cli start; inaczej pilot
# 2. most + krótki test (2 s) - robot ma iść wolno do przodu i stanąć po Ctrl+C
ros2 run r1_basics cmd_vel_bridge
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1}}"     # drugi terminal, Ctrl+C po 2 s
# 3. teleop (Shift = bokiem), potem odometria: przejdź 1 m i porównaj /r1/odom z taśmą miarową
ros2 run teleop_twist_keyboard teleop_twist_keyboard
ros2 run r1_basics dead_reckoning
# 4. dojazd: najpierw krótki cel na wprost
ros2 launch r1_basics walk.launch.py goal_x:=1.0 goal_y:=0.0
```
Odometria: R1 nie ma potwierdzonego tematu odometrii, dlatego `dead_reckoning` całkuje zadaną prędkość
z kursem z IMU. Dryf rośnie z drogą: cele do ok. 2 m. Jeśli robot publikuje `/odommodestate` albo
`/lf/odommodestate` (sprawdź `ros2 topic list`), opisz to - patrz „Do sprawdzenia”.

### W10: ręce, talia, głowa

```bash
ros2 run r1_basics sport_cli stand                   # FSM 4 (albo pilot L2+UP)
ros2 topic echo --once /lowstate --field imu_state   # stan dochodzi?
ros2 launch r1_basics arm.launch.py                  # sekwencja ok. 25 s; Ctrl+C = oddanie w 1 s
```
Węzeł najpierw pyta o FSM (7001) i odmawia przy 811. Gdy robot nie odpowiada na 7001, kontynuuje
z ostrzeżeniem - wtedy sam upewnij się, że robot stoi. Nie uruchamiaj w tym czasie wbudowanych akcji
ramion (machanie z pilota/aplikacji): `arm_sdk` i usługa akcji wykluczają się (błąd 7400).

### Kamera (dock EDU)

- Wymagane łatki: Patch ≥ 1.0.1.17 i R1 Stereo Patch PC1 ≥ 0.0.1.42. Usługę wideo włączasz w aplikacji
  (Ustawienia → Stan usług), a `video_hub` zatrzymujesz ręcznie (konflikt).
- Strumienie RTP H.264 po UDP: 5001 obraz 1280×720, 5002/5003 lewe/prawe oko 544×448. Według
  dokumentacji dochodzą do docka EDU. Test na docku:
  `gst-launch-1.0 udpsrc port=5001 ! application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,payload=96 ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink sync=false`
- Dock ma Ubuntu 20.04 (JetPack 5.1.1), więc nie ma natywnego Jazzy. Propozycja **(do sprawdzenia na
  robocie)**: kontener `ros:jazzy` z `--net=host` na docku, w nim ten workspace i `camera.launch.py`:
  ```bash
  docker run -it --rm --net=host -v ~/r1_ws:/root/r1_ws ros:jazzy bash     # na docku
  # w kontenerze: apt install jak w „Instalacja”, colcon build, CycloneDDS z interfejsem docka, potem:
  ros2 launch r1_basics camera.launch.py                 # albo port:=5002 (mniejszy obraz)
  ```
- Głębia: `sudo unitree_depth_start` → `/dev/video-dep` (16 bit, mm, 10 fps), węzeł z
  `depth_device:=/dev/video-dep` (kontener potrzebuje `--device /dev/video-dep`). Format urządzenia nie
  był sprawdzony - węzeł ostrzeże, jeśli klatki nie są 16-bitowe.
- Surowy obraz 1280×720 bgr8 w 30 Hz to ok. 83 MB/s przez DDS. Do podglądu na laptopie po kablu
  wybierz raczej port 5002 (544×448, ok. 22 MB/s).
- `ros2 topic hz` na tak dużych obrazach zaniża częstotliwość (narzędzie w Pythonie nie nadąża:
  w teście 16-18 Hz przy faktycznych 30 Hz). Obraz sprawdzaj w `rqt_image_view` albo
  `ros2 topic echo --once --field width /r1/camera/image_raw`.
- Kamera siedzi na `head_yaw_link`: uruchom `arm_sequence` (głowa w lewo/prawo) i patrz, jak zmienia się obraz.

## Pliki

| Plik | Rola |
|---|---|
| `r1_basics/cmd_vel_bridge.py` | most `/cmd_vel` → 7105, watchdog, E-Stop, StopMove przy Ctrl+C, log kodów (127) |
| `r1_basics/sport_cli.py` | `get_fsm` / `stand` / `start` / `stop` z terminala |
| `r1_basics/dead_reckoning.py` | odometria zliczeniowa (prędkość zadana + kurs z IMU) |
| `r1_basics/goto_point.py` | regulator P dojazdu do punktu |
| `r1_basics/arm_sequence.py` | sekwencja `arm_sdk` z rampami wagi i zabezpieczeniami |
| `r1_basics/camera.py` | GStreamer → `sensor_msgs/Image` (+ głębia) |
| `r1_basics/r1_mock.py` | makieta robota |
| `r1_basics/arm_sdk.py` | tabela 13 przegubów (sloty, limity URDF, KP/KD), CRC `unitree_hg/LowCmd`, plan ruchu |
| `r1_basics/sport_api.py` | id API, stany FSM, budowanie żądań |
| `r1_basics/util.py`, `params.py` | geometria, regulator, parametry odporne na `-p x:=1` |
| `launch/walk.launch.py` | W9: most + odometria + dojazd (`use_mock`, `goal_x`, `goal_y`, `imu_yaw_bias`) |
| `launch/arm.launch.py` | W10: `arm_sequence` (`use_mock`), kończy się razem z sekwencją |
| `launch/camera.launch.py`, `launch/mock.launch.py` | kamera; sama makieta |
| `config/r1_basics.yaml` | wszystkie parametry z komentarzami |
| `config/cyclonedds_r1.xml` | CycloneDDS z interfejsem sieciowym (do edycji) |
| `test/test_crc.py`, `test/test_logic.py` | CRC kontra C++ Unitree; limity, prędkości i wagi planu ruchu |

**CRC `arm_sdk`:** oficjalny przykład R1 (`unitree_sdk2/example/r1/high_level/r1_arm_sdk_dds_example.cpp`,
wrapper `dds_wrapper/robots/r1/r1_pub.h`) **nie liczy CRC** dla `rt/arm_sdk` (pole zostaje 0; `crc32_core`
wołają tylko wydawcy `rt/lowcmd` i `rt/lowstate` (G1, Go2), a `ArmSdk` zarówno R1, jak i G1 wysyła 0). Przykład G1 w `unitree_ros2` też nie, a przykłady Pythonowe G1/H2 liczą.
**Czy R1 wymaga CRC na `rt/arm_sdk` - do sprawdzenia na robocie.** Ten pakiet liczy je zawsze (port
`crc32_core`, zgodny bit w bit z `motor_crc_hg.cpp` i `crc.h` z SDK), a `r1_mock` przy złym albo zerowym
CRC tylko ostrzega, nigdy nie odrzuca wiadomości.

**Kierunki przegubów** (osie z `R1.urdf`, w pozie zerowej ramię zwisa): łokieć 0 = przedramię pod kątem
prostym do ramienia, +1,57 = ręka wyprostowana, ujemny = mocniej zgięty; `shoulder_pitch` ujemny = ręka
do przodu; `shoulder_roll` lewy dodatni / prawy ujemny = ręka w bok; `head_yaw` i `waist_yaw` dodatni =
w lewo; `head_pitch` dodatni = w dół. Cel z oficjalnego przykładu R1 (prawy łokieć -1,57) leży poza
zakresem łokcia w URDF (-0,976..2,185) - nie kopiuj go.

## Status weryfikacji

**Makieta: zweryfikowane end-to-end** (kontener `ros:jazzy-ros-base` arm64, CycloneDDS, 2026-11-23):
budowa z `unitree_api` + `unitree_hg` z `unitree_ros2`, `pytest` 14/14 (w tym CRC kontra skompilowany
`motor_crc_hg.cpp`), dojazd do (1,5; 0,8) w ok. 6 s (błąd do prawdy 0,09 m), watchdog i E-Stop,
FSM 4/811 i `sport_cli`, pełna sekwencja `arm_sequence` (100 Hz, rampy 1 s, CRC OK, skok celu
≤ 0,01 rad na wiadomość), przerwania (Ctrl+C, nieświeży `/lowstate`, `motorstate`), FSM 816,
kamera z testowym strumieniem RTP H.264 (30 Hz), wszystkie launche. Szczegóły i liczby:
`docs/qa/r1/r1_verify.md` w repo kursu.

**Prawdziwy R1 EDU: niezweryfikowane.** Nic z tego pakietu nie było jeszcze uruchomione na robocie.

### Do sprawdzenia na prawdziwym R1

1. Czy `/api/sport/request` z ROS 2 (Jazzy, `unitree_api`) porusza R1 (7105), jakie kody wraca (127?),
   jakie limity prędkości są sensowne.
2. Czy robot publikuje `/odommodestate` / `/lf/odommodestate` (i co w nich jest), czy zostaje odometria zliczeniowa.
3. `arm_sdk` z ROS 2: czy CRC jest wymagane, czy rampa wagi przez `mode_pr` działa w FSM 4, co dzieje
   się z FSM (816?) i jak wrócić do chodu.
4. **Kierunki przegubów**: sekwencja zakłada konwencję osi z `R1.urdf` (patrz „Kierunki przegubów” wyżej).
   Sprawdź, że firmware ma tę samą, zanim puścisz pełną sekwencję: najpierw `-p waves:=1 -p max_joint_speed:=0.5`.
5. Wartości `motor_state[i].motorstate` w spoczynku (węzeł przerywa przy ≠ 0) i częstotliwość `/lowstate`
   (makieta 100 Hz; jeśli robot daje 500 Hz, węzły Pythona subskrybujące `/lowstate` zużyją więcej CPU).
6. Kamera: wersje łatek, czy strumień 5001 dochodzi do docka i do PC, czy kontener `ros:jazzy` na docku
   odbiera UDP, format `/dev/video-dep`.
7. Wersje firmware (ai_sport) i JetPack docka na danym egzemplarzu.
