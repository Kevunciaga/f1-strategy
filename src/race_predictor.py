"""
race_predictor.py - Predict total race time for a strategy.

The predictor owns base lap time and pit loss. For each lap it asks the tyre
model and the fuel model for their time penalties and sums everything up.

Strategy
--------
start_compound: tyre the race starts on, e.g. "MEDIUM"
pit_stops:      list of (lap, compound). The car pits at the end of `lap` and
                continues on a fresh tyre of `compound` from the next lap.

Forced stops (puncture)
-----------------------
If a tyre punctures, the puncture is assumed to happen at the start/finish line
and the car pits at the end of that lap. The tyre model adds the puncture time
penalty to that lap; the predictor adds the pit loss.
- Next planned stop exists: it is moved earlier to the puncture lap.
- No planned stop left: compound is chosen from the laps remaining
  (<= 10 SOFT, <= 20 MEDIUM, otherwise HARD).
- Puncture on a planned pit lap: just change tyres, one stop.
- Puncture on the final lap: no stop, the race ends.
"""

from fuel_model import fuel_penalty
from params import DEFAULT_PARAMS, Params
from tyre_model import has_punctured, tyre_penalty


def predict_race_time(params: Params, num_laps: int, start_compound: str,
                      pit_stops: list[tuple[int, str]]
                      ) -> tuple[float, list[float], list[tuple[int, str]]]:
    """Return (total_race_time, lap_times, stops_taken) for a strategy.

    stops_taken lists every stop actually made as (lap, compound), including
    forced ones and stops that were moved earlier.
    """
    _check_strategy(params, num_laps, start_compound, pit_stops)

    planned = list(pit_stops)  # stops not yet taken
    compound, tyre_age = start_compound, 0

    lap_times = []
    stops_taken = []
    for lap in range(1, num_laps + 1):
        lap_time = (params.base_lap_time + tyre_penalty(params, compound, tyre_age)
                    + fuel_penalty(params, lap - 1))

        new_compound = None
        if planned and planned[0][0] == lap:
            new_compound = planned.pop(0)[1]
        elif has_punctured(params, compound, tyre_age) and lap < num_laps:
            new_compound = _forced_stop_compound(planned, num_laps - lap)

        if new_compound is None:
            tyre_age += 1
        else:
            lap_time += params.pit_loss
            stops_taken.append((lap, new_compound))
            compound, tyre_age = new_compound, 0

        lap_times.append(lap_time)

    return sum(lap_times), lap_times, stops_taken


def _forced_stop_compound(planned: list[tuple[int, str]], laps_left: int) -> str:
    """Compound to fit after a puncture. Pulls the next planned stop forward."""
    if planned:
        return planned.pop(0)[1]
    if laps_left <= 10:
        return "SOFT"
    if laps_left <= 20:
        return "MEDIUM"
    return "HARD"


def _check_strategy(params, num_laps, start_compound, pit_stops) -> None:
    compounds = [start_compound] + [c for _, c in pit_stops]
    for compound in compounds:
        if compound not in params.wear_per_lap:
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
        "1 stop (SOFT -> HARD)":     ("SOFT", [(25, "HARD")]),
        "1 stop (SOFT -> SOFT)":     ("SOFT", [(30, "SOFT")]),
        "2 stop (SOFT-SOFT-SOFT)":   ("SOFT", [(18, "SOFT"), (40, "SOFT")]),
        "No stop (SOFT), punctures": ("SOFT", []),
        "Late stop, punctures first": ("SOFT", [(40, "HARD")]),
    }

    for name, (start, stops) in strategies.items():
        total, lap_times, stops_taken = predict_race_time(DEFAULT_PARAMS, NUM_LAPS, start, stops)
        print(f"{name:28s} {format_time(total)}   stops = {stops_taken}")
