"""
fuel_model.py - Fuel load adds weight, weight adds lap time.

The car starts with an initial fuel load (kg) and burns a constant amount per
lap. The time penalty is proportional to the load carried, so it is largest at
the start and falls as fuel burns off. Pure functions: no state. All numbers
come from Params. Base lap time is owned by the predictor, not this model.
"""

from params import DEFAULT_PARAMS, Params


def fuel_load(params: Params, laps_driven: int) -> float:
    """Fuel left in the car (kg) after `laps_driven` laps. Floors at 0."""
    return max(0.0, params.initial_fuel_load - laps_driven * params.fuel_burn_per_lap)


def fuel_penalty(params: Params, laps_driven: int) -> float:
    """Seconds a fuel load adds to a lap, given laps already driven."""
    return fuel_load(params, laps_driven) * params.seconds_per_kg


if __name__ == "__main__":
    print(f"{'Lap':>3} {'Fuel (kg)':>10} {'Penalty (s)':>12}")
    for lap in range(1, 61):
        laps_driven = lap - 1
        print(f"{lap:3d} {fuel_load(DEFAULT_PARAMS, laps_driven):10.1f} "
              f"{fuel_penalty(DEFAULT_PARAMS, laps_driven):12.3f}")
