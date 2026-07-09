#!/usr/bin/env bash
# Module 1 exercise validator.
# Uruchamia hello node (twój kod) w tle, sprawdza czy /hello pojawia się
# w grafie i czy publikuje na /rosout.

set -uo pipefail

PKG="intro_node"
NODE="/hello"

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red()   { printf "\033[31m%s\033[0m\n" "$1"; }
yellow() { printf "\033[33m%s\033[0m\n" "$1"; }

# 1. ros2 w PATH?
if ! command -v ros2 >/dev/null 2>&1; then
  red "✗ ros2 nie jest w PATH. Source /opt/ros/jazzy/setup.bash?"
  exit 1
fi

# 2. Pakiet zbudowany?
if ! ros2 pkg list 2>/dev/null | grep -q "^${PKG}$"; then
  red "✗ pakiet $PKG nie znaleziony."
  red "  Sprawdź: cd ~/ros2_ws && colcon build --packages-select $PKG && source install/setup.bash"
  exit 1
fi
green "✓ pakiet $PKG zbudowany"

# 3. Uruchom hello w tle
yellow "▶ startuję hello node (twój kod)..."
ros2 run "$PKG" hello > /tmp/m1_hello.log 2>&1 &
HELLO_PID=$!
sleep 3

# 4. /hello widoczny w grafie?
if ros2 node list 2>/dev/null | grep -q "^${NODE}$"; then
  green "✓ $NODE widoczny w ros2 node list"
else
  red "✗ $NODE nie wykryty"
  yellow "  Log z hello (/tmp/m1_hello.log):"
  tail -5 /tmp/m1_hello.log
  kill "$HELLO_PID" 2>/dev/null
  exit 1
fi

# 5. Czy publikuje na /rosout? (to znaczy że TODO 2 zostało zrobione)
ROSOUT_MSG=$(timeout 4 ros2 topic echo /rosout --once 2>/dev/null | grep -E "name: hello|alive" | head -1)
if [[ -n "$ROSOUT_MSG" ]]; then
  green "✓ logi z $NODE widoczne na /rosout"
else
  red "✗ Nie widzimy logów z $NODE na /rosout."
  red "  Sprawdź czy w tick() wywołujesz self.get_logger().info(...)"
  yellow "  Log z hello (/tmp/m1_hello.log):"
  tail -5 /tmp/m1_hello.log
  kill "$HELLO_PID" 2>/dev/null
  exit 1
fi

# 6. Cleanup
kill "$HELLO_PID" 2>/dev/null
wait "$HELLO_PID" 2>/dev/null

echo ""
green "✓ Module 1 exercise — PASSED"
echo ""
echo "Co dalej:"
echo "  1. Stretch: zmień severity na warn, dodaj throttle_duration_sec"
echo "  2. Module 2: pierwsza komunikacja publisher/subscriber"
echo "     → exercises/m2_pub_sub/"
