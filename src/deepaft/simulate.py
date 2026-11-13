"""Simulation scenarios A-D from the dissertation plan (Norman et al. + extensions)."""

from __future__ import annotations

from typing import Literal

import numpy as np


def _mu_nonlinear(z: np.ndarray) -> np.ndarray:
    """Norman et al. Eq. (6) location function."""
    z1, z2, z3, z4 = z[:, 0], z[:, 1], z[:, 2], z[:, 3]
    indicator = ((4 * z3**2 + (z4 - 1) ** 2) > 0.5).astype(float)
    return (
        1.2
        + 1.5 * z1
        + 0.8 * np.sin(3 * np.pi * z2)
        + 1.7 * z2**3
        - 1.2 * z2 * z4
        + 0.2 * np.abs(z2) * z4
        + 1.2 * indicator
    )


def sample_covariates(n: int, seed: int | None = None) -> np.ndarray:
    rng = np.random.default_rng(seed)
    z1 = rng.binomial(1, 0.5, size=n)
    z2 = rng.uniform(-1, 1, size=n)
    z3 = rng.normal(0, 0.5, size=n)
    z4 = rng.uniform(0, 2, size=n)
    return np.column_stack([z1, z2, z3, z4])


def scenario_a(
    n: int = 300,
    sigma: float = 0.5,
    censor_rate: float = 0.4,
    seed: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Scenario A: AFT data, independent censoring (Norman Table 1 style, smaller n).
    """
    rng = np.random.default_rng(seed)
    z = sample_covariates(n, seed=seed)
    mu = _mu_nonlinear(z)
    log_t = mu + rng.normal(0, sigma, size=n)
    time = np.exp(log_t)

    rate = -np.log(1 - censor_rate) / np.median(time)
    censor_time = rng.exponential(1 / rate, size=n)
    observed = np.minimum(time, censor_time)
    event = (time <= censor_time).astype(int)
    return z, observed, event


def scenario_b(
    n: int = 300,
    sigma: float = 0.5,
    seed: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Scenario B: AFT survival, censoring depends on z1 (covariate-dependent follow-up).
    """
    rng = np.random.default_rng(seed)
    z = sample_covariates(n, seed=seed)
    mu = _mu_nonlinear(z)
    log_t = mu + rng.normal(0, sigma, size=n)
    time = np.exp(log_t)

    # shorter follow-up when z1=1
    base_rate = 0.002
    rate = np.where(z[:, 0] == 1, base_rate * 2.5, base_rate)
    censor_time = rng.exponential(1 / rate)
    observed = np.minimum(time, censor_time)
    event = (time <= censor_time).astype(int)
    groups = z[:, 0].astype(int)
    return z, observed, event, groups


def scenario_c(
    n: int = 300,
    sigma: float = 0.5,
    admin_time: float = 800.0,
    seed: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Scenario C: fixed administrative censoring time (degenerate G)."""
    rng = np.random.default_rng(seed)
    z = sample_covariates(n, seed=seed)
    mu = _mu_nonlinear(z)
    log_t = mu + rng.normal(0, sigma, size=n)
    time = np.exp(log_t)
    observed = np.minimum(time, admin_time)
    event = (time <= admin_time).astype(int)
    return z, observed, event


def scenario_d(
    n: int = 300,
    seed: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Scenario D: two residual scales (LGG-like sigma=0.5, GBM-like sigma=1.2).
    """
    rng = np.random.default_rng(seed)
    z = sample_covariates(n, seed=seed)
    mu = _mu_nonlinear(z)
    groups = rng.binomial(1, 0.5, size=n)  # 0=LGG, 1=GBM
    sigmas = np.where(groups == 0, 0.5, 1.2)
    log_t = mu + rng.normal(0, 1, size=n) * sigmas
    time = np.exp(log_t)

    rate = 0.002
    censor_time = rng.exponential(1 / rate, size=n)
    observed = np.minimum(time, censor_time)
    event = (time <= censor_time).astype(int)
    return z, observed, event, groups


def scenario_ph(
    n: int = 300,
    censor_rate: float = 0.3,
    seed: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """PH model (Norman Eq. 7) for misspecification robustness checks."""
    rng = np.random.default_rng(seed)
    z = sample_covariates(n, seed=seed)
    mu = _mu_nonlinear(z)
    eta = mu - 1.2

    # generate from PH via inversion on fine grid
    u = rng.uniform(0, 1, size=n)
    grid = np.linspace(0.01, 5000, 5000)
    times = np.empty(n)
    for i in range(n):
        baseline = np.exp(-5 + 2.5 * np.cos(np.pi * grid) + 0.5 * grid**0.3)
        hazard = baseline * np.exp(eta[i])
        cumhaz = np.cumsum(hazard) * (grid[1] - grid[0])
        surv = np.exp(-cumhaz)
        idx = np.searchsorted(surv, u[i])
        times[i] = grid[min(idx, len(grid) - 1)]

    rate = -np.log(1 - censor_rate) / np.median(times)
    censor_time = rng.exponential(1 / rate, size=n)
    observed = np.minimum(times, censor_time)
    event = (times <= censor_time).astype(int)
    return z, observed, event
