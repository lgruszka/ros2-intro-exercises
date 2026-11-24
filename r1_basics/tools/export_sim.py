#!/usr/bin/env python3
"""W11: eksport modelu symulacji R1 z unitree_rl_mjlab dla węzła r1_sim (ROS 2).

Uruchom w katalogu unitree_rl_mjlab, w tym samym środowisku Pythona co trening (ta sama wersja mujoco):
    python /ścieżka/do/r1_basics/tools/export_sim.py --out ~/r1_policy
Zapisuje:
    scene/scene.xml + scene/assets/  - scena MuJoCo z treningu (robot z aktuatorami pozycyjnymi, wzmocnieniami
                      i kolizjami jak w mjlab, podłoga) - przez Scene.write() z mjlab
    sim_meta.json   - opcje fizyki ustawiane przez mjlab dopiero po kompilacji (krok 5 ms, solver, iteracje),
                      decimation, wysokość startowa, kolejność przegubów i wartości kontrolne aktuatorów
    r1_flat.mjb     - tylko z --mjb: cały skompilowany model w jednym pliku (ok. 100 MB, ta sama wersja mujoco)
Politykę (policy.onnx) skopiuj osobno z logs/rsl_rl/r1_velocity/<data>/.
"""
import argparse
import json
import os
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--task', default='Unitree-R1-Flat')
    ap.add_argument('--out', default='r1_policy')
    ap.add_argument('--device', default='cuda:0', help='cuda:0 albo cpu')
    ap.add_argument('--mjb', action='store_true', help='zapisz też skompilowany model .mjb (duży)')
    a = ap.parse_args()

    sys.path.insert(0, os.getcwd())          # pakiet src/ z unitree_rl_mjlab
    import mujoco
    import mjlab.tasks  # noqa: F401  (rejestr zadań mjlab)
    import src.tasks  # noqa: F401    (zadania Unitree, w tym Unitree-R1-Flat)
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    cfg = load_env_cfg(a.task, play=True)
    cfg.scene.num_envs = 1
    env = ManagerBasedRlEnv(cfg=cfg, device=a.device)
    m = env.sim.mj_model
    out = Path(a.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    env.scene.write(out / 'scene')
    if a.mjb:
        mujoco.mj_saveModel(m, str(out / 'r1_flat.mjb'))
    robot = env.scene['robot']
    o = m.opt
    meta = {
        'task': a.task,
        'mujoco_version': mujoco.__version__,
        'decimation': int(cfg.decimation),
        'init_height': float(cfg.scene.entities['robot'].init_state.pos[2]),
        'joint_names': list(robot.joint_names),
        'nu': int(m.nu),
        'opt': {
            'timestep': float(o.timestep), 'integrator': int(o.integrator), 'cone': int(o.cone),
            'solver': int(o.solver), 'jacobian': int(o.jacobian), 'iterations': int(o.iterations),
            'tolerance': float(o.tolerance), 'ls_iterations': int(o.ls_iterations),
            'ls_tolerance': float(o.ls_tolerance), 'ccd_iterations': int(o.ccd_iterations),
            'impratio': float(o.impratio), 'gravity': [float(g) for g in o.gravity],
            'enableflags': int(o.enableflags), 'disableflags': int(o.disableflags),
        },
        # wartości kontrolne (po randomizacji domeny z trybu play) - do porównania z modelem z scene.xml
        'check': {
            'actuator_kp': [float(v) for v in m.actuator_gainprm[:, 0]],
            'actuator_kd': [float(-v) for v in m.actuator_biasprm[:, 2]],
            'actuator_forcerange': [[float(a), float(b)] for a, b in m.actuator_forcerange],
            'dof_armature': [float(v) for v in m.dof_armature],
            'body_mass_total': float(m.body_mass.sum()),
        },
    }
    (out / 'sim_meta.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print(json.dumps(meta, indent=2))
    print(f'zapisane: {out / "scene" / "scene.xml"}, {out / "sim_meta.json"}')
    env.close()


if __name__ == '__main__':
    main()
