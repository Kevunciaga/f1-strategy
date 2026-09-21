"""
tyre_model.py — Data-driven F1 tyre degradation model fitted from FastF1.

Pipeline
--------
1. Fetch stint-level lap data from FastF1 for a list of races
2. Strip SC/VSC/red-flag laps, out-laps and in-laps, gross outliers
3. Compute per-stint lap-time deltas relative to the stint's clean baseline
4. Fit a physics-informed degradation curve per compound (SOFT/MEDIUM/HARD)
5. Expose TyreModel.predict(compound, age) for use in race_sim.py

Degradation functional form (per compound):
    Δt(age) = -α·exp(-β·age)  +  γ·age  +  δ·max(0, age − cliff)²

    -α·exp(-β·age)  : warm-up improvement (negative at low age, decays to 0)
     γ·age          : steady linear wear
     δ·(age-cliff)² : cliff — accelerated degradation past critical life
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

try:
    import fastf1
    _FASTF1_AVAILABLE = True
except ImportError:
    _FASTF1_AVAILABLE = False
    warnings.warn("fastf1 not installed — cannot fetch live data. Load from saved params only.")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COMPOUNDS = ("SOFT", "MEDIUM", "HARD")

# TrackStatus codes that mark non-racing laps (SC, SC-ending, red, VSC, VSC-ending)
_DIRTY_STATUS_CODES = frozenset({"2", "3", "4", "5", "6"})

# Fitted parameter names in order
_PARAM_NAMES = ["alpha", "beta", "gamma", "delta", "cliff"]

# Per-compound initial guess  [alpha, beta, gamma,  delta,  cliff]
_P0 = {
    "SOFT":   [0.80, 0.80, 0.120, 0.010, 14.0],
    "MEDIUM": [0.55, 0.60, 0.070, 0.005, 22.0],
    "HARD":   [0.35, 0.45, 0.035, 0.002, 35.0],
}

# Parameter bounds (lower, upper)
_BOUNDS = (
    [0.0,  0.01, 0.0,   0.0,    4.0],   # lower
    [5.0,  8.0,  2.0,   0.5,   60.0],   # upper
)


# ---------------------------------------------------------------------------
# Degradation model
# ---------------------------------------------------------------------------

def _deg_func(age, alpha, beta, gamma, delta, cliff):
    """
    Lap-time delta (seconds) as a function of tyre age.

    Negative → tyre still warming up (car is faster than reference).
    Positive → tyre degradation (car is slower than reference).
    """
    age = np.asarray(age, dtype=float)
    warmup = -alpha * np.exp(-beta * age)
    linear = gamma * age
    cliff_term = delta * np.where(age > cliff, (age - cliff) ** 2, 0.0)
    return warmup + linear + cliff_term


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def _is_clean_lap(status) -> bool:
    """Return True if the track status indicates a normal green-flag lap."""
    if pd.isna(status) or status == "" or status == "1":
        return True
    return not any(c in str(status) for c in _DIRTY_STATUS_CODES)


def _load_race_laps(year: int, gp: str, cache_dir: str) -> pd.DataFrame:
    """
    Load a single race session from FastF1 and return cleaned lap data.

    Returns DataFrame with columns:
        Driver, Stint, LapNumber, TyreLife, Compound, LapTimeSec, GP, Year
    """
    if not _FASTF1_AVAILABLE:
        raise RuntimeError("fastf1 is required to fetch live data.")

    fastf1.Cache.enable_cache(cache_dir)
    session = fastf1.get_session(year, gp, "R")
    session.load(laps=True, telemetry=False, weather=False, messages=False)

    laps = session.laps.copy()

    # Drop laps FastF1 flags as inaccurate
    if "IsAccurate" in laps.columns:
        laps = laps[laps["IsAccurate"] == True]

    # Drop safety-car / VSC / red-flag laps
    if "TrackStatus" in laps.columns:
        laps = laps[laps["TrackStatus"].apply(_is_clean_lap)]

    # Need valid lap time and compound
    laps = laps[laps["LapTime"].notna()]
    laps = laps[laps["Compound"].isin(COMPOUNDS)]

    keep = ["Driver", "Stint", "LapNumber", "TyreLife", "Compound", "LapTime"]
    laps = laps[[c for c in keep if c in laps.columns]].copy()
    laps["LapTimeSec"] = laps["LapTime"].dt.total_seconds()
    laps = laps.drop(columns=["LapTime"])
    laps["GP"] = gp
    laps["Year"] = year

    return laps.reset_index(drop=True)


def fetch_multi_race_data(
    races: list[tuple[int, str]],
    cache_dir: str = "../cache",
) -> pd.DataFrame:
    """
    Fetch and concatenate lap data for multiple races.

    Args:
        races:     list of (year, gp_name) e.g. [(2023, "Monza"), (2023, "Bahrain")]
        cache_dir: FastF1 cache directory path

    Returns:
        Combined DataFrame of all races.
    """
    dfs = []
    for year, gp in races:
        print(f"  Loading {year} {gp}...", end=" ", flush=True)
        try:
            df = _load_race_laps(year, gp, cache_dir)
            print(f"→ {len(df)} laps")
            dfs.append(df)
        except Exception as exc:
            print(f"→ FAILED ({exc})")
            warnings.warn(f"Could not load {year} {gp}: {exc}")

    if not dfs:
        raise RuntimeError("No race data could be loaded.")

    return pd.concat(dfs, ignore_index=True)


# ---------------------------------------------------------------------------
# Preprocessing: stint deltas
# ---------------------------------------------------------------------------

def extract_stint_deltas(laps: pd.DataFrame, min_stint_laps: int = 6) -> pd.DataFrame:
    """
    Convert raw lap times to degradation deltas within each stint.

    For each stint:
      - Drop the first 2 laps (out-lap + warm-up) and last lap (in-lap or final push)
      - Compute baseline = 10th-percentile lap time in the remaining 'core' laps
        (represents the car's clean peak pace on that tyre set)
      - delta = lap_time − baseline for every lap in the stint
      - Reject obvious outliers: −3 s < delta < 10 s

    Returns DataFrame with columns [age, delta, compound].
    """
    records = []

    group_keys = [c for c in ["GP", "Year", "Driver", "Stint"] if c in laps.columns]

    for _, grp in laps.groupby(group_keys):
        grp = grp.sort_values("TyreLife").reset_index(drop=True)
        compound = grp["Compound"].iloc[0]

        if len(grp) < min_stint_laps:
            continue

        times = grp["LapTimeSec"].values
        ages  = grp["TyreLife"].values

        # Core section: skip first 2 and last 1 lap
        core = times[2:-1] if len(times) > 4 else times[1:]
        if len(core) < 2:
            continue

        # 10th percentile of core = near-best clean pace
        baseline = float(np.percentile(core, 10))

        for age, t in zip(ages, times):
            delta = t - baseline
            if -3.0 < delta < 10.0:
                records.append({"age": float(age), "delta": delta, "compound": compound})

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Model fitting
# ---------------------------------------------------------------------------

def _fit_compound(data: pd.DataFrame, compound: str) -> dict:
    """Fit degradation curve for one compound. Returns fit metadata dict."""
    sub = data[data["compound"] == compound].copy()

    if len(sub) < 30:
        raise ValueError(f"Too few samples for {compound}: {len(sub)}")

    ages   = sub["age"].values.astype(float)
    deltas = sub["delta"].values.astype(float)

    try:
        popt, pcov = curve_fit(
            _deg_func,
            ages, deltas,
            p0=_P0[compound],
            bounds=_BOUNDS,
            method="trf",
            maxfev=20000,
        )
        perr = np.sqrt(np.diag(pcov))
    except RuntimeError as exc:
        warnings.warn(f"curve_fit failed for {compound}: {exc}. Using P0 defaults.")
        popt = np.array(_P0[compound])
        perr = np.full(len(_P0[compound]), np.nan)

    residuals = deltas - _deg_func(ages, *popt)
    rmse = float(np.sqrt(np.mean(residuals ** 2)))

    return {
        "compound": compound,
        "n_laps":   int(len(sub)),
        "rmse":     rmse,
        "params":   {n: float(v) for n, v in zip(_PARAM_NAMES, popt)},
        "std_err":  {n: float(v) for n, v in zip(_PARAM_NAMES, perr)},
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class TyreModel:
    """
    Fitted F1 tyre degradation model.

    Quick start
    -----------
    # Fit from FastF1 data (needs internet + cache)
    model = TyreModel()
    model.fit([(2023, "Monza"), (2023, "Bahrain"), (2023, "Silverstone")],
              cache_dir="../cache")
    model.save("tyre_params.json")

    # Load saved params (no internet needed)
    model = TyreModel.load("tyre_params.json")

    # Predict
    delta = model.predict("SOFT", age=15)     # scalar
    deltas = model.predict("MEDIUM", np.arange(0, 30))  # array

    # In race sim
    lap_time = base_pace + model.predict(compound, tyre_age)
    """

    def __init__(self):
        self._fits: dict[str, dict] = {}
        self._meta: dict = {}

    # ------------------------------------------------------------------
    # Fitting
    # ------------------------------------------------------------------

    def fit(
        self,
        races: list[tuple[int, str]],
        cache_dir: str = "../cache",
        min_stint_laps: int = 6,
    ) -> "TyreModel":
        """
        Fetch FastF1 data for `races` and fit compound degradation curves.

        Args:
            races:          list of (year, gp_name) tuples
            cache_dir:      FastF1 cache directory
            min_stint_laps: minimum laps in a stint to include it

        Returns:
            self (for chaining)
        """
        print("=" * 60)
        print("TYRE MODEL — DATA FETCH")
        print("=" * 60)
        laps = fetch_multi_race_data(races, cache_dir=cache_dir)

        print(f"\nTotal laps loaded: {len(laps)}")
        print("\nExtracting stint deltas...")
        data = extract_stint_deltas(laps, min_stint_laps=min_stint_laps)
        print(f"Total degradation samples: {len(data)}")
        print(data["compound"].value_counts().to_string())

        print("\nFitting compound models...")
        print("-" * 60)
        self._fits = {}
        for compound in COMPOUNDS:
            if compound not in data["compound"].values:
                print(f"  {compound}: NO DATA — skipping")
                continue
            try:
                fit = _fit_compound(data, compound)
                self._fits[compound] = fit
                p = fit["params"]
                print(
                    f"  {compound:6s}  n={fit['n_laps']:4d}  RMSE={fit['rmse']:.3f}s  "
                    f"α={p['alpha']:.3f}  β={p['beta']:.3f}  "
                    f"γ={p['gamma']:.4f}  δ={p['delta']:.5f}  cliff={p['cliff']:.1f}"
                )
            except Exception as exc:
                print(f"  {compound:6s}: FIT FAILED — {exc}")

        self._meta = {
            "races":    [(y, gp) for y, gp in races],
            "n_laps":   len(laps),
            "n_samples": len(data),
        }

        print("=" * 60)
        return self

    def fit_track(
        self,
        year: int,
        gp: str,
        cache_dir: str = "../cache",
        fallback: "TyreModel | None" = None,
    ) -> "TyreModel":
        """
        Fit using only data from a single GP — most accurate for that specific circuit.

        Compounds with insufficient data are filled from `fallback` model (e.g. a
        cross-track model) so all three compounds remain available.

        Args:
            year:      season year
            gp:        GP name matching FastF1 e.g. "Monza", "Bahrain"
            cache_dir: FastF1 cache directory
            fallback:  TyreModel to use for missing compounds (optional)

        Returns:
            self (for chaining)
        """
        self.fit([(year, gp)], cache_dir=cache_dir, min_stint_laps=4)

        if fallback is not None:
            for compound in COMPOUNDS:
                if compound not in self._fits:
                    if compound in fallback._fits:
                        self._fits[compound] = fallback._fits[compound]
                        print(f"  {compound}: filled from fallback model")

        return self

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Serialize fitted parameters to JSON."""
        payload = {"meta": self._meta, "fits": self._fits}
        Path(path).write_text(json.dumps(payload, indent=2))
        print(f"Saved → {path}")

    @classmethod
    def load(cls, path: str) -> "TyreModel":
        """Load fitted parameters from a JSON file."""
        payload = json.loads(Path(path).read_text())
        model = cls()
        model._fits = payload.get("fits", payload)   # backward compat
        model._meta = payload.get("meta", {})
        return model

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(self, compound: str, age) -> np.ndarray:
        """
        Predicted lap-time delta (seconds) vs the reference (clean peak pace).

        Negative  → tyre still warming up (car faster than reference)
        ~0        → optimal tyre window
        Positive  → degradation adds time

        Args:
            compound: "SOFT", "MEDIUM", or "HARD" (case-insensitive)
            age:      tyre age in laps — scalar or array-like

        Returns:
            np.ndarray of deltas (same shape as age input, or scalar if scalar input)
        """
        compound = compound.upper()
        if compound not in self._fits:
            available = list(self._fits.keys())
            raise KeyError(f"No params for '{compound}'. Available: {available}")

        p = self._fits[compound]["params"]
        scalar_in = np.ndim(age) == 0
        result = _deg_func(
            np.atleast_1d(np.asarray(age, dtype=float)),
            p["alpha"], p["beta"], p["gamma"], p["delta"], p["cliff"],
        )
        return float(result[0]) if scalar_in else result

    def predict_stint(
        self,
        compound: str,
        start_age: int = 0,
        num_laps: int = 20,
    ) -> np.ndarray:
        """
        Return an array of lap-time deltas for a complete stint.

        Args:
            compound:  "SOFT", "MEDIUM", or "HARD"
            start_age: tyre age at start of stint (0 = brand new)
            num_laps:  number of laps to simulate

        Returns:
            Array shape (num_laps,) with per-lap deltas in seconds.
        """
        ages = np.arange(start_age, start_age + num_laps, dtype=float)
        return self.predict(compound, ages)

    def optimal_age(self, compound: str) -> float:
        """
        Tyre age (laps) at which the compound reaches peak performance
        (minimum lap-time delta — typically after the warm-up phase).
        """
        ages = np.linspace(0, 5, 500)
        deltas = self.predict(compound, ages)
        return float(ages[np.argmin(deltas)])

    def peak_life(self, compound: str, threshold_s: float = 1.5) -> float:
        """
        Tyre age (laps) at which degradation exceeds `threshold_s` seconds
        above the optimal delta. Useful for estimating maximum stint length.
        """
        ages = np.arange(0, 70, dtype=float)
        deltas = self.predict(compound, ages)
        optimal = deltas.min()
        crossings = np.where(deltas > optimal + threshold_s)[0]
        if len(crossings) == 0:
            return float(ages[-1])
        return float(ages[crossings[0]])

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def summary(self) -> str:
        """Print a human-readable summary of fitted parameters."""
        lines = ["TyreModel fitted parameters", "-" * 50]
        for compound, fit in self._fits.items():
            p = fit["params"]
            lines.append(
                f"{compound:6s}  n={fit['n_laps']:4d}  RMSE={fit['rmse']:.3f}s\n"
                f"         α={p['alpha']:.3f}  β={p['beta']:.3f}  "
                f"γ={p['gamma']:.4f}  δ={p['delta']:.5f}  cliff={p['cliff']:.1f}\n"
                f"         optimal_age={self.optimal_age(compound):.1f} laps  "
                f"peak_life(1.5s)={self.peak_life(compound):.0f} laps"
            )
        if not self._fits:
            lines.append("  (no compounds fitted yet)")
        return "\n".join(lines)

    def plot(self, max_age: int = 50, save_path: str | None = None) -> None:
        """
        Plot degradation curves for all fitted compounds.

        Args:
            max_age:   maximum tyre age to plot (laps)
            save_path: if given, save figure to this path instead of showing
        """
        ages = np.linspace(0, max_age, 300)
        colours = {"SOFT": "#E8002D", "MEDIUM": "#FFF200", "HARD": "#FFFFFF"}

        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor("#1a1a2e")
        ax.set_facecolor("#1a1a2e")

        for compound in COMPOUNDS:
            if compound not in self._fits:
                continue
            deltas = self.predict(compound, ages)
            colour = colours.get(compound, "grey")
            ax.plot(ages, deltas, label=compound.capitalize(),
                    color=colour, linewidth=2.5)
            opt = self.optimal_age(compound)
            ax.axvline(opt, color=colour, linestyle=":", alpha=0.4)

        ax.axhline(0, color="white", linewidth=0.6, alpha=0.3)
        ax.set_xlabel("Tyre Age (laps)", color="white")
        ax.set_ylabel("Lap-time delta (s)", color="white")
        ax.set_title("Tyre Degradation Model", color="white", fontsize=14)
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_edgecolor("#444")
        ax.legend(facecolor="#222", labelcolor="white")
        ax.grid(color="#333", linestyle="--", linewidth=0.5)

        plt.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Plot saved → {save_path}")
        else:
            plt.show()
        plt.close(fig)

    def compounds_available(self) -> list[str]:
        return list(self._fits.keys())

    def __repr__(self) -> str:
        if not self._fits:
            return "TyreModel(unfitted)"
        return f"TyreModel(compounds={self.compounds_available()})"


# ---------------------------------------------------------------------------
# CLI — run this file directly to fit and save a model
# ---------------------------------------------------------------------------

DEFAULT_RACES = [
    (2023, "Bahrain"),
    (2023, "Saudi Arabia"),
    (2023, "Australia"),
    (2023, "Azerbaijan"),
    (2023, "Spain"),
    (2023, "Canada"),
    (2023, "Silverstone"),
    (2023, "Hungary"),
    (2023, "Netherlands"),
    (2023, "Monza"),
    (2023, "Singapore"),
    (2023, "Japan"),
    (2023, "Abu Dhabi"),
]


if __name__ == "__main__":
    import argparse
    import os
    import sys

    parser = argparse.ArgumentParser(description="Fit F1 tyre degradation model from FastF1")
    parser.add_argument("--output", default="tyre_params.json",
                        help="Output JSON file for fitted parameters")
    parser.add_argument("--cache", default="../cache",
                        help="FastF1 cache directory")
    parser.add_argument("--plot", action="store_true",
                        help="Save a degradation curve plot")
    parser.add_argument("--races", nargs="+", metavar="YEAR:GP",
                        help='Override race list e.g. "2023:Monza" "2023:Bahrain"')
    args = parser.parse_args()

    if args.races:
        races = []
        for r in args.races:
            year_str, gp = r.split(":", 1)
            races.append((int(year_str), gp))
    else:
        races = DEFAULT_RACES

    model = TyreModel()
    model.fit(races, cache_dir=args.cache)

    print()
    print(model.summary())

    model.save(args.output)

    if args.plot:
        plot_path = args.output.replace(".json", "_curves.png")
        model.plot(save_path=plot_path)
