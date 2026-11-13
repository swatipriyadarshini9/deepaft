"""Training losses for Norman et al. (2024) deepAFT censoring methods."""

from __future__ import annotations

from typing import Literal

import numpy as np
import torch
import torch.nn as nn

from deepaft.censoring import (
    buckley_james_impute,
    censoring_survival,
    fan_gijbels_transform,
)


MethodName = Literal["buckley_james", "ipcw", "transform"]


def prepare_training_targets(
    time: np.ndarray,
    event: np.ndarray,
    mu: np.ndarray,
    method: MethodName,
    *,
    groups: np.ndarray | None = None,
    censoring_mode: Literal["marginal", "covariate"] = "marginal",
    ghat: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray | None]:
    """
    Return (y_target, sample_weights) for MSE training.

    y_target is log-time (or log transformed time).
    sample_weights is used for IPCW; None otherwise.
    """
    time = np.asarray(time, dtype=np.float64)
    event = np.asarray(event, dtype=np.int64)
    log_time = np.log(time)

    if method == "buckley_james":
        imputed = buckley_james_impute(
            time,
            event,
            mu,
            groups=groups,
            censoring_mode=censoring_mode,
        )
        return np.log(imputed), None

    if method == "ipcw":
        if ghat is None:
            ghat = censoring_survival(time, event, groups=groups, mode=censoring_mode)
        weights = np.zeros_like(time, dtype=np.float64)
        weights[event == 1] = 1.0 / np.clip(ghat[event == 1], 1e-8, None)
        return log_time, weights

    if method == "transform":
        transformed, _ = fan_gijbels_transform(time, event, ghat=ghat)
        return np.log(np.clip(transformed, 1e-8, None)), None

    raise ValueError(f"unknown method: {method}")


class IPCWMSELoss(nn.Module):
    """Adjusted MSE loss (Norman et al. Eq. 4)."""

    def forward(
        self,
        mu_pred: torch.Tensor,
        y: torch.Tensor,
        weights: torch.Tensor | None,
    ) -> torch.Tensor:
        if weights is None:
            return torch.mean((y - mu_pred) ** 2)
        return torch.sum(weights * (y - mu_pred) ** 2) / torch.sum(weights)
