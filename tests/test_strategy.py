import pytest

from strategy import PitStop, Strategy


def test_pit_laps_not_increasing_raises():
    with pytest.raises(ValueError):
        Strategy("SOFT", (PitStop(30, "HARD"), PitStop(20, "MEDIUM")))


def test_duplicate_pit_lap_raises():
    with pytest.raises(ValueError):
        Strategy("SOFT", (PitStop(20, "HARD"), PitStop(20, "MEDIUM")))


@pytest.mark.parametrize("lap", [0, -3])
def test_pit_lap_below_one_raises(lap):
    with pytest.raises(ValueError):
        Strategy("SOFT", (PitStop(lap, "HARD"),))


def test_validate_rejects_pit_lap_beyond_race(params):
    strategy = Strategy("SOFT", (PitStop(60, "HARD"),))
    with pytest.raises(ValueError):
        strategy.validate(params, num_laps=60)


def test_validate_accepts_last_possible_pit_lap(params):
    Strategy("SOFT", (PitStop(59, "HARD"),)).validate(params, num_laps=60)


def test_validate_rejects_unknown_start_compound(params):
    with pytest.raises(ValueError):
        Strategy("WET").validate(params, num_laps=60)


def test_validate_rejects_unknown_pit_compound(params):
    with pytest.raises(ValueError):
        Strategy("SOFT", (PitStop(20, "WET"),)).validate(params, num_laps=60)


def test_compounds_and_num_stops():
    strategy = Strategy("SOFT", (PitStop(20, "MEDIUM"), PitStop(40, "HARD")))
    assert strategy.compounds == ("SOFT", "MEDIUM", "HARD")
    assert strategy.num_stops == 2


def test_stints_cover_every_lap_once():
    strategy = Strategy("SOFT", (PitStop(20, "MEDIUM"), PitStop(40, "HARD")))
    assert strategy.stints(60) == [(1, 20, "SOFT"), (21, 40, "MEDIUM"), (41, 60, "HARD")]


def test_no_stop_strategy_is_one_stint():
    assert Strategy("HARD").stints(60) == [(1, 60, "HARD")]


def test_list_input_becomes_hashable_tuple():
    strategy = Strategy("SOFT", [PitStop(20, "MEDIUM")])
    assert isinstance(strategy.pit_stops, tuple)
    assert hash(strategy) == hash(Strategy("SOFT", (PitStop(20, "MEDIUM"),)))
