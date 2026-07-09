#!/usr/bin/env bash
# Module 2 exercise validator.
# Uruchamia talker (twój kod) i listener (solution), sprawdza czy wiadomości lecą.
# Wykonuj W SANDBOXIE po colcon build + source.

set -uo pipefail

PKG="intro_pubsub"
TOPIC="/chatter"

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red() { printf "\033[31m%s\033[0m\n" "$1"; }
yellow() { printf "\033[33m%s\033[0m\n" "$1"; }

# 1. Czy ROS2 source'owany?
if ! command -v ros2 >/dev/null 2>&1; then
  red "✗ ros2 nie jest w PATH. Czy source /opt/ros/jazzy/setup.bash?"
  exit 1
fi

# 2. Czy pakiet zbudowany?
if ! ros2 pkg list 2>/dev/null | grep -q "^${PKG}$"; then
  red "✗ pakiet $PKG nie znaleziony."
  red "  Sprawdź: cd ~/ros2_ws && colcon build --packages-select $PKG && source install/setup.bash"
  exit 1
fi
green "✓ pakiet $PKG zbudowany"

# 3. Uruchom talker (twój skeleton) w tle
yellow "▶ startuję talker (twój kod)..."
ros2 run "$PKG" talker > /tmp/m2_talker.log 2>&1 &
TALKER_PID=$!
sleep 3

# 4. Sprawdź czy talker publikuje
PUB_COUNT=$(timeout 4 ros2 topic echo "$TOPIC" --once 2>/dev/null | grep -c "data:" || echo "0")

# 5. Sprzątanie
kill "$TALKER_PID" 2>/dev/null
wait "$TALKER_PID" 2>/dev/null

if [[ "$PUB_COUNT" -gt 0 ]]; then
  green "✓ talker publikuje na $TOPIC"
else
  red "✗ talker nie publikuje. Sprawdź TODO 1, 2, 3 w talker_skeleton.py"
  yellow "  Log talkera (/tmp/m2_talker.log):"
  tail -10 /tmp/m2_talker.log
  exit 1
fi

green ""
green "✓ Module 2 exercise — PASSED"
green ""
echo "Co dalej:"
echo "  1. Stretch: zamień std_msgs/String na geometry_msgs/Twist"
echo "  2. Sprawdź QoS w Foxglove: ros2 topic info -v $TOPIC"
echo "  3. Przejdź do Modułu 3 (Services & Actions)"
