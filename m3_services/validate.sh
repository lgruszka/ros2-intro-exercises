#!/usr/bin/env bash
# Module 3 exercise validator (service intro_services).
# Uruchamia serwer w tle, wywołuje service przez CLI, sprawdza odpowiedź.

set -uo pipefail

PKG="intro_services"
SRV="/add_two_ints"

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red()   { printf "\033[31m%s\033[0m\n" "$1"; }
yellow() { printf "\033[33m%s\033[0m\n" "$1"; }

if ! command -v ros2 >/dev/null 2>&1; then
  red "✗ ros2 nie jest w PATH. Source /opt/ros/jazzy/setup.bash?"
  exit 1
fi

if ! ros2 pkg list 2>/dev/null | grep -q "^${PKG}$"; then
  red "✗ pakiet $PKG nie znaleziony."
  red "  cd ~/ros2_ws && colcon build --packages-select $PKG && source install/setup.bash"
  exit 1
fi
green "✓ pakiet $PKG zbudowany"

yellow "▶ startuję add_server (twój kod)..."
ros2 run "$PKG" add_server > /tmp/m3_server.log 2>&1 &
SERVER_PID=$!
sleep 3

if ! ros2 service list 2>/dev/null | grep -q "^${SRV}$"; then
  red "✗ $SRV nie pojawił się w grafie"
  yellow "  Log z serwera (/tmp/m3_server.log):"
  tail -5 /tmp/m3_server.log
  kill "$SERVER_PID" 2>/dev/null
  exit 1
fi
green "✓ $SRV widoczny w ros2 service list"

# Wywołaj 2 + 3 = 5
RESULT=$(timeout 5 ros2 service call "$SRV" example_interfaces/srv/AddTwoInts "{a: 2, b: 3}" 2>/dev/null || true)
if echo "$RESULT" | grep -q "sum=5"; then
  green "✓ 2 + 3 = 5 (response prawidłowy)"
else
  red "✗ response niepoprawny:"
  echo "$RESULT"
  yellow "  Sprawdź TODO 2 w add_two_ints_server_skeleton.py (response.sum)"
  kill "$SERVER_PID" 2>/dev/null
  exit 1
fi

# Wywołaj 100 + 200 = 300 dla pewności
RESULT2=$(timeout 5 ros2 service call "$SRV" example_interfaces/srv/AddTwoInts "{a: 100, b: 200}" 2>/dev/null || true)
if echo "$RESULT2" | grep -q "sum=300"; then
  green "✓ 100 + 200 = 300"
else
  red "✗ drugi test niepoprawny"
  echo "$RESULT2"
  kill "$SERVER_PID" 2>/dev/null
  exit 1
fi

kill "$SERVER_PID" 2>/dev/null
wait "$SERVER_PID" 2>/dev/null

echo ""
green "✓ Module 3 exercise (services) — PASSED"
echo ""
echo "Co dalej:"
echo "  Stretch: ros2 run intro_actions fibonacci_server"
echo "  Test:    ros2 action send_goal /fibonacci action_tutorials_interfaces/action/Fibonacci \"{order: 6}\" --feedback"
echo "  Module 4: Launch files + colcon workspace"
