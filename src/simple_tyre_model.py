"""
simple_tyre_model.py — Primitive tyre degradation model (learning step 1).

The idea: a tyre starts with 100 "health" points. Each lap it's driven,
health drops by a constant amount. Lap time gets slower the more health
is lost.

Intentionally the simplest possible model — no compounds, no warm-up,
no cliff. This is a stepping stone before the fitted model in tyre_model.py.
"""


COMPOUNDS = {
    "SOFT":   {"wear_per_lap": 3.0, "seconds_per_health_lost": 0.03},
    "MEDIUM": {"wear_per_lap": 2.0, "seconds_per_health_lost": 0.03},
    "HARD":   {"wear_per_lap": 1.0, "seconds_per_health_lost": 0.03},
}

COMPOUND_COLORS = {"SOFT": "#E8002D", "MEDIUM": "#E8B800", "HARD": "#555555"}


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


def plot_laptimes(laptimes_by_compound: dict, save_path: str | None = None) -> None:
    """Plot lap-time evolution for each compound, one line per compound, no markers."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))

    for compound, lap_times in laptimes_by_compound.items():
        laps = range(1, len(lap_times) + 1)
        ax.plot(laps, lap_times, color=COMPOUND_COLORS.get(compound), label=compound)

    ax.set_xlabel("Lap")
    ax.set_ylabel("Lap Time (s)")
    ax.set_title("Lap Time Evolution by Compound")
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    save_path = save_path or "simple_tyre_laptimes.png"
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"Plot saved -> {save_path}")


if __name__ == "__main__":
    BASE_PACE = 90.0  # seconds, arbitrary placeholder
    NUM_LAPS = 60

    laptimes_by_compound = {}
    for compound, params in COMPOUNDS.items():
        lap_times, _ = simulate_stint(num_laps=NUM_LAPS, base_pace=BASE_PACE, **params)
        laptimes_by_compound[compound] = lap_times
        print(f"{compound}: lap1={lap_times[0]:.3f}s  lap{NUM_LAPS}={lap_times[-1]:.3f}s")

    plot_laptimes(laptimes_by_compound)
