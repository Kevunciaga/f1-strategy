"""
compare_real.py - Feed real strategies of a few drivers to the model and
compare the predicted race time with the real one.

Params are fitted on the clean laps of the same race (fit_params.py), with one
base pace per driver. The fit has seen these laps, so the errors are optimistic:
this is an in-sample check. evaluate.py tests on a different race.
"""

from dataclasses import replace

from data_loader import (clean_laps, driver_race_time, driver_strategy,
                         has_wet_tyres, load_race)
from fit_params import fit_params
from race_predictor import format_time, predict_race_time
from strategy import Strategy

YEAR, EVENT = 2021, "Netherlands"
DRIVERS = ["VER", "HAM", "LEC", "ALO", "NOR"]


def describe(strategy: Strategy, num_laps: int) -> str:
    return " ".join(f"{compound[0]}{first}-{last}"
                    for first, last, compound in strategy.stints(num_laps))


def plot_laps(rows, save_path: str = "plots/compare_real.png") -> None:
    from pathlib import Path

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    Path(save_path).parent.mkdir(exist_ok=True)
    fig, axes = plt.subplots(len(rows), 1, figsize=(9, 2.6 * len(rows)), sharex=True)
    for ax, row in zip(axes, rows):
        laps = range(1, len(row["real_laps"]) + 1)
        ax.plot(laps, row["real_laps"], color="#1a73e8", label="real")
        ax.plot(laps, row["pred_laps"], color="#E8002D", label="model")
        ax.set_ylim(70, 85)
        ax.set_ylabel(f"{row['driver']} lap (s)")
        ax.grid(alpha=0.3)
    axes[0].legend(loc="upper right")
    axes[-1].set_xlabel("Lap")
    fig.tight_layout()
    fig.savefig(save_path, dpi=130)
    plt.close(fig)
    print(f"Plot saved -> {save_path}")


def main() -> None:
    laps = load_race(YEAR, EVENT)
    assert not has_wet_tyres(laps), "wet race, not supported yet"
    clean = clean_laps(laps)
    fitted = fit_params(clean)

    print(f"{YEAR} {EVENT}: {len(laps)} laps, {len(clean)} clean")
    print(f"fitted: {fitted.params.degradation_per_lap}, offsets {fitted.params.fresh_pace_offset}, "
          f"{fitted.params.seconds_per_kg:.4f} s/kg, noise {fitted.noise:.2f} s\n")
    header = f"{'Drv':3} {'Laps':>4}  {'Real':>11} {'Model':>11} {'Error':>8}  Strategy"
    print(header)

    rows = []
    for driver in DRIVERS:
        driver_laps = laps[laps["Driver"] == driver].sort_values("LapNumber")
        num_laps = len(driver_laps)
        strategy = driver_strategy(driver_laps)
        real_time = driver_race_time(driver_laps)

        params = replace(fitted.params, base_lap_time=fitted.driver_base_lap_time[driver])
        predicted, lap_times, stops_taken = predict_race_time(params, num_laps, strategy)

        forced = " (forced stop)" if len(stops_taken) != strategy.num_stops else ""
        print(f"{driver:3} {num_laps:4d}  {format_time(real_time):>11} "
              f"{format_time(predicted):>11} {predicted - real_time:+8.1f}  "
              f"{describe(strategy, num_laps)}{forced}")
        rows.append({"driver": driver, "real_laps": driver_laps["LapTimeSec"].tolist(),
                     "pred_laps": lap_times})

    plot_laps(rows)


if __name__ == "__main__":
    main()
