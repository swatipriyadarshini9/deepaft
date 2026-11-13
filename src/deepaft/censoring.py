"""Kaplan-Meier and inverse censoring probability utilities."""

from __future__ import annotations

from typing import Literal

import numpy as np


def _prepare_survival(
    time: np.ndarray,
    event: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    time = np.asarray(time, dtype=np.float64).ravel()
    event = np.asarray(event, dtype=np.int64).ravel()
    if time.shape[0] != event.shape[0]:
        raise ValueError("time and event must have the same length")
    if np.any(time <= 0):
        raise ValueError("survival times must be strictly positive")
    return time, event


def kaplan_meier(
    time: np.ndarray,
    event: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (unique_times, survival_probabilities) for right-censored data."""
    time, event = _prepare_survival(time, event)
    order = np.argsort(time, kind="mergesort")
    time = time[order]
    event = event[order]

    unique_times: list[float] = []
    survival: list[float] = []
    s = 1.0
    n_at_risk = len(time)
    i = 0
    while i < len(time):
        t = time[i]
        d = 0
        c = 0
        while i < len(time) and time[i] == t:
            if event[i] == 1:
                d += 1
            else:
                c += 1
            i += 1
        if d > 0:
            s *= 1.0 - d / max(n_at_risk, 1)
            unique_times.append(float(t))
            survival.append(float(s))
        n_at_risk -= d + c

    if not unique_times:
        return np.array([0.0]), np.array([1.0])

    return np.asarray(unique_times), np.asarray(survival)


def km_survival_at(
    query: np.ndarray,
    km_times: np.ndarray,
    km_surv: np.ndarray,
) -> np.ndarray:
    """Step-function survival S(t) from a KM curve."""
    query = np.asarray(query, dtype=np.float64)
    out = np.ones_like(query, dtype=np.float64)
    for i, q in enumerate(query):
        idx = np.searchsorted(km_times, q, side="right") - 1
        if idx < 0:
            out[i] = 1.0
        else:
            out[i] = km_surv[idx]
    return out


def censoring_survival(
    time: np.ndarray,
    event: np.ndarray,
    *,
    groups: np.ndarray | None = None,
    mode: Literal["marginal", "covariate"] = "marginal",
) -> np.ndarray:
    """
    Estimate P(C > t) for inverse probability of censoring weights.

    For observed failures, G(t) = P(C > t | Z) when mode='covariate'.
    """
    time, event = _prepare_survival(time, event)
    censor_event = 1 - event  # 1 if censored

    if mode == "marginal" or groups is None:
        km_t, km_s = kaplan_meier(time, censor_event)
        return km_survival_at(time, km_t, km_s)

    groups = np.asarray(groups)
    ghat = np.empty_like(time, dtype=np.float64)
    for g in np.unique(groups):
        mask = groups == g
        km_t, km_s = kaplan_meier(time[mask], censor_event[mask])
        ghat[mask] = km_survival_at(time[mask], km_t, km_s)
    return ghat


def buckley_james_impute(
    time: np.ndarray,
    event: np.ndarray,
    mu: np.ndarray | float = 0.0,
    *,
    groups: np.ndarray | None = None,
    censoring_mode: Literal["marginal", "covariate"] = "marginal",
) -> np.ndarray:
    """
    Buckley-James imputation for censored survival times (Norman et al. Eq. 2-3).

    Residuals v = t / exp(mu) are imputed when delta=0.
    """
    time = np.asarray(time, dtype=np.float64).ravel()
    event = np.asarray(event, dtype=np.int64).ravel()
    mu = np.asarray(mu, dtype=np.float64).ravel()
    if mu.size == 1:
        mu = np.full_like(time, float(mu[0]))
    if mu.shape[0] != time.shape[0]:
        raise ValueError("mu must be scalar or same length as time")

    residual = time / np.exp(mu)
    imputed = time.copy()

    if groups is not None and censoring_mode == "covariate":
        for g in np.unique(groups):
            mask = groups == g
            imputed[mask] = _bj_impute_group(residual[mask], event[mask])
    else:
        imputed = _bj_impute_group(residual, event)

    return imputed * np.exp(mu)


def _bj_impute_group(residual: np.ndarray, event: np.ndarray) -> np.ndarray:
    """
    Buckley-James imputation: E(V | V > v_i) on scaled residuals.

    Uses the KM integral form equivalent to Norman et al. Eq. (2):
    v*_i = v_i + (1/S(v_i)) * integral_{v_i}^{infty} S(u) du
    """
    km_t, km_s = kaplan_meier(residual, event)
    if len(km_t) == 0:
        return residual.copy()

    imputed = residual.copy()
    for i in np.where(event == 0)[0]:
        ri = float(residual[i])
        s_ri = float(km_survival_at(np.array([ri]), km_t, km_s)[0])
        if s_ri <= 1e-10:
            continue
        integral = _km_survival_integral(ri, km_t, km_s)
        imputed[i] = ri + integral / s_ri
    return imputed


def _km_survival_integral(
    start: float,
    km_t: np.ndarray,
    km_s: np.ndarray,
) -> float:
    """Integral from start to infinity of the KM survival step function."""
    s_at = float(km_survival_at(np.array([start]), km_t, km_s)[0])
    lo = start
    integral = 0.0
    for t, s in zip(km_t, km_s):
        if t <= start:
            continue
        integral += (t - lo) * s_at
        lo = t
        s_at = s
    if len(km_t):
        tail = max(km_t[-1], lo)
        integral += (tail - lo) * s_at
    return integral


def fan_gijbels_transform(
    time: np.ndarray,
    event: np.ndarray,
    ghat: np.ndarray | None = None,
) -> tuple[np.ndarray, float]:
    """
    Fan-Gijbels unbiased transformation (Norman et al. Section 2.2).

    Returns transformed times and chosen alpha.
    """
    time, event = _prepare_survival(time, event)
    if ghat is None:
        ghat = censoring_survival(time, event, mode="marginal")
    ghat = np.clip(ghat, 1e-8, 1.0)

    transformed = np.empty_like(time)
    alpha_candidates: list[float] = []

    for i in range(len(time)):
        ti = time[i]
        integral = _integral_g_inverse(time, ghat, ti)
        if event[i] == 1:
            alpha_i = (integral - ti) / (ti / ghat[i]) - integral
            alpha_candidates.append(alpha_i)
        if event[i] == 1:
            alpha = alpha_candidates[-1] if alpha_candidates else 0.0
        else:
            alpha = min(alpha_candidates) if alpha_candidates else 0.0
        phi1 = (1 + alpha) * integral - alpha * ti / ghat[i]
        phi2 = (1 + alpha) * integral
        transformed[i] = event[i] * phi1 + (1 - event[i]) * phi2

    alpha_hat = float(min(alpha_candidates)) if alpha_candidates else 0.0
    return transformed, alpha_hat


def _integral_g_inverse(
    time: np.ndarray,
    ghat: np.ndarray,
    t: float,
) -> float:
    """Integral from 0 to t of 1/G(s) ds using step-function G."""
    order = np.argsort(time)
    sorted_t = time[order]
    sorted_g = ghat[order]
    unique_t = np.unique(sorted_t[sorted_t <= t])
    if len(unique_t) == 0:
        return 0.0
    total = 0.0
    prev = 0.0
    for ut in unique_t:
        g = float(sorted_g[sorted_t == ut][0])
        total += (ut - prev) / max(g, 1e-8)
        prev = ut
    if t > prev:
        g_last = float(sorted_g[sorted_t <= t][-1]) if np.any(sorted_t <= t) else 1.0
        total += (t - prev) / max(g_last, 1e-8)
    return total


def check_ghat_degeneracy(
    time: np.ndarray,
    event: np.ndarray,
    *,
    min_unique_censor_times: int = 3,
    min_ghat: float = 1e-3,
) -> tuple[bool, str]:
    """
    Return (is_valid, reason) for IPCW / Transform methods.

    Invalid when censoring is administrative (too few unique censor times)
    or G hits zero too early.
    """
    time, event = _prepare_survival(time, event)
    censor_times = time[event == 0]
    if len(censor_times) == 0:
        return False, "no censored observations"
    if len(np.unique(censor_times)) < min_unique_censor_times:
        return False, "degenerate administrative censoring (too few unique censor times)"
    ghat = censoring_survival(time, event, mode="marginal")
    if np.any(ghat[event == 1] < min_ghat):
        return False, "G(t) too small for some failure times"
    return True, "ok"
