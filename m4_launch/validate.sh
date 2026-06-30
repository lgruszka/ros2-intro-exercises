#!/usr/bin/env bash
# Module 4 exercise validator.
# Uruchamia launch file w tle, sprawdza czy /counter_a i /counter_b są w grafie,
# czy /count_a publikuje.

set -uo pipefail

PKG="intro_demo"
LAUNCH="two_counters.launch.py"

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red()   { printf "\033[31m%s\033[0m\n" "$1"; }
yellow() { printf "\033[33m%s\033[0m\n" "$1"; }

if ! command -v ros2 >/dev/null 2>&1; then
  red "✗ ros2 nie jest w PATH"
  exit 1
fi

if ! ros2 pkg list 2>/dev/null | grep -q "^${PKG}$"; then
  red "✗ pakiet $PKG nie znaleziony."
  red "  cd ~/ros2_ws && colcon build --packages-select $PKG --symlink-install && source install/setup.bash"
  exit 1
fi
green "✓ pakiet $PKG zbudowany"

yellow "▶ startuję $LAUNCH..."
ros2 launch "$PKG" "$LAUNCH" > /tmp/m4_launch.log 2>&1 &
LAUNCH_PID=$!
sleep 5

# /counter_a
if ros2 node list 2>/dev/null | grep -q "^/counter_a$"; then
  green "✓ /counter_a w ros2 node list"
else
  red "✗ /counter_a nie znaleziony — sprawdź TODO 2 w launch file"
  yellow "  Log launch (/tmp/m4_launch.log):"
  tail -10 /tmp/m4_launch.log
  kill "$LAUNCH_PID" 2>/dev/null
  exit 1
fi

# /counter_b
if ros2 node list 2>/dev/null | grep -q "^/counter_b$"; then
  green "✓ /counter_b w ros2 node list"
else
  red "✗ /counter_b nie znaleziony — sprawdź TODO 3 w launch file"
  kill "$LAUNCH_PID" 2>/dev/null
  exit 1
fi

# /monitor
if ros2 node list 2>/dev/null | grep -q "^/monitor$"; then
  green "✓ /monitor w ros2 node list"
else
  red "✗ /monitor nie znaleziony"
  kill "$LAUNCH_PID" 2>/dev/null
  exit 1
fi

# /count_a publikuje?
MSG=$(timeout 4 ros2 topic echo /count_a --once 2>/dev/null || true)
if echo "$MSG" | grep -q "data:"; then
  green "✓ /count_a publikuje wartości"
else
  red "✗ /count_a nie publikuje — sprawdź remapping 'count' → 'count_a'"
  kill "$LAUNCH_PID" 2>/dev/null
  exit 1
fi

kill "$LAUNCH_PID" 2>/dev/null
wait "$LAUNCH_PID" 2>/dev/null

echo ""
green "✓ Module 4 exercise — PASSED"
echo ""
echo "Co dalej:"
echo "  Stretch: dodaj trzeci counter_c z osobnym argumentem name_c"
echo "  Module 5: TF2 i drzewo frames robota"
