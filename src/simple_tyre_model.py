"""
simple_tyre_model.py — Primitive tyre degradation model (learning step 1).

The idea: a tyre starts with 100 "health" points. Each lap it's driven,
health drops by a constant amount. Lap time gets slower the more health
is lost.

Intentionally the simplest possible model — no compounds, no warm-up,
no cliff. This is a stepping stone before the fitted model in tyre_model.py.
"""


class SimpleTyre:
    def __init__(self, wear_per_lap: float = 2.0, seconds_per_health_lost: float = 0.03):
        """
        Args:
            wear_per_lap: health points lost each lap (constant)
            seconds_per_health_lost: lap-time penalty (s) per health point lost
        """
        self.health = 100.0
        self.wear_per_lap = wear_per_lap
        self.seconds_per_health_lost = seconds_per_health_lost

    def lap(self) -> float:
        """Drive one lap: wear the tyre down, return the lap-time penalty (s)."""
        self.health = max(0.0, self.health - self.wear_per_lap)
        health_lost = 100.0 - self.health
        return health_lost * self.seconds_per_health_lost


def simulate_stint(num_laps: int, base_pace: float, wear_per_lap: float = 2.0,
                    seconds_per_health_lost: float = 0.03):
    """Run a stint and return (lap_times, health_trace)."""
    tyre = SimpleTyre(wear_per_lap, seconds_per_health_lost)
    lap_times = []
    healths = []
    for _ in range(num_laps):
        penalty = tyre.lap()
        lap_times.append(base_pace + penalty)
        healths.append(tyre.health)
    return lap_times, healths


if __name__ == "__main__":
    BASE_PACE = 90.0  # seconds, arbitrary placeholder

    lap_times, healths = simulate_stint(num_laps=20, base_pace=BASE_PACE)

    print(f"{'Lap':>3} {'Health':>7} {'LapTime':>9}")
    for i, (t, h) in enumerate(zip(lap_times, healths), start=1):
        print(f"{i:3d} {h:7.1f} {t:9.3f}")
