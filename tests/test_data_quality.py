"""Data quality: suspect flags stay visible and absurd curves trip a guard."""

import json
from pathlib import Path

import numpy as np

from rxnDB.models import Reaction
from rxnDB.store import is_suspect, load_reactions

JSON_DIRECTORY = Path(__file__).resolve().parent.parent / "rxnDB" / "data"


def test_suspect_records_carry_notes():
    for identifier in (
        "jimmy-073", "jimmy-074", "jimmy-045",
        "jimmy-035", "jimmy-060", "jimmy-089",
        "jimmy-091", "jimmy-099", "jimmy-100",
    ):
        record = Reaction.model_validate(json.loads((JSON_DIRECTORY / f"{identifier}.json").read_text()))
        assert is_suspect(record)
        assert record.extensions["verification_note"]


def test_sound_records_are_not_suspect():
    for identifier in ("hp11-001", "jimmy-029", "jimmy-032"):
        record = Reaction.model_validate(json.loads((JSON_DIRECTORY / f"{identifier}.json").read_text()))
        assert not is_suspect(record)


def test_sound_boundaries_stay_within_absurdity_bounds():
    for record in load_reactions():
        if is_suspect(record):
            continue
        for boundary in record.interpreted_boundaries:
            low = boundary.valid_temperature_min_celsius or 400.0
            high = boundary.valid_temperature_max_celsius or 2000.0
            temperature = np.linspace(low, high, 50)
            pressure = (
                boundary.pressure_intercept_gigapascal
                + boundary.pressure_slope_gigapascal_per_celsius * temperature
                + boundary.pressure_curvature_gigapascal_per_celsius_squared * temperature**2
                + boundary.pressure_cubic_gigapascal_per_celsius_cubed * temperature**3
            )
            assert np.max(np.abs(pressure)) < 500, record.reaction_identifier
