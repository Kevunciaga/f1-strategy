"""
fit_params.py - Fit the model's Params from the clean laps of one race.

Ported from learning notebook 03. One least-squares fit over every clean lap:

    lap time = driver pace + compound offset
               + degradation[compound] * tyre age + c * lap number
               + first stint effect * tyre age (stint 1 laps only)

Driver pace is fitted per driver. Offsets are relative to SOFT. The fuel effect
c is shared by all drivers and converted to seconds per kg with the burn rate in
Params.

The first stint term is there because stint 1 laps get quicker as the field
spreads out, drivers stop managing and the track rubbers in. Without it, that
effect is blamed on whichever compound runs most in stint 1 (usually the medium),
and its wear comes out too low: omitted variable bias, see learning notebook 05.
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
    std_errors: dict[str, float]            # uncertainty of each fitted coefficient; no "first_stint_age"
                                            # entry means the race had no clean stint 1 laps to fit it on
    noise: float                            # std of the left-over lap time error, seconds


def fit_params(clean: pd.DataFrame, template: Params = DEFAULT_PARAMS) -> FitResult:
    """Fit fresh_pace_offset, degradation_per_lap, seconds_per_kg and base pace.

    `clean` needs the columns Driver, Stint, Compound, TyreAge, LapNumber, LapTimeSec.
    If there are no clean stint 1 laps (e.g. red flag on lap 1), the first stint
    effect cannot be fitted and is set to 0.
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
    first_stint_age = ((clean["Stint"] == 1) * clean["TyreAge"]).to_numpy(dtype=float)
    if first_stint_age.any():
        columns.append(first_stint_age)
        names.append("first_stint_age")

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
        first_stint_age_effect=float(coef.get("first_stint_age", 0.0)),
    )
    return FitResult(
        params=params,
        driver_base_lap_time={d: float(v) for d, v in driver_base.items()},
        std_errors=dict(zip(names, (float(v) for v in std_errors))),
        noise=float(np.sqrt(noise_var)),
    )


def model_penalty(params: Params, compound: str, tyre_age: int, lap: int, stint: int) -> float:
    """Lap time above base pace that the model expects: tyre + fuel + first stint effect."""
    penalty = tyre_penalty(params, compound, tyre_age) + fuel_penalty(params, lap - 1)
    if stint == 1:
        penalty += params.first_stint_age_effect * tyre_age
    return penalty


@dataclass(frozen=True)
class RaceEstimates:
    start_penalty: float   # mean lap 1 time above what the fitted model expects, seconds
    pit_in_loss: float     # mean in-lap time above expected, seconds
    pit_out_loss: float    # mean out-lap time above expected, seconds
    pit_lane_time: float   # median time from pit entry to pit exit, seconds (information only)
    n_start_laps: int
    n_stops: int

    @property
    def pit_stop_cost(self) -> float:
        """Total time one stop costs: in-lap plus out-lap loss. Includes the time stationary in the box."""
        return self.pit_in_loss + self.pit_out_loss


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
        + model_penalty(fit.params, compound, int(age), int(lap), stint)
        if isinstance(compound, str) else np.nan
        for driver, compound, age, lap, stint
        in zip(laps["Driver"], laps["Compound"], laps["TyreAge"], laps["LapNumber"], laps["Stint"])
    ]
    excess = laps["LapTimeSec"] - np.array(expected)
    neutralised = laps["TrackStatus"].astype(str).apply(lambda status: bool(_NEUTRALISED & set(status)))
    usable = excess.notna() & ~neutralised

    lap1 = usable & (laps["LapNumber"] == 1) & laps["PitOutTime"].isna()
    in_lap = usable & laps["PitInTime"].notna()
    out_lap = usable & laps["PitOutTime"].notna() & (laps["LapNumber"] > 1)

    next_pit_out = laps.sort_values(["Driver", "LapNumber"]).groupby("Driver")["PitOutTime"].shift(-1)
    lane_seconds = (next_pit_out - laps["PitInTime"]).dt.total_seconds()

    return RaceEstimates(
        start_penalty=float(excess[lap1].mean()),
        pit_in_loss=float(excess[in_lap].mean()),
        pit_out_loss=float(excess[out_lap].mean()),
        pit_lane_time=float(lane_seconds[in_lap].median()),
        n_start_laps=int(lap1.sum()),
        n_stops=int(in_lap.sum()),
    )
