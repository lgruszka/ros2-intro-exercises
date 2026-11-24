#!/usr/bin/env bash
# W11: pobiera siatki R1 (unitree_rl_mjlab, Apache-2.0, © Unitree Robotics) do sim/scene/assets/robot,
# żeby r1_sim mógł wczytać dołączoną scenę sim/scene/scene.xml bez własnego treningu.
set -euo pipefail
DEST="$(cd "$(dirname "$0")/.." && pwd)/sim/scene/assets/robot"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
git clone -q --depth 1 --filter=blob:none --sparse https://github.com/unitreerobotics/unitree_rl_mjlab.git "$TMP/m"
git -C "$TMP/m" sparse-checkout set src/assets/robots/unitree_r1/xmls/assets
mkdir -p "$DEST"
cp "$TMP/m/src/assets/robots/unitree_r1/xmls/assets/"* "$DEST/"
echo "siatki R1: $(ls "$DEST" | wc -l) plików w $DEST"
