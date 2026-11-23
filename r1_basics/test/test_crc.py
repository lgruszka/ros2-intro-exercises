"""CRC unitree_hg/LowCmd: port Pythona kontra wzorzec C++ z Unitree.

- test_reference_values: wartości policzone skompilowanym `motor_crc_hg.cpp` z unitree_ros2
  (example/src/src/common) dla wiadomości z `make_case(k)` - patrz docs/qa/r1/r1_verify.md.
- test_against_cpp: kompiluje g++ ten sam plik C++ i porównuje na bieżąco (także na wiadomości,
  którą buduje arm_sequence). Uruchamia się, gdy jest g++ i zmienna UNITREE_ROS2_SRC wskazuje
  katalog repo unitree_ros2 oraz zbudowany pakiet unitree_hg (AMENT_PREFIX_PATH), inaczej skip.
"""
import os
import random
import shutil
import struct
import subprocess
from types import SimpleNamespace

import pytest
from r1_basics.arm_sdk import (ARM_JOINTS, crc32_core, crc32_core_bitwise, hg_lowcmd_bytes, hg_lowcmd_crc,
                               HG_LOWCMD_SIZE, START_POSE, weight_to_mode_pr)

# CRC z C++ (g++ 13.3, aarch64): motor_crc_hg.cpp z unitree_ros2 i crc32_core z unitree_sdk2 crc.h dały
# te same liczby dla make_case(0..3) i arm_case(). 'reserve1' = make_case(1) z reserve[1] = 5: tu
# motor_crc_hg.cpp daje 2636554343 (kopiuje tylko reserve[0]), a SDK crc.h i ten port 2858911040.
REFERENCE = {0: 2308861186, 1: 2636554343, 2: 2911075935, 3: 3324215671, 'arm': 2754177118,
             'reserve1': 2858911040}


def new_msg():
    try:
        from unitree_hg.msg import LowCmd
        return LowCmd()
    except ImportError:          # bez ROS: obiekt z tymi samymi polami
        motor = [SimpleNamespace(mode=0, q=0.0, dq=0.0, tau=0.0, kp=0.0, kd=0.0, reserve=0) for _ in range(35)]
        return SimpleNamespace(mode_pr=0, mode_machine=0, motor_cmd=motor, reserve=[0, 0, 0, 0], crc=0)


def make_case(k):
    """Deterministyczna wiadomość nr k (te same wzory w sterowniku C++ niżej)."""
    msg = new_msg()
    msg.mode_pr = (k * 37) % 101
    msg.mode_machine = k % 7
    for i in range(35):
        m = msg.motor_cmd[i]
        m.mode = (i + k) % 2
        m.q = 0.01 * (i + 1) * (k + 1) - 0.3
        m.dq = -0.002 * i * k
        m.tau = 0.125 * (i % 4) - 0.25
        m.kp = (i % 5) * 10.0 + k
        m.kd = (i % 3) * 0.5
        m.reserve = i * k
    msg.reserve = [k * 1000 + 7, 0, 0, 0]
    return msg


def arm_case():
    """Wiadomość jak z arm_sequence: KP/KD z tabeli, poza startowa, waga 0.73."""
    msg = new_msg()
    for j, q in zip(ARM_JOINTS, START_POSE):
        m = msg.motor_cmd[j.slot]
        m.q, m.kp, m.kd = q, j.kp, j.kd
    msg.mode_pr = weight_to_mode_pr(0.73)
    return msg


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def test_layout_size():
    assert HG_LOWCMD_SIZE == 1004          # jak sizeof(LowCmd) w motor_crc_hg.h i '<2B2x'+... w crc.py
    assert len(hg_lowcmd_bytes(make_case(1))) == 1004


def test_table_equals_bitwise():
    rng = random.Random(7)
    for _ in range(20):
        words = [rng.getrandbits(32) for _ in range(rng.randint(1, 260))]
        assert crc32_core(words) == crc32_core_bitwise(words)


def test_crc_ignores_crc_field():
    msg = make_case(2)
    a = hg_lowcmd_crc(msg)
    msg.crc = 123456
    assert hg_lowcmd_crc(msg) == a


def test_reference_values():
    for k in range(4):
        assert hg_lowcmd_crc(make_case(k)) == REFERENCE[k], f'case {k}'
    assert hg_lowcmd_crc(arm_case()) == REFERENCE['arm']
    msg = make_case(1)
    msg.reserve = [1007, 5, 0, 0]
    assert hg_lowcmd_crc(msg) == REFERENCE['reserve1']


