"""Validator checks: plain names, IMA symbols, physical ranges."""

import pytest
from pydantic import ValidationError

from rxnDB.models import Reaction

VALID = {
    "reaction_identifier": "test-and-ky",
    "reaction_type": "phase_boundary",
    "reactants": [
        {"mineral_symbol": "And", "mineral_name": "andalusite", "chemical_formula": "Al2SiO5", "coefficient": 1.0}
    ],
    "products": [
        {"mineral_symbol": "Ky", "mineral_name": "kyanite", "chemical_formula": "Al2SiO5", "coefficient": 1.0}
    ],
    "observations": [
        {
            "temperature_celsius": 500.0,
            "temperature_uncertainty_celsius": 10.0,
            "pressure_gigapascal": 0.5,
            "pressure_uncertainty_gigapascal": 0.05,
            "pressure_temperature_correlation": 0.2,
            "experimental_outcome": "growth",
            "natural_log_equilibrium_constant": 0.0,
            "natural_log_equilibrium_constant_uncertainty": 0.0,
        }
    ],
    "source": {"authors": ["Test"], "year": 2000, "short_citation": "Test (2000)"},
}


def test_accept_valid_reaction():
    assert Reaction.model_validate(VALID).reaction_identifier == "test-and-ky"


def test_reject_legacy_symbol_with_suggestion():
    record = {**VALID, "reactants": [
        {"mineral_symbol": "q", "mineral_name": "quartz", "chemical_formula": "SiO2", "coefficient": 1.0}
    ]}
    with pytest.raises(ValidationError, match="use 'Qz'"):
        Reaction.model_validate(record)


def test_reject_unknown_symbol():
    record = {**VALID, "reactants": [
        {"mineral_symbol": "Xx", "mineral_name": "nope", "chemical_formula": "Xx", "coefficient": 1.0}
    ]}
    with pytest.raises(ValidationError, match="unknown mineral symbol"):
        Reaction.model_validate(record)


def test_reject_mismatched_name():
    record = {**VALID, "reactants": [
        {"mineral_symbol": "Qz", "mineral_name": "coesite", "chemical_formula": "SiO2", "coefficient": 1.0}
    ]}
    with pytest.raises(ValidationError, match="must pair"):
        Reaction.model_validate(record)


def test_reject_bad_correlation_and_uncertainty():
    bad = {**VALID}
    bad["observations"] = [{**VALID["observations"][0], "pressure_temperature_correlation": 2.0}]
    with pytest.raises(ValidationError):
        Reaction.model_validate(bad)
    bad["observations"] = [{**VALID["observations"][0], "temperature_uncertainty_celsius": -1.0}]
    with pytest.raises(ValidationError):
        Reaction.model_validate(bad)
