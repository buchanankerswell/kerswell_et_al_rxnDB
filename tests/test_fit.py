"""Fit math: slope recovery, error handling, candidate ranking."""

import pytest

from rxnDB.fit import evaluate_line, fit_line, rank_candidates, sample_boundary


def test_fit_recovers_slope():
    temperatures = [400.0, 500.0, 600.0, 700.0]
    pressures = [1.0 + 0.002 * t for t in temperatures]
    fit = fit_line(temperatures, pressures, [5.0] * 4, [0.02] * 4)
    assert fit["slope"] == pytest.approx(0.002, rel=0.05)
    assert fit["slope_variance"] > 0


def test_fit_exact_two_points():
    fit = fit_line([450.0, 550.0], [0.4, 0.6], [15.0, 15.0], [0.05, 0.05])
    assert fit["slope"] == pytest.approx(0.002)
    assert fit["observation_count"] == 2


def test_fit_rejects_degenerate_input():
    with pytest.raises(ValueError, match="at least 2"):
        fit_line([500.0], [0.5])
    with pytest.raises(ValueError, match="must spread"):
        fit_line([500.0, 500.0], [0.4, 0.6])


def test_ranking_prefers_far_extension():
    fit = fit_line([450.0, 550.0], [0.4, 0.6], [15.0, 15.0], [0.05, 0.05])
    ranked = rank_candidates(fit, [500.0, 650.0, 350.0], 10.0, 0.05)
    drops = {row["temperature_celsius"]: row["expected_variance_drop"] for row in ranked}
    assert ranked[0]["temperature_celsius"] in (650.0, 350.0)
    assert drops[500.0] < drops[650.0]
    assert all(row["expected_variance_drop"] >= 0 for row in ranked)


def test_band_grows_from_center():
    fit = fit_line([400.0, 500.0, 600.0], [1.0, 1.2, 1.4], [5.0] * 3, [0.02] * 3)
    rows = {row["temperature"]: row["band"] for row in evaluate_line(fit, [300.0, 500.0, 700.0])}
    assert rows[300.0] > rows[500.0]
    assert rows[700.0] > rows[500.0]


def linear_boundary(intercept=10.256, slope=0.0035, curvature=0.0, cubic=0.0, t_min=650.0, t_max=2000.0, p_min=12.2, p_max=18.0):
    return {
        "pressure_intercept_gigapascal": intercept,
        "pressure_slope_gigapascal_per_celsius": slope,
        "pressure_curvature_gigapascal_per_celsius_squared": curvature,
        "pressure_cubic_gigapascal_per_celsius_cubed": cubic,
        "valid_temperature_min_celsius": t_min,
        "valid_temperature_max_celsius": t_max,
        "valid_pressure_min_gigapascal": p_min,
        "valid_pressure_max_gigapascal": p_max,
    }


def test_sample_boundary_keeps_valid_range():
    samples = sample_boundary(linear_boundary())
    assert len(samples) == 40
    assert all(s["pressure_gigapascal"] is not None for s in samples)
    assert all(12.2 <= s["pressure_gigapascal"] <= 18.0 for s in samples)


def test_sample_boundary_blanks_out_of_range():
    samples = sample_boundary(linear_boundary(p_min=13.0, p_max=14.0))
    kept = [s for s in samples if s["pressure_gigapascal"] is not None]
    assert 0 < len(kept) < 40


def test_sample_boundary_empty_for_corrupt_coefficients():
    samples = sample_boundary(
        linear_boundary(
            intercept=-19.891,
            slope=0.03278,
            curvature=2e-05,
            cubic=8e9,
            t_min=959.0,
            t_max=1304.0,
            p_min=0.0,
            p_max=6.5,
        )
    )
    assert all(s["pressure_gigapascal"] is None for s in samples)
