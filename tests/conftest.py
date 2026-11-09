"""
Shared fixtures. Tests use their own round-number Params so expected values
can be worked out by hand and do not change when the real defaults are fitted.

With these numbers:
  SOFT   loses 2.0 s per lap of age, punctures at age 5
  MEDIUM loses 1.0 s per lap of age, punctures at age 10
  HARD   loses 0.5 s per lap of age, punctures at age 20
"""

import pytest

from params import DEFAULT_PARAMS, Params

TEST_PARAMS = Params(
    base_lap_time=100.0,
    pit_in_loss=5.0,
    pit_out_loss=15.0,
    puncture_penalty=50.0,
    fresh_pace_offset={"SOFT": 0.0, "MEDIUM": 1.0, "HARD": 2.0},
    degradation_per_lap={"SOFT": 2.0, "MEDIUM": 1.0, "HARD": 0.5},
    puncture_age={"SOFT": 5, "MEDIUM": 10, "HARD": 20},
    initial_fuel_load=50.0,
    fuel_burn_per_lap=2.0,
    seconds_per_kg=0.1,
)


@pytest.fixture
def params():
    return TEST_PARAMS


@pytest.fixture(params=[TEST_PARAMS, DEFAULT_PARAMS], ids=["test_params", "default_params"])
def any_params(request):
    """For properties that must hold for any Params, including fitted ones later."""
    return request.param
