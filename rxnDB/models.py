"""Pydantic models for reaction records. Field names read as plain words."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from rxnDB.registry import check_participant

ReactionType = Literal["phase_boundary", "calibration", "melting_curve", "triple_point"]
Outcome = Literal["growth", "no_growth", "reversal", "synthesis", "unknown"]


class PhaseParticipant(BaseModel):
    mineral_symbol: str
    mineral_name: str
    chemical_formula: str
    coefficient: float = Field(gt=0)

    def canonical_symbol(self) -> str:
        return check_participant(self.mineral_symbol, self.mineral_name, self.chemical_formula)


class Observation(BaseModel):
    temperature_celsius: float
    temperature_uncertainty_celsius: float = Field(ge=0)
    pressure_gigapascal: float
    pressure_uncertainty_gigapascal: float = Field(ge=0)
    pressure_temperature_correlation: float = Field(ge=-1, le=1, default=0.0)
    experimental_outcome: Outcome = "unknown"
    natural_log_equilibrium_constant: float = 0.0
    natural_log_equilibrium_constant_uncertainty: float = Field(ge=0, default=0.0)


class Method(BaseModel):
    description: str = ""
    pressure_calibration: str = ""
    temperature_calibration: str = ""


class InterpretedBoundary(BaseModel):
    """A published P(T) curve stored as coefficients, not sampled points."""

    description: str = ""
    pressure_intercept_gigapascal: float
    pressure_slope_gigapascal_per_celsius: float = 0.0
    pressure_curvature_gigapascal_per_celsius_squared: float = 0.0
    pressure_cubic_gigapascal_per_celsius_cubed: float = 0.0
    valid_temperature_min_celsius: float | None = None
    valid_temperature_max_celsius: float | None = None
    valid_pressure_min_gigapascal: float | None = None
    valid_pressure_max_gigapascal: float | None = None


class Source(BaseModel):
    authors: list[str] = Field(min_length=1)
    year: int | list[int] | None = None
    short_citation: str = ""
    doi: str = ""
    license: str = "unknown"


class Reaction(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    reaction_identifier: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    reaction_type: ReactionType
    reactants: list[PhaseParticipant] = Field(min_length=1)
    products: list[PhaseParticipant] = Field(min_length=1)
    observations: list[Observation] = []
    interpreted_boundaries: list[InterpretedBoundary] = []
    method: Method = Method()
    source: Source
    extensions: dict = {}

    @field_validator("reactants", "products")
    @classmethod
    def _check_phases(cls, phases: list[PhaseParticipant]) -> list[PhaseParticipant]:
        for phase in phases:
            phase.canonical_symbol()
        return phases

    @model_validator(mode="after")
    def _check_has_data(self) -> "Reaction":
        if not self.observations and not self.interpreted_boundaries:
            raise ValueError("record needs observations, interpreted boundaries, or both")
        return self


if __name__ == "__main__":
    import json

    print(json.dumps(Reaction.model_json_schema(), indent=2))
