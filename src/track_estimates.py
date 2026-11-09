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
from fit_params import RaceEstimates, estimate_start_and_pit, fit_params


def estimate_track(event: str, years: list[int], verbose: bool = True) -> list[tuple[int, RaceEstimates]]:
    """Estimate lap 1 and pit stop cost for every usable race of `event` in `years`."""
    results = []
    if verbose:
        print(f"{event}")
        print(f"{'year':>4}  {'lap 1':>7}  {'pit stop':>9}  {'cars':>4}  {'stops':>5}")
    for year in years:
        try:
            laps = load_race(year, event)
        except RuntimeError as error:
            if verbose:
                print(f"{year:>4}  skipped: could not load")
            continue
        if has_wet_tyres(laps):
            if verbose:
                print(f"{year:>4}  skipped: wet tyres used")
            continue
        try:
            fit = fit_params(clean_laps(laps))
        except ValueError as error:
            if verbose:
                print(f"{year:>4}  skipped: {error}")
            continue
        est = estimate_start_and_pit(laps, fit)
        results.append((year, est))
        if verbose:
            print(f"{year:>4}  {est.start_penalty:6.1f}s  {est.pit_stop_cost:8.1f}s  "
                  f"{est.n_start_laps:4d}  {est.n_stops:5d}")
    return results


def summarise(results: list[tuple[int, RaceEstimates]]) -> tuple[float, float, float, float]:
    """Mean and spread of lap 1 and pit stop cost over races. Races without a value are left out."""
    start = np.array([est.start_penalty for _, est in results], dtype=float)
    pit = np.array([est.pit_stop_cost for _, est in results], dtype=float)
    start, pit = start[~np.isnan(start)], pit[~np.isnan(pit)]
    spread = lambda v: float(v.std(ddof=1)) if len(v) > 1 else float("nan")
    return (float(start.mean()) if len(start) else float("nan"), spread(start),
            float(pit.mean()) if len(pit) else float("nan"), spread(pit))


def main(event: str, years: list[int]) -> None:
    results = estimate_track(event, years)
    if not results:
        print("no usable races")
        return
    start, start_spread, pit, pit_spread = summarise(results)
    print(f"\n{len(results)} races   lap 1: {start:.1f}s (spread {start_spread:.1f})"
          f"   pit stop: {pit:.1f}s (spread {pit_spread:.1f})")


if __name__ == "__main__":
    main(sys.argv[1], [int(y) for y in sys.argv[2:]])
