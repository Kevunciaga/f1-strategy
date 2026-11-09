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

        start, start_spread, pit, pit_spread = summarise(main_results)
        print(f"{name}: {len(main_results)} races {MAIN_YEARS[0]}-{MAIN_YEARS[-1]}, "
              f"lap 1 {show(start)}s (spread {show(start_spread)}), "
              f"pit stop {show(pit)}s (spread {show(pit_spread)})")
        if new_results:
            new_start, _, new_pit, _ = summarise(new_results)
            print(f"{name}: 2026 regulations: lap 1 {show(new_start)}s ({new_start - start:+.1f}), "
                  f"pit stop {show(new_pit)}s ({new_pit - pit:+.1f}) versus the average above")
        print()

        start_years = tuple(y for y, e in main_results if e.start_penalty == e.start_penalty)
        pit_years = tuple(y for y, e in main_results if e.pit_stop_cost == e.pit_stop_cost)
        lines.append(f'    "{name}": TrackEstimate({show(start)}, {show(pit)}, {start_years}, {pit_years}),')

    print("Paste into TRACKS in src/track_params.py (2021 to 2025 only):\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1:] or list(TRACKS))
