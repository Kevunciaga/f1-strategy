"""
Expected values are worked out by hand from the TEST_PARAMS in conftest.py.
Lap time = 100 + tyre penalty + fuel penalty (+ 20 if a stop is made that lap).
Fuel penalty by lap: 5.0, 4.8, 4.6, 4.4, ...
"""

from dataclasses import replace

import pytest

from race_predictor import predict_race_time
from strategy import PitStop, Strategy


def stop_pairs(stops):
    return [(stop.lap, stop.compound) for stop in stops]


# --- hand-calculated results -------------------------------------------------

def test_no_stop_race_matches_hand_calculation(params):
    # HARD: offset 2.0, +0.5 per lap of age. 4 laps.
    total, lap_times, stops = predict_race_time(params, 4, Strategy("HARD"))
    assert lap_times == pytest.approx([107.0, 107.3, 107.6, 107.9])
    assert total == pytest.approx(429.8)
    assert stops == []


def test_planned_stop_matches_hand_calculation(params):
    # HARD, stop after lap 2 onto SOFT. Lap 2 pays the 20 s pit loss.
    # Lap 3: fresh soft = 100 + 0 + 4.6. Lap 4: soft age 1 = 100 + 2.0 + 4.4.
    strategy = Strategy("HARD", (PitStop(2, "SOFT"),))
    total, lap_times, stops = predict_race_time(params, 4, strategy)
    assert lap_times == pytest.approx([107.0, 127.3, 104.6, 106.4])
    assert total == pytest.approx(445.3)
    assert stop_pairs(stops) == [(2, "SOFT")]


# --- invariants --------------------------------------------------------------

@pytest.mark.parametrize("strategy", [
    Strategy("HARD"),
    Strategy("SOFT", (PitStop(4, "HARD"),)),
    Strategy("SOFT"),
])
def test_one_lap_time_per_lap_and_total_is_their_sum(any_params, strategy):
    total, lap_times, _ = predict_race_time(any_params, 30, strategy)
    assert len(lap_times) == 30
    assert total == pytest.approx(sum(lap_times))


def test_each_stop_adds_exactly_the_pit_loss(params):
    strategy = Strategy("HARD", (PitStop(3, "MEDIUM"), PitStop(7, "HARD")))
    slower = replace(params, pit_loss=params.pit_loss + 5.0)
    base_total, _, stops = predict_race_time(params, 12, strategy)
    slower_total, _, _ = predict_race_time(slower, 12, strategy)
    assert len(stops) == 2
    assert slower_total - base_total == pytest.approx(10.0)


def test_different_params_change_the_result(params):
    strategy = Strategy("HARD")
    slow = replace(params, base_lap_time=params.base_lap_time + 1.0)
    base_total, _, _ = predict_race_time(params, 10, strategy)
    slow_total, _, _ = predict_race_time(slow, 10, strategy)
    assert slow_total - base_total == pytest.approx(10.0)


def test_invalid_strategy_is_rejected_by_predictor(params):
    with pytest.raises(ValueError):
        predict_race_time(params, 10, Strategy("SOFT", (PitStop(10, "HARD"),)))


# --- forced stops (soft punctures at age 5, so on lap 6) ---------------------

def test_puncture_with_no_planned_stop_forces_a_stop_at_the_puncture_lap(params):
    _, _, stops = predict_race_time(params, 20, Strategy("SOFT"))
    assert stops[0].lap == 6


def test_replacement_tyre_can_puncture_too(params):
    # lap 6 stop fits MEDIUM (14 laps left). Medium punctures at age 10, so lap 17.
    _, _, stops = predict_race_time(params, 20, Strategy("SOFT"))
    assert stop_pairs(stops) == [(6, "MEDIUM"), (17, "SOFT")]


def test_forced_stop_lap_pays_puncture_penalty_and_pit_loss(params):
    # lap 6: 100 + (0 + 10.0 wear + 50 puncture) + fuel 4.0 + 20 pit loss
    _, lap_times, _ = predict_race_time(params, 20, Strategy("SOFT"))
    assert lap_times[5] == pytest.approx(184.0)


def test_forced_stop_moves_next_planned_stop_earlier(params):
    strategy = Strategy("SOFT", (PitStop(10, "HARD"),))
    _, _, stops = predict_race_time(params, 20, strategy)
    assert stop_pairs(stops) == [(6, "HARD")]


def test_forced_stop_keeps_later_planned_stops(params):
    strategy = Strategy("SOFT", (PitStop(10, "HARD"), PitStop(15, "SOFT")))
    _, _, stops = predict_race_time(params, 20, strategy)
    assert stop_pairs(stops) == [(6, "HARD"), (15, "SOFT")]


def test_puncture_on_planned_pit_lap_is_one_stop(params):
    strategy = Strategy("SOFT", (PitStop(6, "HARD"),))
    _, lap_times, stops = predict_race_time(params, 20, strategy)
    assert stop_pairs(stops) == [(6, "HARD")]
    assert lap_times[5] == pytest.approx(184.0)


@pytest.mark.parametrize("num_laps, expected_compound", [
    (16, "SOFT"),    # 10 laps left after the stop
    (17, "MEDIUM"),  # 11
    (26, "MEDIUM"),  # 20
    (27, "HARD"),    # 21
])
def test_compound_after_puncture_depends_on_laps_left(params, num_laps, expected_compound):
    _, _, stops = predict_race_time(params, num_laps, Strategy("SOFT"))
    assert stops[0].compound == expected_compound


def test_puncture_on_final_lap_makes_no_stop_and_pays_no_pit_loss(params):
    # lap 6 of 6: 100 + 60 + fuel 4.0, no pit loss
    _, lap_times, stops = predict_race_time(params, 6, Strategy("SOFT"))
    assert stops == []
    assert lap_times[5] == pytest.approx(164.0)


# --- start penalty -----------------------------------------------------------

def test_start_penalty_is_added_to_lap_one_only(params):
    slower_start = replace(params, start_penalty=7.5)
    _, base_laps, _ = predict_race_time(params, 6, Strategy("HARD"))
    _, slow_laps, _ = predict_race_time(slower_start, 6, Strategy("HARD"))
    assert slow_laps[0] - base_laps[0] == pytest.approx(7.5)
    assert slow_laps[1:] == pytest.approx(base_laps[1:])


def test_start_penalty_defaults_to_zero():
    from params import DEFAULT_PARAMS
    assert DEFAULT_PARAMS.start_penalty == 0.0
