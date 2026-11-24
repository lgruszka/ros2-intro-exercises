#!/usr/bin/env python3
"""W12: test odporności polityki w trybie /lowcmd (sim2sim), bez ROS.

Przebieg jak procedura na szubienicy: robot wisi na linie (stopy w powietrzu) -> PASSIVE 1 s -> FIXSTAND 3 s ->
opuszczanie do dotknięcia stopami (lina wciąż napięta, FIXSTAND nie balansuje) -> WALK z komendą zero (polityka
trzyma równowagę) -> luzowanie liny (łapie dopiero przy upadku) -> marsz vx 0.2 m/s 6 s, bokiem vy 0.15 m/s 4 s,
obrót 0.4 rad/s 4 s, stop 3 s. Ta sama klasa R1PolicyController co w węźle
r1_policy; fizyka: R1PolicySim (MuJoCo), krok 5 ms, polityka co 20 ms, komendy z opóźnieniem `delay_ms`.

Użycie: python3 tools/robust_lowcmd.py <katalog sim> [--policy policy_delay.onnx] [--quick]
Wynik: tabela - czy robot ustał, czy lina musiała go złapać, jak trzymał prędkość.
"""
import argparse
import collections
import itertools
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from r1_basics.policy_ctrl import R1PolicyController, tilt  # noqa: E402
from r1_basics.policy_sim import R1PolicySim  # noqa: E402

LIFT = 0.12       # lina napięta 12 cm powyżej zaczepienia stojącego robota: stopy w powietrzu
TOUCH = 0.0       # zaczepienie na wysokości stojącego robota: stopy dotykają, lina jeszcze trzyma
SLACK = 0.15      # po luzowaniu lina łapie dopiero, gdy zaczepienie spadnie 15 cm poniżej pozycji stojącej


def scenario(sim, ctrl, delay_ms=0.0, kp_scale=1.0, friction=1.0, mass=0.0):
    sim.perturb(friction_scale=friction, extra_torso_mass=mass)
    hang = sim.attach_stand + LIFT
    touch = sim.attach_stand + TOUCH
    catch = sim.attach_stand - SLACK
    sim.reset(height=sim.init_height + LIFT)
    sim.gantry_height = hang
    ctrl.mode = 'PASSIVE'
    dt = sim.m.opt.timestep
    delay_s = delay_ms / 1000.0
    queue = collections.deque()
    plan = [('passive', 1.0), ('fixstand', 3.0), ('lower', 3.0), ('stand', 2.0), ('slack', 2.0),
            ('walk_x', 6.0), ('walk_y', 4.0), ('turn', 4.0), ('stop', 3.0)]
    cmds = {'walk_x': (0.2, 0.0, 0.0), 'walk_y': (0.0, 0.15, 0.0), 'turn': (0.0, 0.0, 0.4)}
    t = 0.0
    k = 0
    caught = False
    meas = collections.defaultdict(list)
    out = None
    for phase, dur in plan:
        if phase == 'fixstand':
            ctrl.request('FIXSTAND', current_slots(sim)[0])
        if phase == 'stand':
            ctrl.request('WALK', None)
        t_end = t + dur
        while t < t_end - 1e-9:
            frac = min(1.0, (t - (t_end - dur)) / dur)
            if phase == 'lower':
                sim.gantry_height = hang + (touch - hang) * frac
            if phase == 'slack':
                sim.gantry_height = touch + (catch - touch) * frac
            cmd = cmds.get(phase, (0.0, 0.0, 0.0))
            if k % 4 == 0 or ctrl.mode != 'WALK':
                q_s, dq_s = current_slots(sim)
                quat, _, gyro, _ = sim.imu()
                msg = ctrl.safety(quat)
                if msg:
                    out = out or f'{phase}: {msg}'
                q, kp, kd = ctrl.command(gyro, quat, q_s, dq_s, cmd, dt * (4 if ctrl.mode == 'WALK' else 1))
                # komenda dociera do silników po delay_s (kolejka w czasie, jak w r1_sim cmd_delay_ms)
                queue.append((t + delay_s - 1e-9, q[ctrl.slots], kp[ctrl.slots] * kp_scale, kd[ctrl.slots]))
            ready = None
            while queue and queue[0][0] <= t:
                ready = queue.popleft()
            if ready is not None:
                sim.set_motor_cmd(*ready[1:])
            sim.physics_step()
            if sim.rope_force > 30 and phase not in ('passive', 'fixstand', 'lower', 'stand', 'slack'):
                if not caught:
                    out = out or f'lina złapała w fazie {phase} (t={t:.1f} s)'
                caught = True
            if phase in cmds and t > t_end - dur + 1.5:
                meas[phase].append(sim.base_twist())
            t += dt
            k += 1
        if sim.fallen() and not caught:
            caught = True
    x, y, z, quat = sim.base_pose()
    standing = z > 0.65 and tilt(*quat) < 0.5 and not caught
    track = {p: np.mean(v, axis=0) for p, v in meas.items()}
    return standing, caught, track, out


def current_slots(sim):
    q = np.zeros(35)
    dq = np.zeros(35)
    for slot, qi, dqi in sim.joints():
        q[slot], dq[slot] = qi, dqi
    return q, dq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sim_dir')
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--policy', default='policy.onnx', help='plik polityki w katalogu sim')
    a = ap.parse_args()
    d = os.path.expanduser(a.sim_dir)
    sim = R1PolicySim(f'{d}/scene/scene.xml', f'{d}/{a.policy}', f'{d}/sim_meta.json')
    ctrl = R1PolicyController(f'{d}/{a.policy}')
    grid = [dict()]
    if not a.quick:
        grid += [dict(delay_ms=v) for v in (10, 20, 30, 40, 60)]
        grid += [dict(kp_scale=v) for v in (0.8, 1.2)]
        grid += [dict(friction=v) for v in (0.5, 1.5)]
        grid += [dict(mass=v) for v in (3.0,)]
        grid += [dict(delay_ms=20, kp_scale=0.8, friction=0.5, mass=3.0)]
    print(f'{"zaburzenie":44s} {"stoi":5s} {"lina":5s} {"vx/0.2":>7s} {"vy/0.15":>8s} {"wz/0.4":>7s}  uwagi')
    for g in grid:
        standing, caught, tr, note = scenario(sim, ctrl, **g)
        name = ', '.join(f'{k}={v}' for k, v in g.items()) or 'nominalnie'
        vx = tr.get('walk_x', [0, 0, 0])[0]
        vy = tr.get('walk_y', [0, 0, 0])[1]
        wz = tr.get('turn', [0, 0, 0])[2]
        print(f'{name:44s} {"tak" if standing else "NIE":5s} {"ZŁAP" if caught else "-":5s} {vx:7.2f} {vy:8.2f} {wz:7.2f}  {note or ""}')


if __name__ == '__main__':
    main()
