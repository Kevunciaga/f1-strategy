"""Fit a made-up race with known numbers and check that fit_params recovers them."""

import pandas as pd
import pytest

from data_loader import clean_laps
from fit_params import estimate_start_and_pit, fit_params
from params import Params
from race_predictor import predict_race_time
from strategy import PitStop, Strategy

TRUE = Params(
    base_lap_time=80.0,
    pit_loss=24.0,
    start_penalty=7.0,
    fresh_pace_offset={"SOFT": 0.0, "MEDIUM": 0.4, "HARD": 0.9},
    degradation_per_lap={"SOFT": 0.12, "MEDIUM": 0.07, "HARD": 0.03},
    seconds_per_kg=0.032,
)
NUM_LAPS = 60
DRIVER_PACE = {"AAA": 0.0, "BBB": 0.8, "CCC": -0.5, "DDD": 1.4, "EEE": 0.3, "FFF": -0.2}
STRATEGIES = {
    "AAA": Strategy("SOFT", (PitStop(14, "MEDIUM"), PitStop(38, "HARD"))),
    "BBB": Strategy("MEDIUM", (PitStop(22, "HARD"),)),
    "CCC": Strategy("HARD", (PitStop(30, "SOFT"),)),
    "DDD": Strategy("SOFT", (PitStop(10, "HARD"), PitStop(35, "MEDIUM"))),
    "EEE": Strategy("MEDIUM", (PitStop(18, "SOFT"), PitStop(41, "HARD"))),
    "FFF": Strategy("HARD", (PitStop(26, "MEDIUM"), PitStop(45, "SOFT"))),
}


def made_up_race():
    """Every lap of a noise-free race produced by the simulator itself, with pit and status columns."""
    pit_time = pd.Timestamp("2021-01-01")
    rows = []
    for driver, strategy in STRATEGIES.items():
        params = Params(**{**TRUE.__dict__, "base_lap_time": TRUE.base_lap_time + DRIVER_PACE[driver]})
        _, lap_times, _ = predict_race_time(params, NUM_LAPS, strategy)
        for stint, (first, last, compound) in enumerate(strategy.stints(NUM_LAPS), start=1):
            for lap in range(first, last + 1):
                rows.append({
                    "Driver": driver, "Stint": stint, "Compound": compound,
                    "LapNumber": lap, "TyreAge": lap - first, "LapTimeSec": lap_times[lap - 1],
                    "PitInTime": pit_time if (lap == last and last != NUM_LAPS) else pd.NaT,
                    "PitOutTime": pit_time if (lap == first and first != 1) else pd.NaT,
                    "TrackStatus": "1", "IsAccurate": True, "Deleted": False,
                })
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def race():
    return made_up_race()


@pytest.fixture(scope="module")
def result(race):
    return fit_params(clean_laps(race))


def test_recovers_degradation(result):
    for compound, true_value in TRUE.degradation_per_lap.items():
        assert result.params.degradation_per_lap[compound] == pytest.approx(true_value, abs=1e-6)


def test_recovers_compound_offsets(result):
    for compound, true_value in TRUE.fresh_pace_offset.items():
        assert result.params.fresh_pace_offset[compound] == pytest.approx(true_value, abs=1e-6)


def test_recovers_fuel_effect(result):
    assert result.params.seconds_per_kg == pytest.approx(TRUE.seconds_per_kg, abs=1e-6)


def test_recovers_each_drivers_base_pace(result):
    for driver, pace in DRIVER_PACE.items():
        assert result.driver_base_lap_time[driver] == pytest.approx(TRUE.base_lap_time + pace, abs=1e-6)


def test_noise_free_data_leaves_no_noise(result):
    assert result.noise == pytest.approx(0.0, abs=1e-6)


def test_missing_compound_raises(race):
    clean = clean_laps(race)
    with pytest.raises(ValueError):
        fit_params(clean[clean["Compound"] != "HARD"])


def test_redundant_columns_raise(race):
    clean = clean_laps(race)
    one_stint = clean[(clean["Driver"] == "AAA") & (clean["Compound"] == "SOFT")]
    with pytest.raises(ValueError):
        fit_params(one_stint)


def test_recovers_start_penalty_and_pit_stop_cost(race, result):
    estimates = estimate_start_and_pit(race, result)
    assert estimates.start_penalty == pytest.approx(TRUE.start_penalty, abs=1e-6)
    assert estimates.pit_stop_cost == pytest.approx(TRUE.pit_loss, abs=1e-6)
    assert estimates.n_start_laps == len(STRATEGIES)
    assert estimates.n_stops == sum(s.num_stops for s in STRATEGIES.values())


def test_laps_under_safety_car_are_ignored(race, result):
    slow_start = race.copy()
    slow_start.loc[(slow_start["LapNumber"] == 1) & (slow_start["Driver"] == "AAA"), "LapTimeSec"] += 60.0
    slow_start.loc[(slow_start["LapNumber"] == 1) & (slow_start["Driver"] == "AAA"), "TrackStatus"] = "4"
    estimates = estimate_start_and_pit(slow_start, result)
    assert estimates.start_penalty == pytest.approx(TRUE.start_penalty, abs=1e-6)
    assert estimates.n_start_laps == len(STRATEGIES) - 1
