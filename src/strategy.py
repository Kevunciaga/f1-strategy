"""
strategy.py - A race strategy: starting tyre plus planned pit stops.

A PitStop means: pit at the end of `lap` and continue on a fresh tyre of
`compound` from the next lap. Both classes are frozen, so they cannot change
after creation and can be stored in sets and dict keys.
"""

from dataclasses import dataclass

from params import Params


@dataclass(frozen=True)
class PitStop:
    lap: int
    compound: str


@dataclass(frozen=True)
class Strategy:
    start_compound: str
    pit_stops: tuple[PitStop, ...] = ()

    def __post_init__(self):
        # frozen blocks normal assignment; this keeps a list input hashable
        object.__setattr__(self, "pit_stops", tuple(self.pit_stops))

        laps = [stop.lap for stop in self.pit_stops]
        if any(lap < 1 for lap in laps):
            raise ValueError("Pit laps must be 1 or more")
        if laps != sorted(set(laps)):
            raise ValueError("Pit laps must be unique and in increasing order")

    @property
    def compounds(self) -> tuple[str, ...]:
        """Every compound used, in order, starting tyre first."""
        return (self.start_compound, *(stop.compound for stop in self.pit_stops))

    @property
    def num_stops(self) -> int:
        return len(self.pit_stops)

    def stints(self, num_laps: int) -> list[tuple[int, int, str]]:
        """Planned stints as (first_lap, last_lap, compound). Ignores forced stops."""
        stints = []
        first_lap, compound = 1, self.start_compound
        for stop in self.pit_stops:
            stints.append((first_lap, stop.lap, compound))
            first_lap, compound = stop.lap + 1, stop.compound
        stints.append((first_lap, num_laps, compound))
        return stints

    def validate(self, params: Params, num_laps: int) -> None:
        """Raise ValueError if the strategy does not fit this race."""
        for compound in self.compounds:
            if compound not in params.degradation_per_lap:
                raise ValueError(f"Unknown compound: {compound}")
        if any(stop.lap >= num_laps for stop in self.pit_stops):
            raise ValueError(f"Pit laps must be between 1 and {num_laps - 1}")
