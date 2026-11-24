#!/usr/bin/env python3
"""W12: trening polityki R1 odpornej na opóźnienie komend (pod sim2real).

Rejestruje zadanie Unitree-R1-Flat-Delay = Unitree-R1-Flat z unitree_rl_mjlab, w którym każdy aktuator jest owinięty
w DelayedActuatorCfg (mjlab): cel pozycji dochodzi do silnika z losowym opóźnieniem 0..max_lag kroków fizyki
(krok 5 ms, max_lag 4 = 20 ms). W naszym teście (robust_lowcmd.py) polityka bez opóźnień w treningu przewracała się
od ok. 35 ms opóźnienia komend, a ta - dopiero od ok. 100 ms.

Uruchom w katalogu unitree_rl_mjlab (to samo środowisko co trening W11):
    python /ścieżka/do/r1_basics/tools/train_delay.py Unitree-R1-Flat-Delay --env.scene.num-envs=4096 \\
        --agent.logger=tensorboard --agent.max-iterations=2200
"""
import os
import sys
from dataclasses import replace

sys.path.insert(0, os.getcwd())                      # pakiet src/ z unitree_rl_mjlab
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
MAX_LAG = int(os.environ.get('R1_MAX_LAG', '4'))     # kroki fizyki po 5 ms

import mjlab.tasks  # noqa: E402,F401
import src.tasks  # noqa: E402,F401
from mjlab.actuator import DelayedActuatorCfg  # noqa: E402
from mjlab.tasks.registry import register_mjlab_task  # noqa: E402
from src.tasks.velocity.config.r1.env_cfgs import unitree_r1_flat_env_cfg  # noqa: E402
from src.tasks.velocity.config.r1.rl_cfg import unitree_r1_ppo_runner_cfg  # noqa: E402
from src.tasks.velocity.rl import VelocityOnPolicyRunner  # noqa: E402


def with_delay(cfg):
    robot = cfg.scene.entities['robot']
    art = robot.articulation
    delayed = tuple(DelayedActuatorCfg(base_cfg=a, delay_target='position', delay_min_lag=0, delay_max_lag=MAX_LAG,
                                       delay_hold_prob=0.9, delay_update_period=0) for a in art.actuators)
    robot.articulation = replace(art, actuators=delayed)
    return cfg


rl = unitree_r1_ppo_runner_cfg()
rl.experiment_name = 'r1_velocity_delay'
register_mjlab_task(task_id='Unitree-R1-Flat-Delay', env_cfg=with_delay(unitree_r1_flat_env_cfg()),
                    play_env_cfg=with_delay(unitree_r1_flat_env_cfg(play=True)), rl_cfg=rl,
                    runner_cls=VelocityOnPolicyRunner)

if __name__ == '__main__':
    import train   # scripts/train.py z unitree_rl_mjlab
    train.main()
