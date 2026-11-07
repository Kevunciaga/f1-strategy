import pytest

from tyre_model import has_punctured, stint_penalties, tyre_penalty

COMPOUNDS = ["SOFT", "MEDIUM", "HARD"]


@pytest.mark.parametrize("compound", COMPOUNDS)
def test_fresh_tyre_penalty_is_its_pace_offset(params, compound):
    assert tyre_penalty(params, compound, 0) == params.fresh_pace_offset[compound]


def test_wear_term_is_degradation_times_age(params):
    # soft loses 2.0 s per lap of age, so age 2 adds 4.0 s
    assert tyre_penalty(params, "SOFT", 2) == pytest.approx(4.0)


@pytest.mark.parametrize("compound", COMPOUNDS)
def test_penalty_never_decreases_before_puncture(any_params, compound):
    age = 0
    previous = tyre_penalty(any_params, compound, age)
    while not has_punctured(any_params, compound, age + 1):
        age += 1
        current = tyre_penalty(any_params, compound, age)
        assert current >= previous
        previous = current


@pytest.mark.parametrize("compound", COMPOUNDS)
def test_penalty_is_never_negative(any_params, compound):
    assert all(p >= 0 for p in stint_penalties(any_params, compound, 150))


@pytest.mark.parametrize("compound, last_safe_age, first_puncture_age", [
    ("SOFT", 4, 5),
    ("MEDIUM", 9, 10),
    ("HARD", 19, 20),
])
def test_puncture_age(params, compound, last_safe_age, first_puncture_age):
    assert not has_punctured(params, compound, last_safe_age)
    assert has_punctured(params, compound, first_puncture_age)


def test_puncture_adds_exactly_the_puncture_penalty(params):
    # soft age 4: 0 + 4 x 2.0 = 8.0. age 5: 0 + 5 x 2.0 + 50 = 60.0
    assert tyre_penalty(params, "SOFT", 4) == pytest.approx(8.0)
    assert tyre_penalty(params, "SOFT", 5) == pytest.approx(60.0)


def test_stint_penalties_matches_tyre_penalty(params):
    assert stint_penalties(params, "MEDIUM", 5) == [
        tyre_penalty(params, "MEDIUM", age) for age in range(5)
    ]
