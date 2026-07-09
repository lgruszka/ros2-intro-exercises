#!/usr/bin/env bash
# Module 0 smoke test validator.
# Sprawdza że ROS2 jest sourcowany, talker działa, /chatter widoczny w grafie.

set -uo pipefail

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red()   { printf "\033[31m%s\033[0m\n" "$1"; }
yellow() { printf "\033[33m%s\033[0m\n" "$1"; }

# ── 1. Czy ros2 jest w PATH? ────────────────────────────────────────────
if ! command -v ros2 >/dev/null 2>&1; then
  red "✗ ros2 nie jest w PATH."
  red "  Czy source /opt/ros/jazzy/setup.bash?"
  exit 1
fi
green "✓ ros2 dostępny"

# ── 2. ros2 doctor ──────────────────────────────────────────────────────
DOC_OUT=$(ros2 doctor --report 2>&1 || true)
if echo "$DOC_OUT" | grep -qi "error"; then
  red "✗ ros2 doctor zgłasza error:"
  echo "$DOC_OUT" | grep -i "error" | head -5
  exit 1
fi
green "✓ ros2 doctor — środowisko OK"

# ── 3. Domain ID set? ───────────────────────────────────────────────────
echo "  ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}"

# ── 4. Uruchom talker w tle ─────────────────────────────────────────────
yellow "▶ startuję talker w tle..."
ros2 run demo_nodes_cpp talker > /tmp/m0_talker.log 2>&1 &
TALKER_PID=$!
sleep 3

# ── 5. Sprawdź czy talker widoczny ──────────────────────────────────────
if ros2 node list 2>/dev/null | grep -q "/talker"; then
  green "✓ talker widoczny w ros2 node list"
else
  red "✗ talker nie został wykryty w ros2 node list"
  kill "$TALKER_PID" 2>/dev/null
  exit 1
fi

# ── 6. Sprawdź /chatter ─────────────────────────────────────────────────
if ros2 topic list 2>/dev/null | grep -q "^/chatter$"; then
  green "✓ /chatter widoczny w ros2 topic list"
else
  red "✗ /chatter nie znaleziony"
  kill "$TALKER_PID" 2>/dev/null
  exit 1
fi

# ── 7. Echo — czytamy 1 wiadomość ───────────────────────────────────────
MSG=$(timeout 5 ros2 topic echo /chatter --once 2>/dev/null || true)
if [[ -n "$MSG" ]] && echo "$MSG" | grep -q "data:"; then
  green "✓ ros2 topic echo /chatter — odbieramy wiadomości"
else
  red "✗ Nie odebraliśmy żadnej wiadomości z /chatter"
  kill "$TALKER_PID" 2>/dev/null
  exit 1
fi

# ── 8. Cleanup ──────────────────────────────────────────────────────────
kill "$TALKER_PID" 2>/dev/null
wait "$TALKER_PID" 2>/dev/null

echo ""
green "✓ Module 0 smoke test — PASSED"
echo ""
echo "Co dalej:"
echo "  → Module 1: napiszesz pierwszy własny node Pythonem"
echo "  → exercises/m1_hello_node/"
