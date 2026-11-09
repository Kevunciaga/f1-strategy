"""
evaluate.py - How well does the model predict real race times it was not fitted on?

Every race is tested with numbers taken from OTHER races only:
- tyre and fuel numbers: the mean over other fitted races, either at the same
  track or at all tracks
- start, in-lap and out-lap losses: the mean over other races at the same track
  (recomputed without the test race, so nothing leaks)

2021 to 2025 races are tested leave-one-race-out. 2026 races are tested against
everything from 2021 to 2025: the model never sees them when it is fitted.

One known limit: each driver's base pace is calibrated from their own clean laps
in the test race, like a strategist who knows the car's pace from practice.
Everything else is out-of-sample.

Usage (from the project root, inside the venv):
    python src/evaluate.py
"""

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from build_track_table import MAIN_YEARS, NEW_REGS_YEARS, TRACKS
from data_loader import (clean_laps, driver_race_time, driver_strategy,
                         has_wet_tyres, load_race)
from fit_params import COMPOUNDS, FitResult, RaceEstimates, estimate_start_and_pit, fit_params
from fuel_model import fuel_penalty
from params import DEFAULT_PARAMS, Params
from race_predictor import predict_race_time
from track_estimates import KNOWN_COMPOUND_NAMES
from tyre_model import tyre_penalty

TARGET_SECONDS = 30.0


@dataclass(frozen=True)
class RaceData:
    track: str
    year: int
    laps: pd.DataFrame
    clean: pd.DataFrame
    fit: FitResult
    estimates: RaceEstimates


def load_races(tracks: dict[str, str], years: tuple[int, ...]) -> list[RaceData]:
    """Load every usable dry race. Skipped races are listed with the reason."""
    races = []
    for name, event in tracks.items():
        for year in years:
            try:
                laps = load_race(year, event)
            except RuntimeError:
                print(f"  skipped {name} {year}: could not load")
                continue
            if has_wet_tyres(laps) or set(laps["Compound"].dropna()) - KNOWN_COMPOUND_NAMES:
                print(f"  skipped {name} {year}: wet or unfamiliar tyres")
                continue
            clean = clean_laps(laps)
            try:
                fit = fit_params(clean)
            except ValueError as error:
                print(f"  skipped {name} {year}: {error}")
                continue
            races.append(RaceData(name, year, laps, clean, fit, estimate_start_and_pit(laps, fit)))
    return races


def _mean(values) -> float:
    values = np.array(values, dtype=float)
    values = values[~np.isnan(values)]
    return float(values.mean()) if len(values) else float("nan")


def average_tyre_fuel_params(fits: list[FitResult], template: Params = DEFAULT_PARAMS) -> Params:
    """Mean degradation, compound offsets and fuel effect over several fitted races."""
    return replace(
        template,
        degradation_per_lap={c: _mean([f.params.degradation_per_lap[c] for f in fits]) for c in COMPOUNDS},
        fresh_pace_offset={c: _mean([f.params.fresh_pace_offset[c] for f in fits]) for c in COMPOUNDS},
        seconds_per_kg=_mean([f.params.seconds_per_kg for f in fits]),
    )


def average_track_losses(estimates: list[RaceEstimates], fallback: list[RaceEstimates]) -> tuple[float, float, float]:
    """Mean start, in-lap and out-lap loss. A value missing everywhere in `estimates` comes from `fallback`."""
    result = []
    for name in ("start_penalty", "pit_in_loss", "pit_out_loss"):
        value = _mean([getattr(e, name) for e in estimates])
        result.append(value if value == value else _mean([getattr(e, name) for e in fallback]))
    return tuple(result)


def zero_tyre_and_fuel(params: Params) -> Params:
    """The baseline: no tyre wear, no compound offsets, no fuel effect."""
    return replace(
        params,
        degradation_per_lap={c: 0.0 for c in COMPOUNDS},
        fresh_pace_offset={c: 0.0 for c in COMPOUNDS},
        seconds_per_kg=0.0,
    )


def calibrate_base(params: Params, clean_driver_laps: pd.DataFrame) -> float:
    """A driver's pace: mean of (lap time - tyre penalty - fuel penalty) over their clean laps."""
    penalties = [tyre_penalty(params, c, int(a)) + fuel_penalty(params, int(l) - 1)
                 for c, a, l in zip(clean_driver_laps["Compound"], clean_driver_laps["TyreAge"],
                                    clean_driver_laps["LapNumber"])]
    return float(np.mean(clean_driver_laps["LapTimeSec"].to_numpy() - np.array(penalties)))


