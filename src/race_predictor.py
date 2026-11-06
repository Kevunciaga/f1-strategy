"""
race_predictor.py - Predict total race time for a strategy.

The predictor owns base lap time and pit loss. For each lap it asks the tyre
model and the fuel model for their time penalties and sums everything up.

The strategy (starting tyre and planned pit stops) is a Strategy from
strategy.py.

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
from strategy import PitStop, Strategy
from tyre_model import has_punctured, tyre_penalty


def predict_race_time(params: Params, num_laps: int, strategy: Strategy
                      ) -> tuple[float, list[float], list[PitStop]]:
    """Return (total_race_time, lap_times, stops_taken) for a strategy.

    stops_taken lists every stop actually made, including forced ones and
    stops that were moved earlier.
    """
    strategy.validate(params, num_laps)

    planned = list(strategy.pit_stops)  # stops not yet taken
    compound, tyre_age = strategy.start_compound, 0

    lap_times = []
    stops_taken = []
    for lap in range(1, num_laps + 1):
        lap_time = (params.base_lap_time + tyre_penalty(params, compound, tyre_age)
                    + fuel_penalty(params, lap - 1))

        new_compound = None
        if planned and planned[0].lap == lap:
            new_compound = planned.pop(0).compound
        elif has_punctured(params, compound, tyre_age) and lap < num_laps:
            new_compound = _forced_stop_compound(planned, num_laps - lap)

        if new_compound is None:
            tyre_age += 1
        else:
            lap_time += params.pit_loss
            stops_taken.append(PitStop(lap, new_compound))
            compound, tyre_age = new_compound, 0

        lap_times.append(lap_time)

    return sum(lap_times), lap_times, stops_taken


def _forced_stop_compound(planned: list[PitStop], laps_left: int) -> str:
    """Compound to fit after a puncture. Pulls the next planned stop forward."""
    if planned:
        return planned.pop(0).compound
    if laps_left <= 10:
        return "SOFT"
    if laps_left <= 20:
        return "MEDIUM"
    return "HARD"


def format_time(seconds: float) -> str:
    """Format seconds as H:MM:SS.mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:06.3f}"


if __name__ == "__main__":
    NUM_LAPS = 60

    strategies = {
        "No stop (HARD)":            Strategy("HARD"),
        "1 stop (SOFT -> HARD)":     Strategy("SOFT", (PitStop(25, "HARD"),)),
        "1 stop (SOFT -> SOFT)":     Strategy("SOFT", (PitStop(30, "SOFT"),)),
        "2 stop (SOFT-SOFT-SOFT)":   Strategy("SOFT", (PitStop(18, "SOFT"), PitStop(40, "SOFT"))),
        "No stop (SOFT), punctures": Strategy("SOFT"),
        "Late stop, punctures first": Strategy("SOFT", (PitStop(40, "HARD"),)),
    }

    for name, strategy in strategies.items():
        total, lap_times, stops_taken = predict_race_time(DEFAULT_PARAMS, NUM_LAPS, strategy)
        stops = [(stop.lap, stop.compound) for stop in stops_taken]
        print(f"{name:28s} {format_time(total)}   stops = {stops}")
