"""Load and search JSON records. Small corpus, plain linear scan."""

import json
import os
from pathlib import Path

from rxnDB.models import Reaction

DATA_DIRECTORY = Path(__file__).resolve().parent / "data"


def data_directory() -> Path:
    override = os.environ.get("RXNDB_DATA_DIRECTORY")
    return Path(override) if override else DATA_DIRECTORY


def load_reactions(directory: str | Path | None = None) -> list[Reaction]:
    folder = Path(directory) if directory else data_directory()
    reactions = []
    for path in sorted(folder.glob("*.json")):
        reactions.append(Reaction.model_validate(json.loads(path.read_text())))
    return reactions


def search_reactions(
    reactions: list[Reaction],
    mineral_symbol: str | None = None,
    reaction_type: str | None = None,
    query: str | None = None,
) -> list[Reaction]:
    found = reactions
    if mineral_symbol:
        wanted = {s.strip() for s in mineral_symbol.split(",") if s.strip()}
        found = [
            reaction
            for reaction in found
            if wanted & participant_symbols(reaction)
        ]
    if reaction_type:
        found = [reaction for reaction in found if reaction.reaction_type == reaction_type]
    if query:
        needle = query.lower()
        found = [reaction for reaction in found if needle in searchable_text(reaction)]
    return found


def participant_symbols(reaction: Reaction) -> set[str]:
    return {p.mineral_symbol for p in [*reaction.reactants, *reaction.products]}


def is_suspect(reaction: Reaction) -> bool:
    """Records flagged for verification review; the list marks them."""
    return reaction.extensions.get("verification_status") == "suspect"


def searchable_text(reaction: Reaction) -> str:
    parts = [
        reaction.reaction_identifier,
        reaction.source.short_citation,
        *[p.mineral_symbol for p in [*reaction.reactants, *reaction.products]],
        *[p.mineral_name for p in [*reaction.reactants, *reaction.products]],
    ]
    return " ".join(parts).lower()
