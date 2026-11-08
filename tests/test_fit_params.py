"""Fit a made-up race with known numbers and check that fit_params recovers them."""

import pandas as pd
import pytest

from fit_params import fit_params
from params import Params
from race_predictor import predict_race_time
from strategy import PitStop, Strategy

TRUE = Params(
    base_lap_time=80.0,
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


def made_up_clean_laps():
    """Noise-free laps produced by the race simulator itself, pit laps removed."""
    rows = []
    for driver, strategy in STRATEGIES.items():
        params = Params(**{**TRUE.__dict__, "base_lap_time": TRUE.base_lap_time + DRIVER_PACE[driver]})
        _, lap_times, _ = predict_race_time(params, NUM_LAPS, strategy)
        for first, last, compound in strategy.stints(NUM_LAPS):
            for lap in range(first, last + 1):
                if lap == last and last != NUM_LAPS:
                    continue  # in-lap carries the pit loss
                rows.append({"Driver": driver, "Compound": compound, "LapNumber": lap,
                             "TyreAge": lap - first, "LapTimeSec": lap_times[lap - 1]})
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def result():
    return fit_params(made_up_clean_laps())


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


def test_missing_compound_raises():
    laps = made_up_clean_laps()
    with pytest.raises(ValueError):
        fit_params(laps[laps["Compound"] != "HARD"])


def test_redundant_columns_raise():
    laps = made_up_clean_laps()
    one_stint = laps[(laps["Driver"] == "AAA") & (laps["Compound"] == "SOFT")]
    with pytest.raises(ValueError):
        fit_params(one_stint)