def neutralised_laps(race: RaceData) -> int:
    """Number of race laps run under Safety Car, VSC or red flag (for most of the field)."""
    status = race.laps["TrackStatus"].astype(str).apply(lambda t: bool(set("4567") & set(t)))
    return int((status.groupby(race.laps["LapNumber"]).mean() > 0.5).sum())


def eligible_drivers(race: RaceData) -> list[str]:
    """Drivers who finished within 3 laps of the winner and have at least 20 clean laps."""
    race_laps = race.laps["LapNumber"].max()
    return [d for d in sorted(race.laps["Driver"].unique())
            if (race.laps["Driver"] == d).sum() >= race_laps - 3 and (race.clean["Driver"] == d).sum() >= 20]


def race_errors(params: Params, race: RaceData) -> np.ndarray:
    """Predicted minus real race time, in seconds, for every eligible driver."""
    errors = []
    for driver in eligible_drivers(race):
        driver_laps = race.laps[race.laps["Driver"] == driver].sort_values("LapNumber")
        base = calibrate_base(params, race.clean[race.clean["Driver"] == driver])
        predicted, _, _ = predict_race_time(replace(params, base_lap_time=base), len(driver_laps),
                                            driver_strategy(driver_laps))
        errors.append(predicted - driver_race_time(driver_laps))
    return np.array(errors)


def build_params(test: RaceData, train: list[RaceData], same_track: bool) -> Params:
    """Params for predicting `test` using only the races in `train`."""
    track_races = [r for r in train if r.track == test.track]
    fit_source = track_races if same_track and track_races else train
    params = average_tyre_fuel_params([r.fit for r in fit_source])
    start, in_loss, out_loss = average_track_losses([r.estimates for r in track_races],
                                                    [r.estimates for r in train])
    return replace(params, start_penalty=start, pit_in_loss=in_loss, pit_out_loss=out_loss)


def evaluate_race(test: RaceData, train: list[RaceData]) -> dict[str, np.ndarray]:
    """Errors of the three variants for one test race."""
    same = build_params(test, train, same_track=True)
    every = build_params(test, train, same_track=False)
    return {
        "same track": race_errors(same, test),
        "all tracks": race_errors(every, test),
        "baseline": race_errors(zero_tyre_and_fuel(same), test),
    }


def summarise_errors(errors: np.ndarray) -> str:
    return (f"mean {errors.mean():+6.1f}  MAE {np.abs(errors).mean():5.1f}  worst {np.abs(errors).max():5.1f}  "
            f"within {TARGET_SECONDS:.0f}s {100 * np.mean(np.abs(errors) <= TARGET_SECONDS):3.0f}%")


def main() -> None:
    print("Loading races (cached)...")
    fit_races = load_races(TRACKS, MAIN_YEARS)
    test_races = load_races(TRACKS, NEW_REGS_YEARS)
    print(f"{len(fit_races)} races 2021-2025, {len(test_races)} races 2026\n")
    print("SC laps = laps run under Safety Car, VSC or red flag. The model has no Safety Car (Goal 3),\n"
          "so races with SC laps are expected to miss.\n")

    groups = {
        "2021-2025, leave one race out": (fit_races, fit_races),
        "2026, fitted on 2021-2025": (test_races, fit_races),
    }
    collected = {}   # (group, "no SC" or "with SC") -> list of error dicts
    print(f"{'race':18} {'drv':>3} {'SC laps':>7} | {'same-track MAE':>14} {'worst':>6} | {'all-tracks MAE':>14} | {'baseline MAE':>12}")
    for label, (tests, pool) in groups.items():
        for race in tests:
            train = [r for r in pool if r is not race]
            if not train:
                continue
            out = evaluate_race(race, train)
            sc_laps = neutralised_laps(race)
            collected.setdefault((label, "no SC laps" if sc_laps == 0 else "with SC laps"), []).append(out)
            print(f"{race.track + ' ' + str(race.year):18} {len(out['same track']):3d} {sc_laps:7d} | "
                  f"{np.abs(out['same track']).mean():14.1f} {np.abs(out['same track']).max():6.1f} | "
                  f"{np.abs(out['all tracks']).mean():14.1f} | {np.abs(out['baseline']).mean():12.1f}")
        print()

    for (label, kind), outs in collected.items():
        print(f"{label}: races {kind} ({len(outs)} races)")
        for variant in ("same track", "all tracks", "baseline"):
            print(f"  {variant:11} {summarise_errors(np.concatenate([o[variant] for o in outs]))}")
        print()


if __name__ == "__main__":
    main()
