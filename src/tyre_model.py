"""
tyre_model.py - Step 2: three compounds, each with its own constant wear rate.

A tyre starts at 100 health. Each lap it loses a constant amount of health
set by its compound. Each compound also has a fresh-tyre pace offset: softs
are fastest, hards slowest. The tyre adds a time penalty to the lap made of
that offset plus a wear term in proportion to the health lost. Base lap time
is owned by the predictor, not this model.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SECONDS_PER_HEALTH_LOST = 0.03  # lap time penalty per health point lost

# Seconds added to the lap on which the tyre punctures (placeholder)
PUNCTURE_PENALTY = 40.0

# Seconds slower than the fastest compound (soft) on a fresh tyre (placeholders)
FRESH_PACE_OFFSET = {"SOFT": 0.0, "MEDIUM": 0.5, "HARD": 1.0}

# Health points lost per lap (placeholders)
WEAR_PER_LAP = {"SOFT": 3.0, "MEDIUM": 2.0, "HARD": 1.0}

COLOURS = {"SOFT": "#E8002D", "MEDIUM": "#E8B800", "HARD": "#555555"}


class Tyre:
    def __init__(self, compound: str):
        self.compound = compound
        self.health = 100.0

    def time_penalty(self) -> float:
        """Seconds added to a lap: fresh pace offset plus wear at current health."""
        health_lost = 100.0 - self.health
        return FRESH_PACE_OFFSET[self.compound] + health_lost * SECONDS_PER_HEALTH_LOST

    def drive_lap(self) -> None:
        """Wear the tyre by one lap."""
        self.health = max(0.0, self.health - WEAR_PER_LAP[self.compound])


def tyre_penalty(compound: str, tyre_age: int) -> float:
    """
    Seconds a tyre adds to a lap, given its compound and age.

    tyre_age: laps already driven on this set. Fresh tyre = 0.

    Pure function: no state, no side effects. Same inputs always give the
    same output. The old Tyre class gets this answer by looping drive_lap();
    here you must get it straight from tyre_age.
    """
    health_lost = min(100.0, tyre_age * WEAR_PER_LAP[compound])
    penalty = FRESH_PACE_OFFSET[compound] + health_lost * SECONDS_PER_HEALTH_LOST
    if has_punctured(compound, tyre_age):
        penalty += PUNCTURE_PENALTY
    return penalty


def has_punctured(compound: str, tyre_age: int) -> bool:
    """True once the tyre has lost all 100 health. Placeholder rule."""
    return tyre_age * WEAR_PER_LAP[compound] >= 100.0


def stint_penalties(compound: str, num_laps: int) -> list[float]:
    """Tyre time penalty for each lap of a stint on one fresh tyre."""
    tyre = Tyre(compound)
    penalties = []
    for _ in range(num_laps):
        penalties.append(tyre.time_penalty())
        tyre.drive_lap()
    return penalties


def plot_penalties(num_laps: int, save_path: str = "tyre_penalties.png") -> None:
    """Plot tyre time penalty against lap for each compound."""
    fig, ax = plt.subplots(figsize=(8, 5))
    for compound in WEAR_PER_LAP:
        penalties = stint_penalties(compound, num_laps)
        ax.plot(range(1, num_laps + 1), penalties,
                color=COLOURS[compound], label=compound)
    ax.set_xlabel("Lap")
    ax.set_ylabel("Tyre time penalty (s)")
    ax.set_title("Tyre time penalty vs lap by compound")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"Plot saved -> {save_path}")


if __name__ == "__main__":
    plot_penalties(num_laps=60)
