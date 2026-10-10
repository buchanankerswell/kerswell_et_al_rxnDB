"""Canonical mineral symbols plus legacy aliases.

Symbols marked IMA follow Warr 2021; the rest are provisional single-symbol
forms awaiting verification. Either way the validator accepts exactly one
symbol per phase, so legacy variants fail with a concrete suggestion.
Extend by editing registry.json; no code change needed.
"""

import json
from difflib import get_close_matches
from functools import lru_cache
from pathlib import Path

REGISTRY_PATH = Path(__file__).with_name("registry.json")


@lru_cache(maxsize=1)
def _registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text())


def _phases() -> dict[str, dict[str, str]]:
    return _registry()["phases"]


def _aliases() -> dict[str, str]:
    return _registry()["aliases"]


CANONICAL_PHASES: dict[str, dict[str, str]] = _phases()
LEGACY_ALIASES: dict[str, str] = _aliases()


def symbol_source(symbol: str) -> str:
    """Return IMA, species, or provisional for a canonical symbol."""
    return _phases()[symbol]["symbol_source"]


def normalize_symbol(symbol: str) -> str:
    """Return the canonical symbol or raise with a concrete suggestion."""
    if symbol in _phases():
        return symbol
    if symbol in _aliases():
        target = _aliases()[symbol]
        raise ValueError(f"legacy symbol {symbol!r}: use {target!r}")
    hint = get_close_matches(symbol, list(_phases()), n=1)
    suggestion = f"; did you mean {hint[0]!r}?" if hint else ""
    raise ValueError(f"unknown mineral symbol {symbol!r}{suggestion}")


def check_participant(symbol: str, name: str, formula: str) -> str:
    """Check symbol, name, and formula agree with the registry."""
    canonical = normalize_symbol(symbol)
    entry = _phases()[canonical]
    if name != entry["mineral_name"] or formula != entry["chemical_formula"]:
        raise ValueError(
            f"{canonical!r} must pair {entry['mineral_name']!r} with "
            f"{entry['chemical_formula']!r}; got {name!r} with {formula!r}"
        )
    return canonical
