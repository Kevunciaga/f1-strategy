"""
track_params.py - Per-track numbers measured from real races.

Each entry is the average over the dry, usable races of that track (see
build_track_table.py, which prints the lines below). TRACKS is read-only at run
time: nobody can change it by accident while the program runs. To change a
number, edit this file.

start_penalty: seconds lap 1 is slower than the model expects (standing start)
pit_in_loss:   seconds lost on the in-lap of a stop
pit_out_loss:  seconds lost on the out-lap (pit lane, stationary time, cold tyres)
pit_lane_time: seconds from pit entry to pit exit. Information only: it is already
               inside the in-lap and out-lap losses and is never added to anything.
start_years:   the races lap 1 was averaged over
pit_years:     the races the pit losses were averaged over

None means "not measured": lap 1 is ignored when a red flag or Safety Car neutralised
it in every available race, so params_for_track keeps the template's value.
"""

from dataclasses import dataclass, replace
from types import MappingProxyType

from params import DEFAULT_PARAMS, Params


@dataclass(frozen=True)
class TrackEstimate:
    start_penalty: float | None
    pit_in_loss: float | None
    pit_out_loss: float | None
    pit_lane_time: float | None
    start_years: tuple[int, ...]
    pit_years: tuple[int, ...]

    @property
    def pit_loss(self) -> float | None:
        """Total cost of one stop, or None if either part is missing."""
        if self.pit_in_loss is None or self.pit_out_loss is None:
            return None
        return self.pit_in_loss + self.pit_out_loss


TRACKS = MappingProxyType({
    # paste lines from build_track_table.py here (2021 to 2025 races only)
    "Zandvoort": TrackEstimate(8.1, 5.2, 19.8, 19.5, (2021, 2022, 2024, 2025), (2021, 2022, 2024, 2025)),
    "Barcelona": TrackEstimate(7.5, 4.6, 19.5, 22.3, (2022, 2023, 2024, 2025), (2022, 2023, 2024, 2025)),
    "Jeddah": TrackEstimate(5.8, 6.8, 20.2, 23.8, (2021, 2023, 2024), (2021, 2023, 2024)),
    "Monaco": TrackEstimate(11.6, 13.4, 3.0, 24.1, (2021, 2025), (2021, 2024, 2025)),
    "Monza": TrackEstimate(6.2, 5.0, 21.8, 24.8, (2022, 2025), (2022, 2025)),
    "Silverstone": TrackEstimate(7.3, 1.6, 21.4, 28.9, (2023,), (2021, 2022, 2023)),
})


def params_for_track(track: str, template: Params = DEFAULT_PARAMS) -> Params:
    """`template` with this track's start penalty and pit loss filled in."""
    if track not in TRACKS:
        raise KeyError(f"No numbers for track {track!r}. Known tracks: {sorted(TRACKS)}")
    estimate = TRACKS[track]
    return replace(
        template,
        start_penalty=template.start_penalty if estimate.start_penalty is None else estimate.start_penalty,
        pit_in_loss=template.pit_in_loss if estimate.pit_in_loss is None else estimate.pit_in_loss,
        pit_out_loss=template.pit_out_loss if estimate.pit_out_loss is None else estimate.pit_out_loss,
    )
