"""
fuel_model.py - Fuel load adds weight, weight adds lap time.

The car starts with an initial fuel load (kg) and burns a constant amount per
lap. The time penalty is proportional to the load carried, so it is largest at
the start and falls as fuel burns off. Pure functions: no state. Base lap time
is owned by the predictor, not this model.
"""

INITIAL_FUEL_LOAD = 110.0   # kg at race start (placeholder)
FUEL_BURN_PER_LAP = 1.8     # kg burned per lap (placeholder)
SECONDS_PER_KG = 0.03       # lap time penalty per kg carried (placeholder)


def fuel_load(laps_driven: int) -> float:
    """Fuel left in the car (kg) after `laps_driven` laps. Floors at 0."""
    return max(0.0, INITIAL_FUEL_LOAD - laps_driven * FUEL_BURN_PER_LAP)


def fuel_penalty(laps_driven: int) -> float:
    """Seconds a fuel load adds to a lap, given laps already driven."""
    return fuel_load(laps_driven) * SECONDS_PER_KG


if __name__ == "__main__":
    print(f"{'Lap':>3} {'Fuel (kg)':>10} {'Penalty (s)':>12}")
    for lap in range(1, 61):
        laps_driven = lap - 1
        print(f"{lap:3d} {fuel_load(laps_driven):10.1f} {fuel_penalty(laps_driven):12.3f}")
