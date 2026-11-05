"""
race_predictor.py - Predict total race time for a strategy.

The predictor owns base lap time and pit loss. For each lap it asks the tyre
model and the fuel model for their time penalties and sums everything up.

Strategy
--------
start_compound: tyre the race starts on, e.g. "MEDIUM"
pit_stops:      list of (lap, compound). The car pits at the end of `lap` and
                continues on a fresh tyre of `compound` from the next lap.
"""

from fuel_model import Fuel
from tyre_model import WEAR_PER_LAP, Tyre

BASE_LAP_TIME = 90.0  # seconds, fastest compound (soft), fresh tyre, empty tank (placeholder)
PIT_LOSS = 21.0       # seconds lost per pit stop (placeholder)


def predict_race_time(num_laps: int, start_compound: str,
                      pit_stops: list[tuple[int, str]]) -> tuple[float, list[float]]:
    """Return (total_race_time, lap_times) for a strategy."""
    _check_strategy(num_laps, start_compound, pit_stops)

    pit_compound_after = dict(pit_stops)
    tyre = Tyre(start_compound)
    fuel = Fuel()

    lap_times = []
    for lap in range(1, num_laps + 1):
        lap_time = BASE_LAP_TIME + tyre.time_penalty() + fuel.time_penalty()

        tyre.drive_lap()
        fuel.drive_lap()

        if lap in pit_compound_after:
            lap_time += PIT_LOSS
            tyre = Tyre(pit_compound_after[lap])

        lap_times.append(lap_time)

    return sum(lap_times), lap_times


def _check_strategy(num_laps, start_compound, pit_stops) -> None:
    compounds = [start_compound] + [c for _, c in pit_stops]
    for compound in compounds:
        if compound not in WEAR_PER_LAP:
            raise ValueError(f"Unknown compound: {compound}")

    laps = [lap for lap, _ in pit_stops]
    if laps != sorted(set(laps)):
        raise ValueError("Pit laps must be unique and in increasing order")
    if any(lap < 1 or lap >= num_laps for lap in laps):
        raise ValueError(f"Pit laps must be between 1 and {num_laps - 1}")


def format_time(seconds: float) -> str:
    """Format seconds as H:MM:SS.mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:06.3f}"


if __name__ == "__main__":
    NUM_LAPS = 60

    strategies = {
        "No stop (HARD)":            ("HARD", []),
        "1 stop (SOFT -> HARD)":   ("SOFT", [(25, "HARD")]),
        "1 stop (SOFT -> SOFT)":   ("SOFT", [(30, "SOFT")]),
        "2 stop (SOFT-SOFT-SOFT)": ("SOFT", [(18, "SOFT"), (40, "SOFT")]),
    }

    for name, (start, stops) in strategies.items():
        total, lap_times = predict_race_time(NUM_LAPS, start, stops)
        print(f"{name:28s} {format_time(total)}   "
              f"lap 1 = {lap_times[0]:.2f}s  lap {NUM_LAPS} = {lap_times[-1]:.2f}s")
