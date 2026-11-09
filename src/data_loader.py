"""
data_loader.py - Load a real race from FastF1 and turn it into model inputs.

Two jobs:
- Ground truth: each driver's real Strategy and real race time.
- Training table: clean laps that show normal racing pace.
"""

import pandas as pd

from env_file import load_env_file
from strategy import PitStop, Strategy

# TrackStatus codes: 2 yellow, 4 safety car, 5 red flag, 6 VSC, 7 VSC ending
_DIRTY_STATUS_CODES = set("24567")


def load_race(year: int, event, cache_dir: str = "cache") -> pd.DataFrame:
    """Load race laps from FastF1. `event` is a round number or event name."""
    import fastf1

    load_env_file()   # F1_USERNAME and F1_PASSWORD from .env, if present
    fastf1.Cache.enable_cache(cache_dir)
    try:
        session = fastf1.get_session(year, event, "R")
        session.load(laps=True, telemetry=False, weather=False, messages=False)
        laps = session.laps.copy()
    except Exception as error:
        raise RuntimeError(
            f"Could not load laps for {year} {event}. FastF1 needs an F1 account login "
            f"(env vars F1_USERNAME and F1_PASSWORD) to download recent races that are not cached."
        ) from error
    if isinstance(event, str):
        check_event_matches(session.event, event, year)
    laps["EventName"] = session.event["EventName"]
    laps["LapTimeSec"] = laps["LapTime"].dt.total_seconds()
    return add_tyre_age(laps)


def check_event_matches(info, requested: str, year: int) -> None:
    """FastF1 matches names loosely and returns the nearest race if the requested one did not happen."""
    fields = ("EventName", "OfficialEventName", "Location", "Country")
    haystack = " ".join(str(info[field]) for field in fields).lower()
    if requested.lower() not in haystack:
        raise RuntimeError(f"Asked for {requested!r} in {year}, FastF1 returned {info['EventName']!r}: "
                           f"that race did not take place or the name does not match")


def add_tyre_age(laps: pd.DataFrame) -> pd.DataFrame:
    """Add TyreAge: laps since the stint started. FastF1's TyreLife also counts laps on used start tyres."""
    laps = laps.copy()
    first_lap = laps.groupby(["Driver", "Stint"])["LapNumber"].transform("min")
    laps["TyreAge"] = laps["LapNumber"] - first_lap
    return laps


def has_wet_tyres(laps: pd.DataFrame) -> bool:
    return bool(laps["Compound"].isin(["INTERMEDIATE", "WET"]).any())


def clean_laps(laps: pd.DataFrame) -> pd.DataFrame:
    """Keep laps that show normal pace: no pit laps, no lap 1, no yellow/SC/VSC/red."""
    keep = (
        laps["LapTimeSec"].notna()
        & laps["PitInTime"].isna()
        & laps["PitOutTime"].isna()
        & (laps["LapNumber"] > 1)
        & laps["IsAccurate"]
        & laps["Deleted"].ne(True)
        & ~laps["TrackStatus"].astype(str).apply(lambda s: bool(_DIRTY_STATUS_CODES & set(s)))
    )
    return laps[keep]


def driver_strategy(driver_laps: pd.DataFrame) -> Strategy:
    """Real strategy of one driver: start tyre plus a PitStop at the end of every stint but the last."""
    stints = (
        driver_laps.sort_values("LapNumber")
        .groupby("Stint")
        .agg(compound=("Compound", "first"), last_lap=("LapNumber", "max"))
        .sort_index()
    )
    compounds = stints["compound"].tolist()
    last_laps = stints["last_lap"].astype(int).tolist()
    stops = tuple(PitStop(lap, compound)
                  for lap, compound in zip(last_laps[:-1], compounds[1:]))
    return Strategy(compounds[0], stops)


def driver_race_time(driver_laps: pd.DataFrame) -> float:
    """Total race time in seconds: sum of every lap time."""
    return float(driver_laps["LapTimeSec"].sum())


def estimate_base_pace(clean_driver_laps: pd.DataFrame, n: int = 5) -> float:
    """Crude base pace: mean of the driver's n fastest clean laps. To be replaced by fitting."""
    return float(clean_driver_laps["LapTimeSec"].nsmallest(n).mean())
