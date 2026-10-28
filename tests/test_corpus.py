"""Database invariants over the committed JSON records."""

import json
from pathlib import Path

from rxnDB.fit import sample_boundary
from rxnDB.models import Reaction
from rxnDB.registry import CANONICAL_PHASES, LEGACY_ALIASES

JSON_DIRECTORY = Path(__file__).resolve().parent.parent / "rxnDB" / "data"


def load_database() -> list[Reaction]:
    return [Reaction.model_validate(json.loads(path.read_text())) for path in sorted(JSON_DIRECTORY.glob("*.json"))]


def test_database_counts():
    names = [path.name for path in JSON_DIRECTORY.glob("*.json")]
    assert sum(name.startswith("hp11-") for name in names) == 525
    assert sum(name.startswith("jimmy-") for name in names) == 101


def test_database_validates_with_single_symbols():
    legacy_only = set(LEGACY_ALIASES) - set(CANONICAL_PHASES)
    identifiers = set()
    quartz_symbols = set()
    for record in load_database():
        identifiers.add(record.reaction_identifier)
        assert record.observations or record.interpreted_boundaries
        for participant in list(record.reactants) + list(record.products):
            assert participant.mineral_symbol not in legacy_only
            if participant.mineral_name == "quartz":
                quartz_symbols.add(participant.mineral_symbol)
    assert len(identifiers) == 626
    assert quartz_symbols == {"Qz"}


def test_fully_clipped_boundaries_are_documented():
    # Nine stored polynomials never enter their stated pressure limits.
    # Coefficients match the legacy compilation exactly, so these are
    # transcription errors awaiting literature review, not migration bugs.
    # This test fails if the set changes in either direction.
    fully_clipped = set()
    for record in load_database():
        for boundary in record.interpreted_boundaries:
            kept = [s for s in sample_boundary(boundary.model_dump()) if s["pressure_gigapascal"] is not None]
            if not kept:
                fully_clipped.add(record.reaction_identifier)
    assert fully_clipped == {
        "jimmy-035",
        "jimmy-045",
        "jimmy-060",
        "jimmy-073",
        "jimmy-074",
        "jimmy-089",
        "jimmy-091",
        "jimmy-099",
        "jimmy-100",
    }
