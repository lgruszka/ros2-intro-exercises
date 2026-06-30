#!/usr/bin/env bash
# Wspólny env dla pracy z Go2 — SOURCE'uj w KAŻDYM terminalu (nie uruchamiaj):
#   source tools/go2_env.sh
#
# Ustawia: workspace + CycloneDDS pod sieć robota + restart daemona DDS.
# Dostosuj GO2_WS jeśli Twój workspace jest gdzie indziej:
#   GO2_WS=~/moj_ws source tools/go2_env.sh

GO2_WS="${GO2_WS:-$HOME/go2_ws}"

source /opt/ros/jazzy/setup.bash
# shellcheck disable=SC1091
source "$GO2_WS/install/setup.bash" 2>/dev/null || {
  echo "[go2_env] BŁĄD: brak $GO2_WS/install/setup.bash — zbuduj ws (colcon build) albo ustaw GO2_WS"; return 1 2>/dev/null || exit 1; }

# DDS pod sieć robota. Config instaluje się z go2_bringup (ustaw w nim interfejs!).
export CYCLONEDDS_URI="$(ros2 pkg prefix go2_bringup 2>/dev/null)/share/go2_bringup/config/cyclonedds_go2.xml"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# Po przełączeniu DDS (sim<->go2) zawsze restart daemona — #1 przyczyna "nie widać topiców".
ros2 daemon stop 2>/dev/null; sleep 1

echo "[go2_env] WS=$GO2_WS RMW=$RMW_IMPLEMENTATION"
echo "[go2_env] CYCLONEDDS_URI=$CYCLONEDDS_URI"
