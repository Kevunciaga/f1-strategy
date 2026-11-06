"""
Shared fixtures. Tests use their own round-number Params so expected values
can be worked out by hand and do not change when the real defaults are fitted.

With these numbers:
  SOFT   punctures at tyre age 5   (5 x 20 health = 100)
  MEDIUM punctures at tyre age 10  (10 x 10)
  HARD   punctures at tyre age 20  (20 x 5)
"""

import pytest

from params import DEFAULT_PARAMS, Params

TEST_PARAMS = Params(
    base_lap_time=100.0,
    pit_loss=20.0,
    seconds_per_health_lost=0.1,
    puncture_penalty=50.0,
    fresh_pace_offset={"SOFT": 0.0, "MEDIUM": 1.0, "HARD": 2.0},
    wear_per_lap={"SOFT": 20.0, "MEDIUM": 10.0, "HARD": 5.0},
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
