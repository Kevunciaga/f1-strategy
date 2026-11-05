"""
fuel_model.py - Step 2: fuel load adds weight, weight adds lap time.

The car starts with an initial fuel load (kg). Each lap it burns a constant
amount of fuel. The fuel adds a time penalty to the lap in proportion to the
load carried, so lap time falls as fuel burns off. Base lap time is owned by
the predictor, not this model.
"""

INITIAL_FUEL_LOAD = 110.0   # kg at race start (placeholder)
FUEL_BURN_PER_LAP = 1.8     # kg burned per lap (placeholder)
SECONDS_PER_KG = 0.03       # lap time penalty per kg carried (placeholder)


class Fuel:
    def __init__(self, initial_load: float = INITIAL_FUEL_LOAD,
                 burn_per_lap: float = FUEL_BURN_PER_LAP):
        self.load = initial_load
        self.burn_per_lap = burn_per_lap

    def time_penalty(self) -> float:
        """Seconds added to a lap by the fuel carried at the current load."""
        return self.load * SECONDS_PER_KG

    def drive_lap(self) -> None:
        """Burn one lap of fuel."""
        self.load = max(0.0, self.load - self.burn_per_lap)


if __name__ == "__main__":
    fuel = Fuel()
    print(f"{'Lap':>3} {'Fuel (kg)':>10} {'Penalty (s)':>12}")
    for lap in range(1, 61):
        print(f"{lap:3d} {fuel.load:10.1f} {fuel.time_penalty():12.3f}")
        fuel.drive_lap()