DRIVER = r"""
#include <cstdio>
#include <cstring>
#include <cstdint>
#include "common/motor_crc_hg.h"
// Czyta wiadomości jako tekst (floaty jako bity float32 w hex), liczy get_crc() z motor_crc_hg.cpp.
int main(int argc, char** argv) {
  FILE* f = std::fopen(argv[1], "r");
  unsigned mode_pr, mode_machine;
  while (std::fscanf(f, "%u %u", &mode_pr, &mode_machine) == 2) {
    unitree_hg::msg::LowCmd m;
    m.mode_pr = mode_pr; m.mode_machine = mode_machine;
    for (int i = 0; i < 35; ++i) {
      unsigned mode, res; uint32_t b[5]; float v[5];
      std::fscanf(f, "%u %x %x %x %x %x %u", &mode, &b[0], &b[1], &b[2], &b[3], &b[4], &res);
      std::memcpy(v, b, sizeof(v));
      m.motor_cmd[i].mode = mode; m.motor_cmd[i].q = v[0]; m.motor_cmd[i].dq = v[1];
      m.motor_cmd[i].tau = v[2]; m.motor_cmd[i].kp = v[3]; m.motor_cmd[i].kd = v[4];
      m.motor_cmd[i].reserve = res;
    }
    for (int r = 0; r < 4; ++r) { unsigned x; std::fscanf(f, "%u", &x); m.reserve[r] = x; }
    get_crc(m);
    std::printf("%u\n", m.crc);
  }
  return 0;
}
"""


def dump(msg):
    def bits(x):
        return '%08x' % struct.unpack('<I', struct.pack('<f', x))[0]
    parts = [str(msg.mode_pr), str(msg.mode_machine)]
    for m in msg.motor_cmd:
        parts += [str(m.mode), bits(m.q), bits(m.dq), bits(m.tau), bits(m.kp), bits(m.kd), str(m.reserve)]
    parts += [str(int(r)) for r in msg.reserve]
    return ' '.join(parts)


def include_dirs():
    dirs = []
    for prefix in os.environ.get('AMENT_PREFIX_PATH', '').split(os.pathsep):
        inc = os.path.join(prefix, 'include')
        if os.path.isdir(inc):
            dirs += [os.path.join(inc, d) for d in sorted(os.listdir(inc))
                     if os.path.isdir(os.path.join(inc, d))]
    return dirs


@pytest.mark.skipif(not shutil.which('g++') or not os.environ.get('UNITREE_ROS2_SRC'),
                    reason='potrzebne g++ i UNITREE_ROS2_SRC=<repo unitree_ros2>')
def test_against_cpp(tmp_path):
    example = os.path.join(os.environ['UNITREE_ROS2_SRC'], 'example', 'src')
    # motor_crc_hg.h dołącza rclcpp/rclcpp.hpp, którego get_crc() nie potrzebuje - podmieniamy na pusty
    shim = tmp_path / 'shim' / 'rclcpp'
    shim.mkdir(parents=True)
    (shim / 'rclcpp.hpp').write_text('#pragma once\n')
    (tmp_path / 'driver.cpp').write_text(DRIVER)
    cmd = ['g++', '-std=c++17', '-O1', '-include', 'cstring', '-I', str(tmp_path / 'shim'),
           '-I', os.path.join(example, 'include'), '-I', os.path.join(example, 'include', 'common'),
           '-Wno-unused-result']
    for d in include_dirs():
        cmd += ['-I', d]
    cmd += [str(tmp_path / 'driver.cpp'), os.path.join(example, 'src', 'common', 'motor_crc_hg.cpp'),
            '-o', str(tmp_path / 'driver')]
    subprocess.run(cmd, check=True)

    rng = random.Random(1)
    msgs = [make_case(k) for k in range(4)] + [arm_case()]
    for _ in range(5):                     # losowe wiadomości (reserve[1..3] = 0, patrz niżej)
        msg = make_case(rng.randint(0, 9))
        for m in msg.motor_cmd:
            m.q = f32(rng.uniform(-3.0, 3.0))
        msgs.append(msg)
    (tmp_path / 'msgs.txt').write_text('\n'.join(dump(m) for m in msgs) + '\n')
    out = subprocess.run([str(tmp_path / 'driver'), str(tmp_path / 'msgs.txt')], check=True,
                         capture_output=True, text=True).stdout.split()
    assert [int(x) for x in out] == [hg_lowcmd_crc(m) for m in msgs]
    # Uwaga: motor_crc_hg.cpp kopiuje z msg.reserve tylko 4 bajty (reserve[0]); Python SDK i ten port
    # pakują wszystkie 4 słowa. Przy reserve[1..3] = 0 (zawsze w praktyce) wyniki są identyczne.
