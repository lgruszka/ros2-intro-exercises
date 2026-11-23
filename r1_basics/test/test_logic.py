"""Logika bez ROS: geometria, regulator dojazdu, plan ruchu arm_sequence (limity, prędkości, wagi)."""
import math

from r1_basics.arm_sdk import (ARM_JOINTS, build_sequence, effective_limits, safe_limits, START_POSE,
                               WAVE_POSE, weight_to_mode_pr)
from r1_basics.sport_api import velocity_parameter
from r1_basics.util import (holonomic_p_control, integrate_body_velocity, limit_vector, quat_to_yaw,
                            wrap_angle, yaw_to_quat)


def test_angles():
    assert abs(wrap_angle(3 * math.pi) - math.pi) < 1e-9
    for yaw in (-3.0, -1.0, 0.0, 0.5, 3.1):
        assert abs(quat_to_yaw(*yaw_to_quat(yaw)) - yaw) < 1e-9


def test_limit_vector_keeps_direction():
    vx, vy = limit_vector(3.0, 4.0, 0.5)
    assert abs(math.hypot(vx, vy) - 0.5) < 1e-9 and abs(vx / vy - 0.75) < 1e-9
    assert limit_vector(0.1, 0.1, 0.5) == (0.1, 0.1)


def test_p_control_frames():
    # cel 1 m na wprost przy kursie 90 st. (robot patrzy w +y): w ramie robota cel jest po prawej
    vx, vy, wz = holonomic_p_control(1.0, 0.0, math.pi / 2, 0.8, 1.5, 0.3, 0.5)
    assert abs(vx) < 1e-9 and vy < 0 and abs(math.hypot(vx, vy) - 0.3) < 1e-9
    assert wz == -0.5                    # obrót w prawo, przycięty do max_wz
    # blisko celu bez obrotu
    assert holonomic_p_control(0.05, 0.05, 1.0, 0.8, 1.5, 0.3, 0.5)[2] == 0.0


def test_dead_reckoning_step():
    x, y = integrate_body_velocity(0.0, 0.0, math.pi / 2, 1.0, 0.0, 2.0)
    assert abs(x) < 1e-9 and abs(y - 2.0) < 1e-9


def test_velocity_json():
    assert velocity_parameter(0.3, -0.1, 0.25, 0.5) == '{"velocity": [0.3, -0.1, 0.25], "duration": 0.5}'


def test_mode_pr():
    assert [weight_to_mode_pr(w) for w in (-1, 0, 0.29, 0.5, 1.0, 2.0)] == [0, 0, 29, 50, 100, 100]


def test_poses_inside_safe_limits():
    for pose in (START_POSE, WAVE_POSE):
        for j, q in zip(ARM_JOINTS, pose):
            low, high = safe_limits(j)
            assert low <= q <= high, j.name
            assert j.lower < low < 0 < high < j.upper


def run_plan(seed, rate=100.0, max_speed=1.0, **kw):
    segments = build_sequence(seed, max_speed=max_speed, **kw)
    samples = []
    for seg in segments:
        n = int(seg.duration * rate)
        samples += [seg.fn(i / rate) for i in range(n + 1)]
    return segments, samples


def test_plan_weights_speed_and_return():
    seed = [0.1, 0.2, 0.0, 0.4, 0.0, -0.1, -0.2, 0.0, 0.5, 0.0, 0.05, 0.0, 0.0]
    segments, samples = run_plan(seed)
    weights = [w for _, w in samples]
    assert weights[0] == 0.0 and weights[-1] == 0.0 and max(weights) == 1.0
    # rampa wagi monotoniczna na początku i na końcu, bez skoków > 1/100 na próbkę
    assert all(abs(b - a) <= 0.0101 for a, b in zip(weights, weights[1:]))
    # cele: start i koniec = zmierzona poza, prędkość <= 1 rad/s, w limitach
    assert samples[0][0] == seed and max(abs(a - b) for a, b in zip(samples[-1][0], seed)) < 1e-9
    limits = effective_limits(seed)
    for (q0, _), (q1, _) in zip(samples, samples[1:]):
        assert max(abs(b - a) for a, b in zip(q0, q1)) * 100.0 <= 1.0 + 1e-6
    for q, _ in samples:
        assert all(low - 1e-9 <= v <= high + 1e-9 for v, (low, high) in zip(q, limits))
    assert 15.0 < sum(s.duration for s in segments) < 40.0


def test_plan_slow_speed_and_far_seed():
    seed = [-2.0, 1.9, 0.0, 1.9, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]   # ręka daleko, poza 70%
    _, samples = run_plan(seed, max_speed=0.5)
    for (q0, _), (q1, _) in zip(samples, samples[1:]):
        assert max(abs(b - a) for a, b in zip(q0, q1)) * 100.0 <= 0.5 + 1e-6
    low, high = effective_limits(seed)[1]
    assert high == 1.9                  # zmierzona poza poszerza limit, nie jest przycinana
