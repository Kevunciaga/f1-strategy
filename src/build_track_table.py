"""
build_track_table.py - Download races, measure lap 1 and pit stop cost per track,
print lines to paste into track_params.py.

The paste lines use MAIN_YEARS only. Races under the 2026 regulations are measured
separately and printed beside them with the difference, so new-regulation timings
never move the main average without you deciding that they should.

Races not yet downloaded need an F1 account login (env vars F1_USERNAME and
F1_PASSWORD, set in the same shell line). Downloaded races are cached in cache/
and load without a login afterwards.

Usage (from the project root, inside the venv):
    python src/build_track_table.py
    python src/build_track_table.py Monza Monaco
"""

import sys

from track_estimates import estimate_track, summarise

# name used in track_params.py -> name FastF1 understands
TRACKS = {
    "Zandvoort": "Zandvoort",
    "Barcelona": "Barcelona",
    "Jeddah": "Jeddah",
    "Monaco": "Monaco",
    "Monza": "Monza",
    "Silverstone": "Silverstone",
}
MAIN_YEARS = (2021, 2022, 2023, 2024, 2025)
NEW_REGS_YEARS = (2026,)
YEARS = list(MAIN_YEARS + NEW_REGS_YEARS)


def show(value: float) -> str:
    return "None" if value != value else f"{value:.1f}"   # nan becomes None


def main(names: list[str]) -> None:
    lines = []
    for name in names:
        results = estimate_track(TRACKS[name], YEARS)
        main_results = [(y, e) for y, e in results if y in MAIN_YEARS]
        new_results = [(y, e) for y, e in results if y in NEW_REGS_YEARS]
        print()
        if not main_results:
            print(f"{name}: no usable races in {MAIN_YEARS[0]} to {MAIN_YEARS[-1]}\n")
            continue

        t = summarise(main_results)
        print(f"{name}: {len(main_results)} races {MAIN_YEARS[0]}-{MAIN_YEARS[-1]}: "
              f"lap 1 {show(t.start_penalty)}s (spread {show(t.start_spread)}), "
              f"in-lap {show(t.pit_in_loss)}s, out-lap {show(t.pit_out_loss)}s, "
              f"pit stop {show(t.pit_in_loss + t.pit_out_loss)}s (spread {show(t.pit_spread)}), "
              f"time in pit lane {show(t.pit_lane_time)}s")
        if new_results:
            n = summarise(new_results)
            print(f"{name}: 2026 regulations: lap 1 {show(n.start_penalty)}s ({n.start_penalty - t.start_penalty:+.1f}), "
                  f"in-lap {show(n.pit_in_loss)}s ({n.pit_in_loss - t.pit_in_loss:+.1f}), "
                  f"out-lap {show(n.pit_out_loss)}s ({n.pit_out_loss - t.pit_out_loss:+.1f}) versus the average above")
        print()

        start_years = tuple(y for y, e in main_results if e.start_penalty == e.start_penalty)
        pit_years = tuple(y for y, e in main_results if e.pit_in_loss == e.pit_in_loss)
        lines.append(f'    "{name}": TrackEstimate({show(t.start_penalty)}, {show(t.pit_in_loss)}, '
                     f'{show(t.pit_out_loss)}, {show(t.pit_lane_time)}, {start_years}, {pit_years}),')

    print("Paste into TRACKS in src/track_params.py (2021 to 2025 only):\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1:] or list(TRACKS))
