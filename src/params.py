"""
params.py - Every number the race time model uses, in one place.

The model functions hold the logic. This object holds the numbers. Different
tracks or fitted values are just different Params. All defaults are
placeholders until real data is used.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Params:
    # Race
    base_lap_time: float = 90.0   # s, fastest compound (soft), fresh tyre, empty tank
    pit_in_loss: float = 5.0      # s lost on the in-lap of a pit stop
    pit_out_loss: float = 16.0    # s lost on the out-lap (pit lane, stationary time, cold tyres)
    start_penalty: float = 0.0    # s added to lap 1 (standing start, bunched cars)

    # Tyre
    puncture_penalty: float = 40.0         # s added to the lap on which a tyre punctures
    fresh_pace_offset: dict[str, float] = field(  # s slower than soft on a fresh tyre
        default_factory=lambda: {"SOFT": 0.0, "MEDIUM": 0.5, "HARD": 1.0})
    degradation_per_lap: dict[str, float] = field(  # s lost per lap of tyre age
        default_factory=lambda: {"SOFT": 0.09, "MEDIUM": 0.06, "HARD": 0.03})
    puncture_age: dict[str, int] = field(           # tyre age (laps) at which the tyre punctures
        default_factory=lambda: {"SOFT": 34, "MEDIUM": 50, "HARD": 100})

    # Fuel
    initial_fuel_load: float = 110.0   # kg at race start
    fuel_burn_per_lap: float = 1.8     # kg burned per lap
    seconds_per_kg: float = 0.03       # s of lap time per kg carried


    @property
    def pit_loss(self) -> float:
        """Total time one pit stop costs: in-lap loss plus out-lap loss."""
        return self.pit_in_loss + self.pit_out_loss


DEFAULT_PARAMS = Params()
