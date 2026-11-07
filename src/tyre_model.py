"""
tyre_model.py - Tyre time penalty by compound and tyre age.

Each compound has a fresh-tyre pace offset (softs fastest, hards slowest) and
loses a fixed number of seconds per lap of tyre age. The time penalty of a lap
is the offset plus degradation times tyre age. Once a tyre reaches its puncture
age the lap gets a large extra penalty. Pure functions: no state. All numbers
come from Params. Base lap time is owned by the predictor, not this model.
"""

from params import DEFAULT_PARAMS, Params

COLOURS = {"SOFT": "#E8002D", "MEDIUM": "#E8B800", "HARD": "#555555"}


def has_punctured(params: Params, compound: str, tyre_age: int) -> bool:
    """True once the tyre reaches its puncture age. Placeholder rule."""
    return tyre_age >= params.puncture_age[compound]


def tyre_penalty(params: Params, compound: str, tyre_age: int) -> float:
    """
    Seconds a tyre adds to a lap, given its compound and age.

    tyre_age: laps already driven on this set. Fresh tyre = 0.
    """
    penalty = (params.fresh_pace_offset[compound]
               + tyre_age * params.degradation_per_lap[compound])
    if has_punctured(params, compound, tyre_age):
        penalty += params.puncture_penalty
    return penalty


def stint_penalties(params: Params, compound: str, num_laps: int) -> list[float]:
    """Tyre time penalty for each lap of a stint on one fresh tyre."""
    return [tyre_penalty(params, compound, age) for age in range(num_laps)]


def plot_penalties(params: Params, num_laps: int,
                   save_path: str = "tyre_penalties.png") -> None:
    """Plot tyre time penalty against lap for each compound."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    for compound in params.degradation_per_lap:
        penalties = stint_penalties(params, compound, num_laps)
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
    plot_penalties(DEFAULT_PARAMS, num_laps=60)
