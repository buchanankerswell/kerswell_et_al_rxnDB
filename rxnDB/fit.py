"""Straight-line P(T) fits and next-point scores.

Pure functions shared by the API and notebooks; nothing here touches HTTP.
Method: weighted least squares with T-error propagation folded into the
weights and iterated to convergence. An approximation, not full ODR, and
the returned method name says so.
"""

from __future__ import annotations

import numpy as np

METHOD_NAME = "iterated_weighted_least_squares"


def fit_line(
    temperatures: list[float],
    pressures: list[float],
    temperature_errors: list[float] | None = None,
    pressure_errors: list[float] | None = None,
    correlations: list[float] | None = None,
) -> dict:
    """Fit :math:`P = P_0 + mT` (pressure from intercept and slope). Units pass through."""
    temperature = np.asarray(temperatures, dtype=float)
    pressure = np.asarray(pressures, dtype=float)
    count = temperature.size
    if count < 2:
        raise ValueError("need at least 2 observations to fit a line")
    if float(np.ptp(temperature)) == 0.0:
        raise ValueError("temperatures must spread to fit a slope")

    variance_t = _variance_array(temperature_errors, count)
    variance_p = _variance_array(pressure_errors, count)
    correlation = np.zeros(count) if correlations is None else np.asarray(correlations, dtype=float)
    covariance = correlation * np.sqrt(variance_t * variance_p)

    if bool(np.all(variance_t == 0.0) and np.all(variance_p == 0.0)):
        return _unweighted_fit(temperature, pressure)

    slope = 0.0
    for _ in range(20):
        effective = variance_p + slope * slope * variance_t - 2.0 * slope * covariance
        weights = 1.0 / np.maximum(effective, 1e-12)
        result = _weighted_fit(temperature, pressure, weights)
        if abs(result["slope"] - slope) < 1e-9:
            slope = result["slope"]
            break
        slope = result["slope"]

    effective = variance_p + slope * slope * variance_t - 2.0 * slope * covariance
    weights = 1.0 / np.maximum(effective, 1e-12)
    result = _weighted_fit(temperature, pressure, weights)
    result["method"] = METHOD_NAME
    return result


def _variance_array(errors: list[float] | None, count: int) -> np.ndarray:
    if errors is None:
        return np.zeros(count)
    return np.square(np.asarray(errors, dtype=float))


def _weighted_fit(temperature: np.ndarray, pressure: np.ndarray, weights: np.ndarray) -> dict:
    total = float(np.sum(weights))
    mean_t = float(np.sum(weights * temperature) / total)
    mean_p = float(np.sum(weights * pressure) / total)
    sxx = float(np.sum(weights * (temperature - mean_t) ** 2))
    if sxx == 0.0:
        raise ValueError("temperatures must spread to fit a slope")
    slope = float(np.sum(weights * (temperature - mean_t) * (pressure - mean_p)) / sxx)
    intercept = mean_p - slope * mean_t
    slope_variance = 1.0 / sxx
    intercept_variance = 1.0 / total + mean_t * mean_t * slope_variance
    slope_intercept_covariance = -mean_t * slope_variance
    return {
        "method": METHOD_NAME,
        "slope": slope,
        "intercept": intercept,
        "slope_variance": slope_variance,
        "intercept_variance": intercept_variance,
        "slope_intercept_covariance": slope_intercept_covariance,
        "mean_temperature": mean_t,
        "observation_count": int(temperature.size),
    }


def _unweighted_fit(temperature: np.ndarray, pressure: np.ndarray) -> dict:
    result = _weighted_fit(temperature, pressure, np.ones_like(temperature))
    count = temperature.size
    predicted = result["intercept"] + result["slope"] * temperature
    residual = float(np.sum((pressure - predicted) ** 2) / max(count - 2, 1))
    for key in ("slope_variance", "intercept_variance", "slope_intercept_covariance"):
        result[key] *= residual
    result["method"] = "ordinary_least_squares"
    return result


def sample_boundary(boundary: dict, count: int = 40) -> list[dict]:
    """Sample a stored P(T) polynomial, blanking points outside valid range.

    Out-of-range samples carry None pressure so plots break the line
    instead of drawing through unphysical segments.
    """
    count = max(count, 2)
    low = boundary["valid_temperature_min_celsius"]
    high = boundary["valid_temperature_max_celsius"]
    if low is None or high is None:
        low, high = 400.0, 1800.0
    floor = boundary["valid_pressure_min_gigapascal"]
    floor = max(floor if floor is not None else 0.0, 0.0)
    ceiling = boundary["valid_pressure_max_gigapascal"]
    samples = []
    for i in range(count):
        temperature = low + (high - low) * i / (count - 1)
        pressure = (
            boundary["pressure_intercept_gigapascal"]
            + boundary["pressure_slope_gigapascal_per_celsius"] * temperature
            + boundary["pressure_curvature_gigapascal_per_celsius_squared"] * temperature**2
            + boundary["pressure_cubic_gigapascal_per_celsius_cubed"] * temperature**3
        )
        if pressure < floor or (ceiling is not None and pressure > ceiling):
            pressure = None
        samples.append({"temperature_celsius": temperature, "pressure_gigapascal": pressure})
    return samples


def evaluate_line(fit: dict, temperatures: list[float], width: float = 1.96) -> list[dict]:
    """Mean pressure and band half-width at each temperature."""
    slope, intercept = fit["slope"], fit["intercept"]
    out = []
    for temperature in temperatures:
        mean = intercept + slope * temperature
        variance = (
            fit["intercept_variance"] + temperature * temperature * fit["slope_variance"] + 2.0 * temperature * fit["slope_intercept_covariance"]
        )
        out.append({"temperature": float(temperature), "pressure": float(mean), "band": float(width * np.sqrt(max(variance, 0.0)))})
    return out


def rank_candidates(
    fit: dict,
    candidate_temperatures: list[float],
    assumed_temperature_error: float = 10.0,
    assumed_pressure_error: float = 0.05,
    assumed_correlation: float = 0.0,
) -> list[dict]:
    """Rank candidate temperatures by expected slope-variance drop.

    Uses the WLS identity :math:`\\mathrm{Var}(\\hat m) = 1/S_{xx}` and adds each candidate with
    its assumed weight. Tbar shift is ignored; the ordering is what matters.
    """
    slope, current = fit["slope"], fit["slope_variance"]
    sxx = 1.0 / current if current > 0 else 0.0
    assumed_variance = (
        assumed_pressure_error**2
        + slope * slope * assumed_temperature_error**2
        - 2.0 * slope * assumed_correlation * assumed_temperature_error * assumed_pressure_error
    )
    weight = 1.0 / max(assumed_variance, 1e-12)
    mean_t = fit["mean_temperature"]
    ranked = []
    for temperature in candidate_temperatures:
        predicted = fit["intercept"] + slope * temperature
        updated = sxx + weight * (temperature - mean_t) ** 2
        new_variance = 1.0 / updated if updated > 0 else current
        ranked.append(
            {
                "temperature_celsius": float(temperature),
                "pressure_gigapascal": float(predicted),
                "expected_slope_variance": float(new_variance),
                "expected_variance_drop": float(max(current - new_variance, 0.0)),
            }
        )
    ranked.sort(key=lambda row: row["expected_variance_drop"], reverse=True)
    return ranked
