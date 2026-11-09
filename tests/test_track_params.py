from types import MappingProxyType

import pytest

import track_params
from params import DEFAULT_PARAMS
from track_params import TRACKS, TrackEstimate, params_for_track


def test_tracks_cannot_be_changed_at_run_time():
    with pytest.raises(TypeError):
        TRACKS["Nowhere"] = TrackEstimate(1.0, 2.0, (2021,), (2021,))


def test_track_entries_cannot_be_changed_at_run_time():
    entry = next(iter(TRACKS.values()))
    with pytest.raises(Exception):
        entry.start_penalty = 99.0


def test_params_for_track_fills_in_start_penalty_and_pit_loss():
    track = next(name for name, e in TRACKS.items() if e.start_penalty is not None and e.pit_loss is not None)
    params = params_for_track(track)
    assert params.start_penalty == TRACKS[track].start_penalty
    assert params.pit_loss == TRACKS[track].pit_loss


def test_params_for_track_keeps_everything_else_from_the_template():
    track = next(iter(TRACKS))
    params = params_for_track(track)
    assert params.degradation_per_lap == DEFAULT_PARAMS.degradation_per_lap
    assert params.seconds_per_kg == DEFAULT_PARAMS.seconds_per_kg
    assert params.base_lap_time == DEFAULT_PARAMS.base_lap_time


def test_a_missing_number_keeps_the_template_value(monkeypatch):
    fake = MappingProxyType({"Nowhere": TrackEstimate(None, 22.0, (), (2021,))})
    monkeypatch.setattr(track_params, "TRACKS", fake)
    params = track_params.params_for_track("Nowhere")
    assert params.start_penalty == DEFAULT_PARAMS.start_penalty
    assert params.pit_loss == 22.0


def test_unknown_track_raises_with_the_known_names():
    with pytest.raises(KeyError, match="Zandvoort"):
        params_for_track("Atlantis")
