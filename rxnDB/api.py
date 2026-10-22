"""FastAPI tier. Browsers and agents read the same endpoints."""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from rxnDB import fit as boundary_fit
from rxnDB.models import Reaction
from rxnDB.store import load_reactions, search_reactions

app = FastAPI(title="rxnDB", version="1.0.0")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/reactions", response_model=list[Reaction])
def list_reactions(
    mineral_symbol: str | None = None,
    reaction_type: str | None = None,
    query: str | None = None,
) -> list[Reaction]:
    return search_reactions(load_reactions(), mineral_symbol, reaction_type, query)


@app.get("/reactions/{reaction_identifier}", response_model=Reaction)
def get_reaction(reaction_identifier: str) -> Reaction:
    for reaction in load_reactions():
        if reaction.reaction_identifier == reaction_identifier:
            return reaction
    raise HTTPException(status_code=404, detail=f"unknown reaction {reaction_identifier!r}")


@app.get("/export")
def export_reactions(
    mineral_symbol: str | None = None,
    reaction_type: str | None = None,
    query: str | None = None,
) -> Response:
    records = search_reactions(load_reactions(), mineral_symbol, reaction_type, query)
    payload = json.dumps([record.model_dump() for record in records], indent=2)
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=rxndb-export.json"},
    )


@app.post("/validate", response_model=Reaction)
def validate_reaction(record: Reaction) -> Reaction:
    return record


class FitRequest(BaseModel):
    reaction_identifier: str


class DesignRequest(BaseModel):
    reaction_identifier: str
    temperature_min_celsius: float | None = None
    temperature_max_celsius: float | None = None
    candidate_count: int = Field(default=20, ge=2, le=200)
    assumed_temperature_uncertainty_celsius: float = Field(default=10.0, ge=0)
    assumed_pressure_uncertainty_gigapascal: float = Field(default=0.05, ge=0)


def _fit_for(reaction_identifier: str) -> tuple[Reaction, dict]:
    for reaction in load_reactions():
        if reaction.reaction_identifier == reaction_identifier:
            if len(reaction.observations) < 2:
                raise HTTPException(status_code=422, detail=f"{reaction_identifier!r} holds no fittable point set")
            observations = reaction.observations
            fit = boundary_fit.fit_line(
                [o.temperature_celsius for o in observations],
                [o.pressure_gigapascal for o in observations],
                [o.temperature_uncertainty_celsius for o in observations],
                [o.pressure_uncertainty_gigapascal for o in observations],
                [o.pressure_temperature_correlation for o in observations],
            )
            return reaction, fit
    raise HTTPException(status_code=404, detail=f"unknown reaction {reaction_identifier!r}")


@app.post("/fit/boundary")
def fit_boundary(request: FitRequest) -> dict:
    reaction, fit = _fit_for(request.reaction_identifier)
    temperatures = sorted(o.temperature_celsius for o in reaction.observations)
    low, high = temperatures[0], temperatures[-1]
    grid = [low + (high - low) * i / 19 for i in range(20)]
    return {
        "reaction_identifier": reaction.reaction_identifier,
        "slope_gigapascal_per_celsius": fit["slope"],
        "intercept_gigapascal": fit["intercept"],
        "slope_standard_error": fit["slope_variance"] ** 0.5,
        "intercept_standard_error": fit["intercept_variance"] ** 0.5,
        "observation_count": fit["observation_count"],
        "method": fit["method"],
        "line": [
            {"temperature_celsius": row["temperature"], "pressure_gigapascal": row["pressure"], "band_gigapascal": row["band"]}
            for row in boundary_fit.evaluate_line(fit, grid)
        ],
    }


@app.post("/design/next-point")
def design_next_point(request: DesignRequest) -> dict:
    reaction, fit = _fit_for(request.reaction_identifier)
    temperatures = sorted(o.temperature_celsius for o in reaction.observations)
    low = request.temperature_min_celsius
    high = request.temperature_max_celsius
    if low is None or high is None:
        span = temperatures[-1] - temperatures[0] or 100.0
        low = temperatures[0] - 0.2 * span if low is None else low
        high = temperatures[-1] + 0.2 * span if high is None else high
    grid = [low + (high - low) * i / (request.candidate_count - 1) for i in range(request.candidate_count)]
    candidates = boundary_fit.rank_candidates(
        fit,
        grid,
        request.assumed_temperature_uncertainty_celsius,
        request.assumed_pressure_uncertainty_gigapascal,
    )
    return {"reaction_identifier": reaction.reaction_identifier, "candidates": candidates}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/observations")
def observations_page() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


def main() -> None:
    import uvicorn

    uvicorn.run("rxnDB.api:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
