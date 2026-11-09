"""
fit_params.py - Fit the model's Params from the clean laps of one race.

Ported from learning notebook 03. One least-squares fit over every clean lap:

    lap time = driver pace + compound offset
               + degradation[compound] * tyre age + c * lap number

Driver pace is fitted per driver. Offsets are relative to SOFT. The fuel effect
c is shared by all drivers and converted to seconds per kg with the burn rate in
Params.
"""

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from fuel_model import fuel_penalty
from params import DEFAULT_PARAMS, Params
from tyre_model import tyre_penalty

COMPOUNDS = ("SOFT", "MEDIUM", "HARD")


@dataclass(frozen=True)
class FitResult:
    params: Params                          # base_lap_time is the mean over drivers
    driver_base_lap_time: dict[str, float]  # base_lap_time per driver
    std_errors: dict[str, float]            # uncertainty of each fitted coefficient
    noise: float                            # std of the left-over lap time error, seconds


def fit_params(clean: pd.DataFrame, template: Params = DEFAULT_PARAMS) -> FitResult:
    """Fit fresh_pace_offset, degradation_per_lap, seconds_per_kg and base pace.

    `clean` needs the columns Driver, Compound, TyreAge, LapNumber, LapTimeSec.
    Everything not fitted (pit loss, fuel load, burn rate, puncture rule) is
    copied from `template`.
    """
    missing = [c for c in COMPOUNDS if c not in set(clean["Compound"])]
    if missing:
        raise ValueError(f"No clean laps on {missing}, cannot fit those compounds")

    drivers = sorted(clean["Driver"].unique())
    columns, names = [], []
    for driver in drivers:
        columns.append((clean["Driver"] == driver).to_numpy(dtype=float))
        names.append(f"base_{driver}")
    for compound in COMPOUNDS[1:]:
        columns.append((clean["Compound"] == compound).to_numpy(dtype=float))
        names.append(f"offset_{compound}")
    for compound in COMPOUNDS:
        columns.append(((clean["Compound"] == compound) * clean["TyreAge"]).to_numpy(dtype=float))
        names.append(f"deg_{compound}")
    columns.append(clean["LapNumber"].to_numpy(dtype=float))
    names.append("lap")

    X = np.column_stack(columns)
    y = clean["LapTimeSec"].to_numpy(dtype=float)
    if np.linalg.matrix_rank(X) < X.shape[1]:
        raise ValueError("Input columns are redundant: not enough variety in pit laps or compounds")

    theta = np.linalg.solve(X.T @ X, X.T @ y)
    residuals = y - X @ theta
    noise_var = residuals @ residuals / (len(y) - X.shape[1])
    std_errors = np.sqrt(np.diag(noise_var * np.linalg.inv(X.T @ X)))

    coef = dict(zip(names, theta))
    seconds_per_kg = -coef["lap"] / template.fuel_burn_per_lap

    # model fuel penalty at lap L is k * (load0 - burn * (L - 1)), so its constant part is k * (load0 + burn)
    fuel_constant = seconds_per_kg * (template.initial_fuel_load + template.fuel_burn_per_lap)
    driver_base = {d: coef[f"base_{d}"] - fuel_constant for d in drivers}

    params = replace(
        template,
        base_lap_time=float(np.mean(list(driver_base.values()))),
        seconds_per_kg=float(seconds_per_kg),
        fresh_pace_offset={"SOFT": 0.0,
                           **{c: float(coef[f"offset_{c}"]) for c in COMPOUNDS[1:]}},
        degradation_per_lap={c: float(coef[f"deg_{c}"]) for c in COMPOUNDS},
    )
    return FitResult(
        params=params,
        driver_base_lap_time={d: float(v) for d, v in driver_base.items()},
        std_errors=dict(zip(names, (float(v) for v in std_errors))),
        noise=float(np.sqrt(noise_var)),
    )


@dataclass(frozen=True)
class RaceEstimates:
    start_penalty: float   # mean lap 1 time above what the fitted model expects, seconds
    pit_stop_cost: float   # mean in-lap plus out-lap time above expected, per stop, seconds
    n_start_laps: int
    n_stops: int


# Safety Car, red flag, VSC: laps under these are slow for reasons unrelated to the start or the stop
_NEUTRALISED = set("4567")


def estimate_start_and_pit(laps: pd.DataFrame, fit: FitResult) -> RaceEstimates:
    """Measure what the fitted model leaves unexplained on lap 1 and on pit laps.

    `laps` is the full lap table of the race (not only clean laps), `fit` is the
    fit_params result for the same race. Excluded: pit-lane starters (their lap 1
    is different), laps under Safety Car, red flag or VSC, drivers without a fitted pace.
    """
    expected = [
        fit.driver_base_lap_time.get(driver, np.nan)
        + tyre_penalty(fit.params, compound, int(age)) + fuel_penalty(fit.params, int(lap) - 1)
        if isinstance(compound, str) else np.nan
        for driver, compound, age, lap in zip(laps["Driver"], laps["Compound"], laps["TyreAge"], laps["LapNumber"])
    ]
    excess = laps["LapTimeSec"] - np.array(expected)
    neutralised = laps["TrackStatus"].astype(str).apply(lambda status: bool(_NEUTRALISED & set(status)))
    usable = excess.notna() & ~neutralised

    lap1 = usable & (laps["LapNumber"] == 1) & laps["PitOutTime"].isna()
    in_lap = usable & laps["PitInTime"].notna()
    out_lap = usable & laps["PitOutTime"].notna() & (laps["LapNumber"] > 1)

    return RaceEstimates(
        start_penalty=float(excess[lap1].mean()),
        pit_stop_cost=float(excess[in_lap].mean() + excess[out_lap].mean()),
        n_start_laps=int(lap1.sum()),
        n_stops=int(in_lap.sum()),
    )
