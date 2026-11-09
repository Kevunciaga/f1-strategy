"""
track_estimates.py - Average lap 1 slowness and pit stop cost over several races at one track.

One race gives a noisy number (grid order, first-lap incidents, one pit lane
day). Several races at the same track give a steadier one.

Usage (from the project root, inside the venv):
    python src/track_estimates.py Netherlands 2021 2022 2024
"""

import sys

import numpy as np

from data_loader import clean_laps, has_wet_tyres, load_race
from fit_params import estimate_start_and_pit, fit_params


def main(event: str, years: list[int]) -> None:
    rows = []
    print(f"{event}\n")
    print(f"{'year':>4}  {'lap 1':>7}  {'pit stop':>9}  {'cars':>4}  {'stops':>5}")
    for year in years:
        try:
            laps = load_race(year, event)
        except RuntimeError as error:
            print(f"{year:>4}  skipped: could not load ({str(error)[:60]}...)")
            continue
        if has_wet_tyres(laps):
            print(f"{year:>4}  skipped: wet tyres used")
            continue
        try:
            fit = fit_params(clean_laps(laps))
        except ValueError as error:
            print(f"{year:>4}  skipped: {error}")
            continue
        est = estimate_start_and_pit(laps, fit)
        rows.append(est)
        print(f"{year:>4}  {est.start_penalty:6.1f}s  {est.pit_stop_cost:8.1f}s  "
              f"{est.n_start_laps:4d}  {est.n_stops:5d}")

    if not rows:
        print("no usable races")
        return
    start = np.array([r.start_penalty for r in rows])
    pit = np.array([r.pit_stop_cost for r in rows])
    spread = lambda v: v.std(ddof=1) if len(v) > 1 else float("nan")
    print(f"\n{len(rows)} races   lap 1: {start.mean():.1f}s (spread {spread(start):.1f})"
          f"   pit stop: {pit.mean():.1f}s (spread {spread(pit):.1f})")


if __name__ == "__main__":
    main(sys.argv[1], [int(y) for y in sys.argv[2:]])
