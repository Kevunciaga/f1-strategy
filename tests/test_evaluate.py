from dataclasses import replace

import numpy as np
import pytest

from data_loader import clean_laps
from evaluate import (RaceData, average_track_losses, average_tyre_fuel_params, build_params,
                      calibrate_base, neutralised_laps, race_errors, zero_tyre_and_fuel)
from fit_params import RaceEstimates, estimate_start_and_pit, fit_params
from test_fit_params import made_up_race


def make_race(track="A", year=2021):
    laps = made_up_race()
    clean = clean_laps(laps)
    fit = fit_params(clean)
    return RaceData(track, year, laps, clean, fit, estimate_start_and_pit(laps, fit))


def test_noise_free_race_is_predicted_exactly_from_another_identical_race():
    train, test = make_race(year=2021), make_race(year=2022)
    errors = race_errors(build_params(test, [train], same_track=True), test)
    assert len(errors) == 6
    assert errors == pytest.approx(np.zeros(6), abs=1e-6)


def test_calibrated_base_pace_equals_the_driver_base_pace_in_noise_free_data():
    race = make_race()
    driver_clean = race.clean[race.clean["Driver"] == "BBB"]
    assert calibrate_base(race.fit.params, driver_clean) == pytest.approx(race.fit.driver_base_lap_time["BBB"])


def test_average_tyre_fuel_params_is_the_median_over_races():
    base = make_race().fit

    def fit_with(deg, kg):
        return replace(base, params=replace(base.params, degradation_per_lap={"SOFT": deg, "MEDIUM": deg, "HARD": deg},
                                            seconds_per_kg=kg))

    median = average_tyre_fuel_params([fit_with(0.1, 0.02), fit_with(0.2, 0.03), fit_with(5.0, 0.90)])
    assert median.degradation_per_lap["SOFT"] == pytest.approx(0.2)
    assert median.seconds_per_kg == pytest.approx(0.03)


def test_missing_track_value_falls_back_to_other_tracks():
    nan = float("nan")
    track = [RaceEstimates(nan, 4.0, 20.0, 21.0, 0, 5)]
    elsewhere = [RaceEstimates(8.0, 5.0, 18.0, 20.0, 20, 5), RaceEstimates(10.0, 5.0, 18.0, 20.0, 20, 5)]
    start, in_loss, out_loss = average_track_losses(track, elsewhere)
    assert start == pytest.approx(9.0)    # from elsewhere: nothing at this track
    assert in_loss == pytest.approx(4.0)  # from this track
    assert out_loss == pytest.approx(20.0)


def test_zero_baseline_removes_tyre_and_fuel_effects():
    baseline = zero_tyre_and_fuel(make_race().fit.params)
    assert set(baseline.degradation_per_lap.values()) == {0.0}
    assert set(baseline.fresh_pace_offset.values()) == {0.0}
    assert baseline.seconds_per_kg == 0.0


def test_neutralised_laps_counts_laps_where_most_of_the_field_is_neutralised():
    race = make_race()
    laps = race.laps.copy()
    laps.loc[laps["LapNumber"].isin([5, 6, 7]), "TrackStatus"] = "4"
    laps.loc[(laps["LapNumber"] == 20) & (laps["Driver"] == "AAA"), "TrackStatus"] = "4"   # one car only
    assert neutralised_laps(replace(race, laps=laps)) == 3
