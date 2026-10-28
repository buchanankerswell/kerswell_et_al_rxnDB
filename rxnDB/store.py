"""Load and search JSON records. Small database, plain linear scan."""

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
        found = [reaction for reaction in found if wanted & participant_symbols(reaction)]
    if reaction_type:
        found = [reaction for reaction in found if reaction.reaction_type == reaction_type]
    if query:
        tokens = query.lower().split()
        # Words prefixed with `-` drop records holding them; a bare `-`
        # carries no meaning and is ignored.
        excluded = set()
        positives = []
        for token in tokens:
            if token.startswith("-") and len(token) > 1:
                excluded.add(token[1:])
            elif token != "-":
                positives.append(token)
        tokens = positives
        if tokens or excluded:
            # Fuzzy compromise: one word behaves explicitly, while several
            # words keep records holding a combination (two or more) of them
            # and rank the most overlapping records first. Tokens naming a
            # reaction identifier always match that record explicitly.
            known = {reaction.reaction_identifier.lower() for reaction in found}
            names = {token for token in tokens if token in known}
            words = [token for token in tokens if token not in known]
            scored = []
            for reaction in found:
                text = searchable_text(reaction)
                if any(part in text for part in excluded):
                    continue
                if reaction.reaction_identifier.lower() in names:
                    hits = sum(1 for token in tokens if token in text)
                    scored.append((hits, reaction.reaction_identifier, reaction))
                    continue
                if not words:
                    if not tokens:
                        scored.append((0, reaction.reaction_identifier, reaction))
                    continue
                hits = sum(1 for token in words if token in text)
                if hits >= min(2, len(words)):
                    scored.append((hits, reaction.reaction_identifier, reaction))
            scored.sort(key=lambda row: (-row[0], row[1]))
            found = [reaction for _, _, reaction in scored]
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
