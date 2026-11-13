"""Survival function and time predictions from fitted deepAFT models."""

from __future__ import annotations

import numpy as np

from deepaft.censoring import kaplan_meier, km_survival_at


def baseline_survival(
    time: np.ndarray,
    event: np.ndarray,
    mu: np.ndarray,
    sigma: np.ndarray | float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Estimate baseline survival S0 from scaled residuals (Norman et al. Eq. 5).

    T0 = T * exp(-mu); with heteroscedastic scale, use (log T - mu) / sigma.
    """
    time = np.asarray(time, dtype=np.float64)
    event = np.asarray(event, dtype=np.int64)
    mu = np.asarray(mu, dtype=np.float64)
    sigma = np.asarray(sigma, dtype=np.float64)
    if sigma.size == 1:
        sigma = np.full_like(mu, float(sigma))

    log_residual = (np.log(time) - mu) / np.clip(sigma, 1e-8, None)
    residual = np.exp(log_residual)
    return kaplan_meier(residual, event)


def predict_survival(
    times: np.ndarray,
    mu: np.ndarray,
    km_times: np.ndarray,
    km_surv: np.ndarray,
    sigma: np.ndarray | float = 1.0,
) -> np.ndarray:
    """
    S(t | z) = S0((t * exp(-mu))^(1/sigma)) under log-scale heterogeneity.

    Returns array of shape (n_samples, n_times).
    """
    times = np.asarray(times, dtype=np.float64)
    mu = np.asarray(mu, dtype=np.float64)
    sigma = np.asarray(sigma, dtype=np.float64)
    if sigma.size == 1:
        sigma = np.full_like(mu, float(sigma))

    out = np.zeros((len(mu), len(times)), dtype=np.float64)
    for i in range(len(mu)):
        scaled = (times * np.exp(-mu[i])) ** (1.0 / np.clip(sigma[i], 1e-8, None))
        out[i] = km_survival_at(scaled, km_times, km_surv)
    return out


def _baseline_median_residual(km_times: np.ndarray, km_surv: np.ndarray) -> float:
    """Median on residual scale from baseline KM."""
    if len(km_times) == 0:
        return 1.0
    idx = np.where(km_surv <= 0.5)[0]
    if len(idx) == 0:
        return float(km_times[-1])
    return float(km_times[idx[0]])


def predict_median_time(
    mu: np.ndarray,
    km_times: np.ndarray,
    km_surv: np.ndarray,
    sigma: np.ndarray | float = 1.0,
    grid: np.ndarray | None = None,
) -> np.ndarray:
    """
    Median survival time (calendar days) from baseline KM on residual scale.

    Norman et al. Eq. (5): median(T|z) = m0 * exp(mu) with constant scale;
    with heteroscedastic scale: T = exp(mu) * r^sigma.
    """
    mu = np.asarray(mu, dtype=np.float64)
    sigma = np.asarray(sigma, dtype=np.float64)
    if sigma.size == 1:
        sigma = np.full_like(mu, float(sigma))

    r_med = _baseline_median_residual(km_times, km_surv)

    if grid is not None:
        # Optional numerical fallback on calendar grid
        surv = predict_survival(grid, mu, km_times, km_surv, sigma=sigma)
        medians = np.full(len(mu), np.nan)
        for i in range(len(mu)):
            below = np.where(surv[i] <= 0.5)[0]
            if len(below):
                medians[i] = grid[below[0]]
            else:
                medians[i] = np.exp(mu[i]) * (r_med ** sigma[i])
        return medians

    return np.exp(mu) * (r_med ** sigma)


def restricted_mean_survival(
    mu: np.ndarray,
    km_times: np.ndarray,
    km_surv: np.ndarray,
    tau: float,
    sigma: np.ndarray | float = 1.0,
    n_grid: int = 200,
) -> np.ndarray:
    """RMST up to tau (Norman et al. Section 2.3)."""
    grid = np.linspace(0, tau, n_grid)
    surv = predict_survival(grid, mu, km_times, km_surv, sigma=sigma)
    return np.trapz(surv, grid, axis=1)
