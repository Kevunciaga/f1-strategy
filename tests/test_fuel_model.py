import pytest

from fuel_model import fuel_load, fuel_penalty


def test_full_load_at_race_start(params):
    assert fuel_load(params, 0) == 50.0


def test_load_falls_by_burn_rate_per_lap(params):
    assert fuel_load(params, 3) == pytest.approx(44.0)


def test_load_floors_at_zero(params):
    assert fuel_load(params, 1000) == 0.0


def test_penalty_is_load_times_seconds_per_kg(params):
    assert fuel_penalty(params, 0) == pytest.approx(5.0)
    assert fuel_penalty(params, 3) == pytest.approx(4.4)


def test_penalty_is_linear_in_load(params):
    # equal lap steps remove equal fuel, so equal time
    step_1 = fuel_penalty(params, 0) - fuel_penalty(params, 1)
    step_2 = fuel_penalty(params, 1) - fuel_penalty(params, 2)
    assert step_1 == pytest.approx(step_2)


def test_penalty_never_increases_and_is_never_negative(any_params):
    penalties = [fuel_penalty(any_params, lap) for lap in range(150)]
    assert all(p >= 0 for p in penalties)
    assert all(later <= earlier for earlier, later in zip(penalties, penalties[1:]))
