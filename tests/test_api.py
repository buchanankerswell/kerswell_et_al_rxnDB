"""API: the same JSON serves browsers and agents."""

import pytest
from fastapi.testclient import TestClient

from rxnDB.api import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_list_and_fetch():
    records = client.get("/reactions").json()
    assert len(records) >= 626
    identifiers = {record["reaction_identifier"] for record in records}
    assert {"hp11-001", "hp11-010", "jimmy-032"} <= identifiers
    assert len(identifiers) == len(records)
    single = client.get("/reactions/hp11-001").json()
    assert single["reaction_identifier"] == "hp11-001"
    assert client.get("/reactions/missing").status_code == 404


def test_search_by_symbol():
    records = client.get("/reactions", params={"mineral_symbol": "Ky"}).json()
    identifiers = {record["reaction_identifier"] for record in records}
    assert {"jimmy-030", "jimmy-031", "jimmy-032"} <= identifiers
    for record in records:
        symbols = {p["mineral_symbol"] for p in record["reactants"] + record["products"]}
        assert "Ky" in symbols


def test_export_json_only():
    response = client.get("/export", params={"mineral_symbol": "Qz"})
    assert response.headers["content-type"] == "application/json"
    records = response.json()
    assert len(records) > 100
    for record in records:
        symbols = {p["mineral_symbol"] for p in record["reactants"] + record["products"]}
        assert "Qz" in symbols


def test_validate_accepts_and_rejects():
    valid = client.get("/reactions/hp11-001").json()
    assert client.post("/validate", json=valid).status_code == 200
    invalid = {**valid, "reactants": [{"mineral_symbol": "q", "mineral_name": "quartz", "chemical_formula": "SiO2", "coefficient": 1.0}]}
    response = client.post("/validate", json=invalid)
    assert response.status_code == 422
    assert "Qz" in str(response.json())


def test_curve_record_serves_boundaries():
    record = client.get("/reactions/jimmy-032").json()
    assert record["observations"] == []
    assert record["interpreted_boundaries"][0]["pressure_intercept_gigapascal"] == 10.256


def test_fit_boundary_endpoint():
    response = client.post("/fit/boundary", json={"reaction_identifier": "hp11-001"})
    assert response.status_code == 200
    body = response.json()
    assert body["slope_gigapascal_per_celsius"] == pytest.approx(-0.0025)
    assert body["observation_count"] == 2
    assert len(body["line"]) == 20


def test_fit_rejects_curve_only_record():
    response = client.post("/fit/boundary", json={"reaction_identifier": "jimmy-032"})
    assert response.status_code == 422


def test_design_next_point_ranks_extension():
    response = client.post(
        "/design/next-point",
        json={"reaction_identifier": "hp11-001", "candidate_count": 5},
    )
    assert response.status_code == 200
    candidates = response.json()["candidates"]
    assert len(candidates) == 5
    drops = [candidate["expected_variance_drop"] for candidate in candidates]
    assert drops == sorted(drops, reverse=True)
    assert max(drops) > 0


def test_ui_is_canonical_theme_without_plotly():
    page = client.get("/").text
    assert "plot.ly" not in page
    assert 'id="plot"' in page and 'id="plot_tip"' in page
    assert 'id="help"' in page and 'id="help_btn"' in page
    js = client.get("/static/app.js").text
    assert "Plotly" not in js
    assert "clipPath" in js and "data-tip" in js
    assert "Temperature:" in js and "Pressure:" in js and "Phases:" not in js
    assert "PLOT_LIMIT" not in js and "plot_note" not in js
    assert "toggleHelp" in js and "initTheme" in js
    css = client.get("/static/app.css").text
    assert "--link: #3b5cf6" in css and "--hairline" in css


def test_ui_tabs_share_filtering_with_animation():
    for path in ("/", "/observations"):
        response = client.get(path)
        assert response.status_code == 200
        page = response.text
        assert 'data-tab="reactions"' in page
        assert 'data-tab="observations"' in page
        assert 'id="tab_indicator"' in page
        assert 'id="view-reactions"' in page
        assert 'id="view-observations"' in page
        assert 'id="obs_count"' in page
        assert "<th>reaction</th>" in page and "<th>phases</th>" in page
        assert "<th>type</th>" in page and "<th>outcome</th>" not in page
        assert "Phase Diagram" in page and "Pressure&ndash;Temperature" not in page
    css = client.get("/static/app.css").text
    assert "#tab_indicator" in css and "view-in" in css
    js = client.get("/static/app.js").text
    assert "set_tab" in js and "move_tab_indicator" in js
    assert "popstate" in js and "switch-in" in js
    assert "sym-cell" in js and "name-cell" in js
    assert "phase_names" in js and "mineral_name" in js
    assert "reaction_type" in js and "experimental_outcome" not in js


def test_ui_plot_pan_zoom_controls():
    page = client.get("/").text
    assert 'id="plot_reset"' in page
    js = client.get("/static/app.js").text
    assert '"wheel"' in js and '"pointerdown"' in js and '"dblclick"' in js
    assert "reset_view" in js and "request_draw" in js and "draw_cache" in js
    css = client.get("/static/app.css").text
    assert "touch-action: none" in css and ".panning" in css


def test_ui_plot_hover_emphasis_and_ctrl_click_select():
    page = client.get("/").text
    assert 'id="plot_reset"' in page
    js = client.get("/static/app.js").text
    assert 'closest("g.series")' in js and "clear_emphasis" in js
    assert "metaKey" in js and "scrollIntoView" in js
    assert "suppress_click" in js and '"contextmenu"' in js
    assert "down_owner" in js and "select-mod" in js
    css = client.get("/static/app.css").text
    assert "#plot.select-mod" in css
