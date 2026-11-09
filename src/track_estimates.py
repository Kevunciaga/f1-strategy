"""
track_estimates.py - Average lap 1 slowness and pit stop cost over several races at one track.

One race gives a noisy number (grid order, first-lap incidents, one pit lane
day). Several races at the same track give a steadier one.

Usage (from the project root, inside the venv):
    python src/track_estimates.py Netherlands 2021 2022 2024
"""

import sys

import numpy as np

from dataclasses import dataclass

from data_loader import clean_laps, has_wet_tyres, load_race
from fit_params import RaceEstimates, estimate_start_and_pit, fit_params

# Compound names the fit understands. Older seasons used other names (ultrasoft and so on).
KNOWN_COMPOUND_NAMES = {"SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET", "UNKNOWN", "TEST_UNKNOWN"}


def estimate_track(event: str, years: list[int], verbose: bool = True) -> list[tuple[int, RaceEstimates]]:
    """Estimate lap 1 and pit stop cost for every usable race of `event` in `years`."""
    results = []
    if verbose:
        print(f"{event}")
        print(f"{'year':>4}  {'lap 1':>7}  {'in-lap':>7}  {'out-lap':>8}  {'pit lane':>9}  {'cars':>4}  {'stops':>5}")
    for year in years:
        try:
            laps = load_race(year, event)
        except RuntimeError as error:
            if verbose:
                reason = "wrong event" if "did not take place" in str(error) else "could not load"
                print(f"{year:>4}  skipped: {reason}")
            continue
        if has_wet_tyres(laps):
            if verbose:
                print(f"{year:>4}  skipped: wet tyres used")
            continue
        odd_names = set(laps["Compound"].dropna()) - KNOWN_COMPOUND_NAMES
        if odd_names:
            if verbose:
                print(f"{year:>4}  skipped: unfamiliar tyre names {sorted(odd_names)}")
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
            print(f"{year:>4}  {est.start_penalty:6.1f}s  {est.pit_in_loss:6.1f}s  {est.pit_out_loss:7.1f}s  "
                  f"{est.pit_lane_time:8.1f}s  {est.n_start_laps:4d}  {est.n_stops:5d}")
    return results


@dataclass(frozen=True)
class TrackSummary:
    """Mean over races of each measured number. A race without a value is left out of that mean."""
    start_penalty: float
    pit_in_loss: float
    pit_out_loss: float
    pit_lane_time: float
    start_spread: float
    pit_spread: float   # spread of the total pit stop cost


def summarise(results: list[tuple[int, RaceEstimates]]) -> TrackSummary:
    def column(name: str) -> np.ndarray:
        values = np.array([getattr(est, name) for _, est in results], dtype=float)
        return values[~np.isnan(values)]

    mean = lambda v: float(v.mean()) if len(v) else float("nan")
    spread = lambda v: float(v.std(ddof=1)) if len(v) > 1 else float("nan")
    return TrackSummary(
        start_penalty=mean(column("start_penalty")),
        pit_in_loss=mean(column("pit_in_loss")),
        pit_out_loss=mean(column("pit_out_loss")),
        pit_lane_time=mean(column("pit_lane_time")),
        start_spread=spread(column("start_penalty")),
        pit_spread=spread(np.array([est.pit_stop_cost for _, est in results], dtype=float)),
    )


def main(event: str, years: list[int]) -> None:
    results = estimate_track(event, years)
    if not results:
        print("no usable races")
        return
    t = summarise(results)
    print(f"\n{len(results)} races   lap 1: {t.start_penalty:.1f}s (spread {t.start_spread:.1f})"
          f"   in-lap {t.pit_in_loss:.1f}s   out-lap {t.pit_out_loss:.1f}s"
          f"   pit stop {t.pit_in_loss + t.pit_out_loss:.1f}s (spread {t.pit_spread:.1f})"
          f"   time in pit lane {t.pit_lane_time:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1], [int(y) for y in sys.argv[2:]])
