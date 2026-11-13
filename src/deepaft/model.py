"""Neural network for location mu(z) and optional scale sigma(z)."""

from __future__ import annotations

from typing import Literal

import numpy as np
import torch
import torch.nn as nn


class MuMLP(nn.Module):
    """ReLU MLP predicting log-scale location mu(z) (Norman et al. Section 2.1)."""

    def __init__(
        self,
        input_dim: int,
        hidden: tuple[int, ...] = (8, 6),
        scale_mode: Literal["constant", "group", "network"] = "constant",
        n_groups: int = 1,
    ) -> None:
        super().__init__()
        self.scale_mode = scale_mode
        layers: list[nn.Module] = []
        prev = input_dim
        for h in hidden:
            layers.extend([nn.Linear(prev, h), nn.ReLU()])
            prev = h
        self.backbone = nn.Sequential(*layers) if layers else nn.Identity()
        self.mu_head = nn.Linear(prev if hidden else input_dim, 1)

        if scale_mode == "network":
            self.log_sigma_head = nn.Linear(prev if hidden else input_dim, 1)
        elif scale_mode == "group":
            self.group_log_sigma = nn.Parameter(torch.zeros(n_groups))
        else:
            self.log_sigma = nn.Parameter(torch.zeros(1))

    def forward(
        self,
        x: torch.Tensor,
        group_idx: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if isinstance(self.backbone, nn.Identity):
            h = x
        else:
            h = self.backbone(x)
        mu = self.mu_head(h).squeeze(-1)
        if self.scale_mode == "network":
            log_sigma = self.log_sigma_head(h).squeeze(-1)
        elif self.scale_mode == "group":
            if group_idx is None:
                raise ValueError("group_idx required when scale_mode='group'")
            log_sigma = self.group_log_sigma[group_idx.long()]
        else:
            log_sigma = self.log_sigma.expand_as(mu)
        sigma = torch.exp(log_sigma)
        return mu, sigma


def standardize_features(
    X: np.ndarray,
    mean: np.ndarray | None = None,
    std: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = np.asarray(X, dtype=np.float64)
    if mean is None:
        mean = X.mean(axis=0)
    if std is None:
        std = X.std(axis=0)
    std = np.where(std < 1e-8, 1.0, std)
    return (X - mean) / std, mean, std
