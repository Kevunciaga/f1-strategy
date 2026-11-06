"""Tests use small made-up lap tables, so no FastF1 download is needed."""

import pandas as pd
import pytest

from data_loader import (clean_laps, driver_race_time, driver_strategy,
                         estimate_base_pace, has_wet_tyres)
from strategy import PitStop, Strategy


def laps_table(rows):
    columns = ["LapNumber", "Stint", "Compound", "LapTimeSec", "PitInTime",
               "PitOutTime", "IsAccurate", "Deleted", "TrackStatus"]
    defaults = dict(Stint=1, Compound="SOFT", LapTimeSec=75.0, PitInTime=pd.NaT,
                    PitOutTime=pd.NaT, IsAccurate=True, Deleted=False, TrackStatus="1")
    return pd.DataFrame([{**defaults, **row} for row in rows], columns=columns)


def test_strategy_from_two_stints():
    laps = laps_table(
        [{"LapNumber": n, "Stint": 1, "Compound": "SOFT"} for n in range(1, 21)]
        + [{"LapNumber": n, "Stint": 2, "Compound": "HARD"} for n in range(21, 41)]
    )
    assert driver_strategy(laps) == Strategy("SOFT", (PitStop(20, "HARD"),))


def test_strategy_keeps_consecutive_stints_on_same_compound():
    laps = laps_table(
        [{"LapNumber": n, "Stint": 1, "Compound": "MEDIUM"} for n in range(1, 11)]
        + [{"LapNumber": n, "Stint": 2, "Compound": "MEDIUM"} for n in range(11, 21)]
        + [{"LapNumber": n, "Stint": 3, "Compound": "SOFT"} for n in range(21, 26)]
    )
    assert driver_strategy(laps) == Strategy(
        "MEDIUM", (PitStop(10, "MEDIUM"), PitStop(20, "SOFT")))


def test_strategy_with_no_stop():
    laps = laps_table([{"LapNumber": n} for n in range(1, 11)])
    assert driver_strategy(laps) == Strategy("SOFT")


def test_race_time_is_sum_of_lap_times():
    laps = laps_table([{"LapNumber": n, "LapTimeSec": 70.0 + n} for n in range(1, 4)])
    assert driver_race_time(laps) == pytest.approx(216.0)


def test_clean_laps_drops_everything_that_is_not_normal_pace():
    pit = pd.Timestamp("2021-09-05")
    laps = laps_table([
        {"LapNumber": 1},                          # standing start
        {"LapNumber": 2},                          # keep
        {"LapNumber": 3, "PitInTime": pit},        # in-lap
        {"LapNumber": 4, "PitOutTime": pit},       # out-lap
        {"LapNumber": 5, "IsAccurate": False},
        {"LapNumber": 6, "Deleted": True},
        {"LapNumber": 7, "TrackStatus": "4"},      # safety car
        {"LapNumber": 8, "TrackStatus": "12"},     # yellow flag
        {"LapNumber": 9, "LapTimeSec": float("nan")},
        {"LapNumber": 10},                         # keep
    ])
    assert clean_laps(laps)["LapNumber"].tolist() == [2, 10]


def test_base_pace_is_mean_of_fastest_laps():
    laps = laps_table([{"LapNumber": n, "LapTimeSec": t}
                       for n, t in enumerate([80, 74, 73, 75, 72, 71, 90], start=1)])
    assert estimate_base_pace(laps, n=3) == pytest.approx((71 + 72 + 73) / 3)


def test_wet_tyre_detection():
    dry = laps_table([{"LapNumber": 1}, {"LapNumber": 2, "Compound": "HARD"}])
    wet = laps_table([{"LapNumber": 1}, {"LapNumber": 2, "Compound": "INTERMEDIATE"}])
    assert not has_wet_tyres(dry)
    assert has_wet_tyres(wet)
