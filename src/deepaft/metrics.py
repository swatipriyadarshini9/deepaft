"""Evaluation metrics for censored survival predictions."""

from __future__ import annotations

import numpy as np


def harrell_c_index(
    predicted_time: np.ndarray,
    time: np.ndarray,
    event: np.ndarray,
) -> float:
    """
    Harrell's C-index using predicted survival times.

    Higher predicted time => longer survival (Norman et al. Section 3).
    """
    predicted_time = np.asarray(predicted_time, dtype=np.float64).ravel()
    time = np.asarray(time, dtype=np.float64).ravel()
    event = np.asarray(event, dtype=np.int64).ravel()

    concordant = 0.0
    comparable = 0.0
    n = len(time)
    for i in range(n):
        for j in range(i + 1, n):
            if time[i] == time[j] and event[i] == event[j]:
                continue
            if time[i] < time[j] and event[i] == 1:
                comparable += 1
                if predicted_time[i] < predicted_time[j]:
                    concordant += 1
                elif predicted_time[i] == predicted_time[j]:
                    concordant += 0.5
            elif time[j] < time[i] and event[j] == 1:
                comparable += 1
                if predicted_time[j] < predicted_time[i]:
                    concordant += 1
                elif predicted_time[i] == predicted_time[j]:
                    concordant += 0.5
    if comparable == 0:
        return float("nan")
    return concordant / comparable


def amse(
    predicted_log_time: np.ndarray,
    time: np.ndarray,
    event: np.ndarray,
    ghat: np.ndarray,
) -> float:
    """Adjusted mean squared error on log-time (Norman et al. Eq. 4)."""
    log_time = np.log(time)
    mask = event == 1
    if not np.any(mask):
        return float("nan")
    err = (log_time[mask] - predicted_log_time[mask]) ** 2
    weights = 1.0 / np.clip(ghat[mask], 1e-8, None)
    return float(np.sum(weights * err) / np.sum(weights))


def integrated_brier_score(
    surv_probs: np.ndarray,
    times_grid: np.ndarray,
    time: np.ndarray,
    event: np.ndarray,
) -> float:
    """
    Simple IBS: mean squared error between predicted S(t) and KM target.

    surv_probs: (n_samples, n_times)
    """
    time = np.asarray(time, dtype=np.float64)
    event = np.asarray(event, dtype=np.int64)
    n = len(time)
    ibs = 0.0
    for k, t in enumerate(times_grid):
        y = ((time > t).astype(float))
        ibs += np.mean((surv_probs[:, k] - y) ** 2)
    return ibs / len(times_grid)
