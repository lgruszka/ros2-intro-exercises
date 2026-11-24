# sim/ - gotowa polityka chodu R1 do W11 (symulacja)

- `policy.onnx` - polityka chodu wytrenowana przez nas w `unitree_rl_mjlab` (zadanie `Unitree-R1-Flat`,
  PPO, 3000 iteracji, 4096 robotów naraz; przebieg opisany w W11). **Tylko do symulacji** - nie jest to
  wbudowany sterownik Unitree i nie przeszła żadnej walidacji na prawdziwym robocie.
- `sim_meta.json` - opcje fizyki MuJoCo z treningu (krok 5 ms, solver, iteracje), wersja mujoco, kolejność przegubów.
- `scene/scene.xml` - scena z treningu zapisana przez mjlab (`Scene.write`): model R1 z aktuatorami i kolizjami
  + podłoga. Siatki (`scene/assets/robot/*.STL`, ok. 22 MB) NIE są w repo - pobierz je: `../tools/get_meshes.sh`.

Licencje: model R1 i siatki pochodzą z `unitreerobotics/unitree_rl_mjlab` (Apache-2.0, © Unitree Robotics);
scena jest pochodną tego modelu. Wagi polityki: wytrenowane przez LucsRobotics kodem Apache-2.0, udostępnione
na licencji pakietu (MIT).

Uruchomienie: `ros2 launch r1_basics walk.launch.py sim_dir:=$(pwd) goal_x:=1.5 goal_y:=0.8` (z katalogu `sim/`).
