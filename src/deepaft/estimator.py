"""Main DeepAFT estimator (Norman et al. 2024 + limitation-aware options)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import torch
import torch.nn as nn

from deepaft.censoring import censoring_survival
from deepaft.diagnostics import select_method
from deepaft.methods import IPCWMSELoss, MethodName, prepare_training_targets
from deepaft.model import MuMLP, standardize_features
from deepaft.predict import baseline_survival, predict_median_time, predict_survival, restricted_mean_survival


CensoringMode = Literal["marginal", "covariate"]
ScaleMode = Literal["constant", "group", "network"]


@dataclass
class DeepAFTConfig:
    method: MethodName = "buckley_james"
    hidden: tuple[int, ...] = (8, 6)
    censoring: CensoringMode = "marginal"
    scale: ScaleMode = "constant"
    max_outer_iter: int = 10
    tol: float = 1e-3
    epochs: int = 200
    lr: float = 1e-3
    weight_decay: float = 1e-4
    batch_size: int = 64
    auto_fallback: bool = True
    random_state: int = 42
    verbose: bool = False


class DeepAFT:
    """
    Nonlinear accelerated failure time model with neural network mu(z).

    Reproduces Norman et al. (2024) methods:
      - buckley_james (iterative imputation + MSE)
      - ipcw (adjusted MSE, Eq. 4)
      - transform (Fan-Gijbels + MSE)

    Limitation-aware extensions:
      - censoring='covariate' uses G(t|z) for weights/imputation
      - scale='group' or 'network' for heteroscedastic residuals
      - auto_fallback when IPCW/Transform are degenerate
    """

    def __init__(
        self,
        method: MethodName = "buckley_james",
        hidden: tuple[int, ...] = (8, 6),
        *,
        censoring: CensoringMode = "marginal",
        scale: ScaleMode = "constant",
        max_outer_iter: int = 10,
        tol: float = 1e-3,
        epochs: int = 200,
        lr: float = 1e-3,
        weight_decay: float = 1e-4,
        batch_size: int = 64,
        auto_fallback: bool = True,
        random_state: int = 42,
        verbose: bool = False,
    ) -> None:
        self.config = DeepAFTConfig(
            method=method,
            hidden=hidden,
            censoring=censoring,
            scale=scale,
            max_outer_iter=max_outer_iter,
            tol=tol,
            epochs=epochs,
            lr=lr,
            weight_decay=weight_decay,
            batch_size=batch_size,
            auto_fallback=auto_fallback,
            random_state=random_state,
            verbose=verbose,
        )
        self._net: MuMLP | None = None
        self._X_mean: np.ndarray | None = None
        self._X_std: np.ndarray | None = None
        self._km_times: np.ndarray | None = None
        self._km_surv: np.ndarray | None = None
        self._time: np.ndarray | None = None
        self._event: np.ndarray | None = None
        self._mu_train: np.ndarray | None = None
        self._sigma_train: np.ndarray | None = None
        self._group_map: dict[int, int] | None = None
        self._fallback_reason: str | None = None
        self._effective_method: MethodName = method

    def fit(
        self,
        X: np.ndarray,
        time: np.ndarray,
        event: np.ndarray,
        *,
        groups: np.ndarray | None = None,
    ) -> "DeepAFT":
        cfg = self.config
        torch.manual_seed(cfg.random_state)
        np.random.seed(cfg.random_state)

        X = np.asarray(X, dtype=np.float64)
        time = np.asarray(time, dtype=np.float64).ravel()
        event = np.asarray(event, dtype=np.int64).ravel()

        effective, reason = select_method(
            time, event, cfg.method, auto_fallback=cfg.auto_fallback
        )
        self._effective_method = effective
        self._fallback_reason = reason

        X_std, self._X_mean, self._X_std = standardize_features(X)
        self._time = time
        self._event = event

        group_idx = None
        n_groups = 1
        if groups is not None:
            groups_arr = np.asarray(groups).astype(int)
            uniq = np.unique(groups_arr)
            self._group_map = {int(g): i for i, g in enumerate(uniq)}
            group_idx = np.array([self._group_map[int(g)] for g in groups_arr])
            n_groups = len(uniq)
        elif cfg.scale == "group":
            raise ValueError("groups required when scale='group'")

        scale_mode = cfg.scale
        if scale_mode == "group" and groups is None:
            scale_mode = "constant"

        self._net = MuMLP(
            input_dim=X_std.shape[1],
            hidden=cfg.hidden,
            scale_mode=scale_mode,
            n_groups=n_groups,
        )

        if effective == "buckley_james":
            mu = self._fit_buckley_james(X_std, time, event, group_idx, groups)
        else:
            mu = self._fit_single_pass(X_std, time, event, group_idx, groups, effective)

        self._mu_train = mu
        sigma = self._predict_sigma(X_std, group_idx)
        self._sigma_train = sigma
        self._km_times, self._km_surv = baseline_survival(time, event, mu, sigma)
        return self

    def _fit_buckley_james(
        self,
        X: np.ndarray,
        time: np.ndarray,
        event: np.ndarray,
        group_idx: np.ndarray | None,
        groups: np.ndarray | None,
    ) -> np.ndarray:
        cfg = self.config
        mu_old = np.zeros(len(time))
        mu = mu_old.copy()

        for outer in range(cfg.max_outer_iter):
            y, weights = prepare_training_targets(
                time,
                event,
                mu,
                "buckley_james",
                groups=groups,
                censoring_mode=cfg.censoring,
            )
            mu = self._train_network(X, y, weights, group_idx)
            delta = float(np.max(np.abs(mu - mu_old)))
            if cfg.verbose:
                print(f"BJ outer {outer + 1}: max |Δmu| = {delta:.6f}")
            if delta <= cfg.tol:
                break
            mu_old = mu.copy()
        return mu

    def _fit_single_pass(
        self,
        X: np.ndarray,
        time: np.ndarray,
        event: np.ndarray,
        group_idx: np.ndarray | None,
        groups: np.ndarray | None,
        method: MethodName,
    ) -> np.ndarray:
        ghat = censoring_survival(
            time, event, groups=groups, mode=self.config.censoring
        )
        y, weights = prepare_training_targets(
            time,
            event,
            np.zeros(len(time)),
            method,
            groups=groups,
            censoring_mode=self.config.censoring,
            ghat=ghat,
        )
        return self._train_network(X, y, weights, group_idx)

    def _train_network(
        self,
        X: np.ndarray,
        y: np.ndarray,
        weights: np.ndarray | None,
        group_idx: np.ndarray | None,
    ) -> np.ndarray:
        cfg = self.config
        assert self._net is not None

        X_t = torch.as_tensor(X, dtype=torch.float32)
        y_t = torch.as_tensor(y, dtype=torch.float32)
        w_t = (
            torch.as_tensor(weights, dtype=torch.float32)
            if weights is not None
            else None
        )
        g_t = (
            torch.as_tensor(group_idx, dtype=torch.long)
            if group_idx is not None
            else None
        )

        opt = torch.optim.Adam(
            self._net.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay
        )
        loss_fn = IPCWMSELoss()
        n = len(y)
        idx = np.arange(n)

        self._net.train()
        for epoch in range(cfg.epochs):
            np.random.shuffle(idx)
            for start in range(0, n, cfg.batch_size):
                batch = idx[start : start + cfg.batch_size]
                xb = X_t[batch]
                yb = y_t[batch]
                gb = g_t[batch] if g_t is not None else None
                wb = w_t[batch] if w_t is not None else None

                opt.zero_grad()
                mu_pred, _ = self._net(xb, gb)
                loss = loss_fn(mu_pred, yb, wb)
                loss.backward()
                opt.step()

            if cfg.verbose and (epoch + 1) % 50 == 0:
                with torch.no_grad():
                    mu_all, _ = self._net(X_t, g_t)
                    print(f"epoch {epoch + 1}: loss={loss_fn(mu_all, y_t, w_t).item():.4f}")

        self._net.eval()
        with torch.no_grad():
            mu, _ = self._net(X_t, g_t)
        return mu.cpu().numpy()

    def _predict_sigma(
        self,
        X: np.ndarray,
        group_idx: np.ndarray | None,
    ) -> np.ndarray:
        assert self._net is not None
        X_t = torch.as_tensor(X, dtype=torch.float32)
        g_t = (
            torch.as_tensor(group_idx, dtype=torch.long)
            if group_idx is not None
            else None
        )
        self._net.eval()
        with torch.no_grad():
            _, sigma = self._net(X_t, g_t)
        return sigma.cpu().numpy()

    def _transform_X(self, X: np.ndarray) -> np.ndarray:
        assert self._X_mean is not None and self._X_std is not None
        X = np.asarray(X, dtype=np.float64)
        return (X - self._X_mean) / self._X_std

    def _group_idx_for_predict(
        self,
        X: np.ndarray,
        groups: np.ndarray | None,
    ) -> np.ndarray | None:
        if self.config.scale != "group" or self._group_map is None:
            return None
        if groups is None:
            return None
        default_idx = 0
        return np.array([
            self._group_map.get(int(g), default_idx) for g in np.asarray(groups).astype(int)
        ])

    def predict_mu(
        self,
        X: np.ndarray,
        *,
        groups: np.ndarray | None = None,
    ) -> np.ndarray:
        assert self._net is not None
        X_std = self._transform_X(X)
        X_t = torch.as_tensor(X_std, dtype=torch.float32)
        g_idx = self._group_idx_for_predict(X, groups)
        g_t = torch.as_tensor(g_idx, dtype=torch.long) if g_idx is not None else None
        self._net.eval()
        with torch.no_grad():
            mu, _ = self._net(X_t, g_t)
        return mu.cpu().numpy()

    def predict_time(
        self,
        X: np.ndarray,
        *,
        groups: np.ndarray | None = None,
    ) -> np.ndarray:
        """Expected survival time proxy: median from S(t|z)."""
        X_std = self._transform_X(X)
        mu = self.predict_mu(X, groups=groups)
        assert self._km_times is not None and self._km_surv is not None
        g_idx = self._group_idx_for_predict(X, groups)
        sigma = self._predict_sigma(X_std, g_idx)
        return predict_median_time(mu, self._km_times, self._km_surv, sigma=sigma)

    def predict_survival(
        self,
        X: np.ndarray,
        times: np.ndarray,
        *,
        groups: np.ndarray | None = None,
    ) -> np.ndarray:
        X_std = self._transform_X(X)
        mu = self.predict_mu(X, groups=groups)
        assert self._km_times is not None and self._km_surv is not None
        g_idx = self._group_idx_for_predict(X, groups)
        sigma = self._predict_sigma(X_std, g_idx)
        return predict_survival(times, mu, self._km_times, self._km_surv, sigma=sigma)

    def predict_rmst(
        self,
        X: np.ndarray,
        tau: float,
    ) -> np.ndarray:
        mu = self.predict_mu(X)
        assert self._km_times is not None and self._km_surv is not None
        X_std = self._transform_X(X)
        sigma = self._predict_sigma(X_std, None)
        return restricted_mean_survival(
            mu, self._km_times, self._km_surv, tau, sigma=sigma
        )

    @property
    def effective_method(self) -> MethodName:
        return self._effective_method

    @property
    def fallback_reason(self) -> str | None:
        return self._fallback_reason
