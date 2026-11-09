"""
track_params.py - Per-track numbers measured from real races.

Each entry is the average over the dry, usable races of that track (see
build_track_table.py, which prints the lines below). TRACKS is read-only at run
time: nobody can change it by accident while the program runs. To change a
number, edit this file.

start_penalty: seconds lap 1 is slower than the model expects (standing start)
pit_loss:      seconds one pit stop costs (in-lap plus out-lap)
start_years:   the races lap 1 was averaged over
pit_years:     the races the pit stop cost was averaged over

None means "not measured": lap 1 is ignored when a red flag or Safety Car neutralised
it in every available race, so params_for_track keeps the template's value.
"""

from dataclasses import dataclass, replace
from types import MappingProxyType

from params import DEFAULT_PARAMS, Params


@dataclass(frozen=True)
class TrackEstimate:
    start_penalty: float | None
    pit_loss: float | None
    start_years: tuple[int, ...]
    pit_years: tuple[int, ...]


TRACKS = MappingProxyType({
    # paste lines from build_track_table.py here
    "Zandvoort": TrackEstimate(8.2, 24.2, (2021, 2022, 2024), (2021, 2022, 2024)),
    "Barcelona": TrackEstimate(7.8, 24.1, (2022, 2023, 2024), (2022, 2023, 2024)),
    "Jeddah": TrackEstimate(5.8, 27.0, (2021, 2023, 2024), (2021, 2023, 2024)),
    "Monaco": TrackEstimate(12.7, 15.3, (2021,), (2021, 2024)),
    "Monza": TrackEstimate(6.4, 26.1, (2022,), (2022,)),
    "Silverstone": TrackEstimate(7.3, 23.0, (2023,), (2021, 2022, 2023)),
})


def params_for_track(track: str, template: Params = DEFAULT_PARAMS) -> Params:
    """`template` with this track's start penalty and pit loss filled in."""
    if track not in TRACKS:
        raise KeyError(f"No numbers for track {track!r}. Known tracks: {sorted(TRACKS)}")
    estimate = TRACKS[track]
    return replace(
        template,
        start_penalty=template.start_penalty if estimate.start_penalty is None else estimate.start_penalty,
        pit_loss=template.pit_loss if estimate.pit_loss is None else estimate.pit_loss,
    )
