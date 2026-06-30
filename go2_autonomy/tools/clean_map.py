#!/usr/bin/env python3
"""Czyszczenie occupancy grid (mapa ROS) z szumu po SLAM.

Usuwa małe, izolowane skupiska ZAJĘTYCH pikseli (pojedyncze "latające" punkty,
które slam_toolbox losowo zostawia) przez analizę spójnych komponentów: każdy
komponent zajętych pikseli o rozmiarze < --min-size jest zamieniany na wolne
(albo nieznane). Opcjonalnie domyka poszarpane ściany (--close).

Konwencja mapy ROS (negate=0): biały(254)=wolne, czarny(0)=zajęte, szary(205)=nieznane.
Zajętość p liczona z progów occupied_thresh/free_thresh z YAML.

Użycie:
    ./tools/clean_map.py ~/maps/lab_sim.yaml                 # -> lab_sim_clean.{yaml,pgm} + _preview.png
    ./tools/clean_map.py ~/maps/lab_sim.yaml --min-size 8    # ostrzej (usuń większe kleksy)
    ./tools/clean_map.py ~/maps/lab_sim.yaml --close 2       # + domknij ściany 2px
    ./tools/clean_map.py ~/maps/lab_sim.yaml -o ~/maps/lab_sim.yaml   # nadpisz w miejscu

Po wyczyszczeniu:  ./tools/sim_run.sh <out>.yaml
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import yaml
from PIL import Image
from scipy import ndimage


def load_map(yaml_path):
    with open(yaml_path) as f:
        meta = yaml.safe_load(f)
    img_path = meta["image"]
    if not os.path.isabs(img_path):
        img_path = os.path.join(os.path.dirname(os.path.abspath(yaml_path)), img_path)
    img = np.array(Image.open(img_path).convert("L"))
    return meta, img, img_path


def main():
    ap = argparse.ArgumentParser(description="Czyszczenie mapy ROS z szumu.")
    ap.add_argument("map_yaml", help="wejściowy plik mapy .yaml")
    ap.add_argument("-o", "--out", default=None,
                    help="wyjściowy .yaml (domyślnie <in>_clean.yaml; ten sam = nadpisanie)")
    ap.add_argument("--min-size", type=int, default=5,
                    help="min. rozmiar [px] skupiska zajętych do ZACHOWANIA (mniejsze = szum, usuwane). Domyślnie 5.")
    ap.add_argument("--fill", choices=["free", "unknown"], default="free",
                    help="czym zastąpić usunięty szum (domyślnie free)")
    ap.add_argument("--close", type=int, default=0,
                    help="domknięcie morfologiczne [px] na zajętych — łączy poszarpane ściany (0=off)")
    ap.add_argument("--connectivity", type=int, choices=[1, 2], default=2,
                    help="1=4-sąsiedztwo, 2=8-sąsiedztwo (domyślnie 2)")
    ap.add_argument("--no-preview", action="store_true", help="nie zapisuj podglądu PNG")
    args = ap.parse_args()

    if not os.path.isfile(args.map_yaml):
        sys.exit(f"✗ brak pliku: {args.map_yaml}")

    meta, img, img_path = load_map(args.map_yaml)
    occ_thresh = float(meta.get("occupied_thresh", 0.65))
    negate = int(meta.get("negate", 0))

    val = img.astype(np.float32)
    p = val / 255.0 if negate else (255.0 - val) / 255.0   # occupancy probability
    occupied = p > occ_thresh
    n_occ0 = int(occupied.sum())

    # spójne komponenty zajętych pikseli
    struct = ndimage.generate_binary_structure(2, args.connectivity)
    lbl, n = ndimage.label(occupied, structure=struct)
    if n == 0:
        sys.exit("✗ mapa nie ma zajętych pikseli — zły plik?")
    sizes = ndimage.sum(np.ones_like(lbl, dtype=np.int64), lbl, range(1, n + 1))

    # wartość wypełnienia (negate=0: free=254, unknown=205; negate=1: odwrotnie-ish)
    if negate:
        fill_val = 0 if args.fill == "free" else 128
    else:
        fill_val = 254 if args.fill == "free" else 205

    out = img.copy()
    small = np.where(sizes < args.min_size)[0] + 1   # etykiety do usunięcia
    removed_px = 0
    if small.size:
        remove_mask = np.isin(lbl, small)
        removed_px = int(remove_mask.sum())
        out[remove_mask] = fill_val

    # opcjonalne domknięcie ścian (po usunięciu szumu)
    if args.close > 0:
        valc = out.astype(np.float32)
        pc = valc / 255.0 if negate else (255.0 - valc) / 255.0
        occ2 = pc > occ_thresh
        closed = ndimage.binary_closing(occ2, structure=struct, iterations=args.close)
        newly = closed & ~occ2
        out[newly] = 0 if not negate else 254

    n_occ1 = int(((out.astype(np.float32) if negate else (255.0 - out.astype(np.float32))) / 255.0 > occ_thresh).sum())

    # zapis
    out_yaml = args.out or (os.path.splitext(args.map_yaml)[0] + "_clean.yaml")
    out_pgm = os.path.splitext(out_yaml)[0] + ".pgm"
    Image.fromarray(out, mode="L").save(out_pgm)
    new_meta = dict(meta)
    new_meta["image"] = os.path.basename(out_pgm)
    with open(out_yaml, "w") as f:
        yaml.safe_dump(new_meta, f, sort_keys=False)

    # podgląd: usunięte piksele na czerwono na tle oryginału
    if not args.no_preview:
        prev = np.stack([img, img, img], axis=-1).astype(np.uint8)
        if small.size:
            prev[remove_mask] = [255, 0, 0]
        prev_path = os.path.splitext(out_yaml)[0] + "_preview.png"
        Image.fromarray(prev, mode="RGB").save(prev_path)
    else:
        prev_path = "(pominięty)"

    print(f"  mapa:            {os.path.basename(img_path)}  ({img.shape[1]}x{img.shape[0]} px)")
    print(f"  komponenty zajęte: {n} (próg zachowania min-size={args.min_size})")
    print(f"  usunięty szum:   {int(small.size)} skupisk, {removed_px} pikseli")
    print(f"  zajętość:        {n_occ0} -> {n_occ1} px" + (f"  (+domknięcie {args.close}px)" if args.close else ""))
    print(f"  ZAPISANO:        {out_yaml}")
    print(f"                   {out_pgm}")
    print(f"  podgląd (usunięte=czerwone): {prev_path}")
    print(f"  test:            ./tools/sim_run.sh {out_yaml}")


if __name__ == "__main__":
    main()
