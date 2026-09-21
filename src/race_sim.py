"""
race_sim.py — F1 race strategy simulator using the fitted TyreModel.

Usage
-----
# Quick run with fitted model:
    python race_sim.py

# The simulator can:
    - Simulate a single strategy and return total race time
    - Brute-force search for the optimal 1-stop or 2-stop strategy
"""

import itertools
import sys
from pathlib import Path

import fastf1
import numpy as np
import pandas as pd

# Import our tyre model
sys.path.insert(0, str(Path(__file__).parent))
from tyre_model import TyreModel, COMPOUNDS

fastf1.Cache.enable_cache(str(Path(__file__).parent.parent / "cache"))


# ---------------------------------------------------------------------------
# Base pace from FastF1
# ---------------------------------------------------------------------------

def get_base_pace(year: int, gp: str, driver: str = "VER") -> float:
    """
    Return an estimated base pace (seconds) for a driver at a GP.

    Uses the fastest 20% of the driver's clean laps as a proxy for
    the reference pace that the TyreModel deltas are added on top of.
    """
    session = fastf1.get_session(year, gp, "R")
    session.load(laps=True, telemetry=False, weather=False, messages=False)

    laps = session.laps.pick_drivers(driver)
    laps = laps[laps["LapTime"].notna()]
    laps = laps[laps["IsAccurate"] == True]

    lap_times = laps["LapTime"].dt.total_seconds().sort_values()
    top_20pct = lap_times.iloc[: max(1, len(lap_times) // 5)]
    return float(top_20pct.mean())


# ---------------------------------------------------------------------------
# Race simulator
# ---------------------------------------------------------------------------

PIT_LOSS = 21.5   # seconds lost per pit stop (stationary + out-lap delta)


def simulate_race(
    base_pace: float,
    num_laps: int,
    pit_laps: tuple[int, ...],
    compounds: tuple[str, ...],
    tyre_model: TyreModel,
    start_tyre_age: int = 0,
) -> dict:
    """
    Simulate a race and return timing breakdown.

    Args:
        base_pace:       reference lap time in seconds (clean pace)
        num_laps:        total race laps
        pit_laps:        lap numbers at which pit stops occur, e.g. (15, 35)
        compounds:       compound for each stint, length = len(pit_laps) + 1
                         e.g. ("SOFT", "MEDIUM", "HARD")
        tyre_model:      fitted TyreModel instance
        start_tyre_age:  tyre age at race start (0 = new, >0 = used set)

    Returns:
        dict with keys: total_time, lap_times, tyre_ages, compounds_used
    """
    if len(compounds) != len(pit_laps) + 1:
        raise ValueError(
            f"Need {len(pit_laps) + 1} compounds for {len(pit_laps)} pit stops, "
            f"got {len(compounds)}"
        )

    # Build stint schedule: list of (stint_start_lap, compound, start_tyre_age)
    stints = []
    stint_starts = [1] + [p + 1 for p in pit_laps]
    stint_ends   = list(pit_laps) + [num_laps]
    ages_at_start = [start_tyre_age] + [0] * len(pit_laps)

    for i, (s, e, c, a) in enumerate(zip(stint_starts, stint_ends, compounds, ages_at_start)):
        stints.append({"start": s, "end": e, "compound": c.upper(), "start_age": a})

    # Build per-lap lookup of (compound, tyre_age)
    lap_compound = {}
    lap_age = {}
    for stint in stints:
        for lap in range(stint["start"], stint["end"] + 1):
            lap_compound[lap] = stint["compound"]
            lap_age[lap] = stint["start_age"] + (lap - stint["start"])

    total_time = 0.0
    lap_times  = []

    for lap in range(1, num_laps + 1):
        compound = lap_compound[lap]
        age      = lap_age[lap]

        deg_delta = tyre_model.predict(compound, age)
        lap_time  = base_pace + deg_delta

        # Add pit stop time loss on the lap the car pits
        if lap in pit_laps:
            lap_time += PIT_LOSS

        total_time += lap_time
        lap_times.append(lap_time)

    return {
        "total_time":    total_time,
        "lap_times":     np.array(lap_times),
        "tyre_ages":     np.array([lap_age[l] for l in range(1, num_laps + 1)]),
        "compounds_used": [lap_compound[l] for l in range(1, num_laps + 1)],
        "pit_laps":      pit_laps,
        "compounds":     compounds,
    }


def format_time(seconds: float) -> str:
    """Format seconds into H:MM:SS.mmm"""
    h  = int(seconds // 3600)
    m  = int((seconds % 3600) // 60)
    s  = seconds % 60
    return f"{h}:{m:02d}:{s:06.3f}"


# ---------------------------------------------------------------------------
# Strategy optimiser — brute-force grid search
# ---------------------------------------------------------------------------

def optimise_strategy(
    base_pace: float,
    num_laps: int,
    tyre_model: TyreModel,
    num_stops: int = 1,
    search_window: tuple[int, int] | None = None,
    allowed_compounds: tuple[str, ...] | None = None,
    mandatory_two_compounds: bool = True,
) -> dict:
    """
    Brute-force search for the optimal pit strategy.

    Args:
        base_pace:             reference lap time in seconds
        num_laps:              total race laps
        tyre_model:            fitted TyreModel
        num_stops:             1 or 2 stops
        search_window:         (earliest_pit, latest_pit) lap range to search
                               defaults to (5, num_laps - 5)
        allowed_compounds:     which compounds to consider
        mandatory_two_compounds: F1 rule — must use at least 2 different compounds

    Returns:
        dict with best strategy and its total_time.
    """
    if allowed_compounds is None:
        allowed_compounds = tuple(tyre_model.compounds_available())
    if search_window is None:
        search_window = (5, num_laps - 5)
    lo, hi = search_window

    best = {"total_time": float("inf")}

    if num_stops == 1:
        pit_candidates = range(lo, hi + 1)
        compound_options = list(itertools.product(allowed_compounds, repeat=2))
        if mandatory_two_compounds:
            compound_options = [c for c in compound_options if c[0] != c[1]]

        for pit in pit_candidates:
            for compounds in compound_options:
                result = simulate_race(base_pace, num_laps, (pit,), compounds, tyre_model)
                if result["total_time"] < best["total_time"]:
                    best = result

    elif num_stops == 2:
        # Only search every 3rd lap to keep runtime manageable
        step = 3
        pit_candidates = range(lo, hi + 1, step)
        compound_options = list(itertools.product(allowed_compounds, repeat=3))
        if mandatory_two_compounds:
            compound_options = [c for c in compound_options if len(set(c)) >= 2]

        for pit1 in pit_candidates:
            for pit2 in range(pit1 + step, hi + 1, step):
                for compounds in compound_options:
                    result = simulate_race(
                        base_pace, num_laps, (pit1, pit2), compounds, tyre_model
                    )
                    if result["total_time"] < best["total_time"]:
                        best = result

    else:
        raise ValueError("num_stops must be 1 or 2")

    return best


# ---------------------------------------------------------------------------
# Main — example run on Monza 2023
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    YEAR    = 2023
    GP      = "Monza"
    DRIVER  = "VER"
    NUM_LAPS = 53

    # --- load or fit tyre model ---
    cache_dir   = str(Path(__file__).parent.parent / "cache")
    params_path = Path(__file__).parent / "tyre_params.json"
    track_path  = Path(__file__).parent / f"tyre_params_{YEAR}_{GP.replace(' ', '_')}.json"

    # Prefer a track-specific model; fall back to cross-track, then fit fresh
    if track_path.exists():
        print(f"Loading track-specific model from {track_path}")
        model = TyreModel.load(str(track_path))
    else:
        fallback = TyreModel.load(str(params_path)) if params_path.exists() else None
        print(f"Fitting track-specific model for {YEAR} {GP}...")
        model = TyreModel()
        model.fit_track(YEAR, GP, cache_dir=cache_dir, fallback=fallback)
        model.save(str(track_path))
        if not params_path.exists():
            print("No cross-track model found — run tyre_model.py to build one.")

    print()
    print(model.summary())

    # --- get base pace ---
    print(f"\nFetching base pace for {DRIVER} at {YEAR} {GP}...")
    base_pace = get_base_pace(YEAR, GP, DRIVER)
    print(f"Base pace: {base_pace:.3f}s ({format_time(base_pace)} per lap)")

    # --- simulate a specific strategy ---
    print("\n--- Single strategy simulation ---")
    result = simulate_race(
        base_pace  = base_pace,
        num_laps   = NUM_LAPS,
        pit_laps   = (18, 38),
        compounds  = ("MEDIUM", "HARD", "MEDIUM"),
        tyre_model = model,
    )
    print(f"Strategy: {result['compounds']}  pits: {result['pit_laps']}")
    print(f"Total time: {format_time(result['total_time'])}")

    # --- optimise 1-stop ---
    print("\n--- Optimising 1-stop strategy ---")
    best_1 = optimise_strategy(base_pace, NUM_LAPS, model, num_stops=1)
    print(f"Best 1-stop: {best_1['compounds']}  pits: {best_1['pit_laps']}")
    print(f"Total time:  {format_time(best_1['total_time'])}")

    # --- optimise 2-stop ---
    print("\n--- Optimising 2-stop strategy ---")
    best_2 = optimise_strategy(base_pace, NUM_LAPS, model, num_stops=2)
    print(f"Best 2-stop: {best_2['compounds']}  pits: {best_2['pit_laps']}")
    print(f"Total time:  {format_time(best_2['total_time'])}")

    # Compare
    print(f"\n1-stop advantage: {format_time(best_2['total_time'] - best_1['total_time'])}")
