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
    pit_loss: float = 21.0        # s lost per pit stop

    # Tyre
    seconds_per_health_lost: float = 0.03  # s of lap time per health point lost
    puncture_penalty: float = 40.0         # s added to the lap on which a tyre punctures
    fresh_pace_offset: dict[str, float] = field(  # s slower than soft on a fresh tyre
        default_factory=lambda: {"SOFT": 0.0, "MEDIUM": 0.5, "HARD": 1.0})
    wear_per_lap: dict[str, float] = field(       # health points lost per lap
        default_factory=lambda: {"SOFT": 3.0, "MEDIUM": 2.0, "HARD": 1.0})

    # Fuel
    initial_fuel_load: float = 110.0   # kg at race start
    fuel_burn_per_lap: float = 1.8     # kg burned per lap
    seconds_per_kg: float = 0.03       # s of lap time per kg carried


DEFAULT_PARAMS = Params()
