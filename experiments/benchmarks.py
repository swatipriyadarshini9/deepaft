"""Baseline survival models for dissertation benchmarks (not shipped on PyPI)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
import pandas as pd


class SurvivalModel(Protocol):
    def fit(self, X: np.ndarray, time: np.ndarray, event: np.ndarray) -> None: ...
    def predict_time(self, X: np.ndarray) -> np.ndarray: ...


@dataclass
class ModelResult:
    name: str
    c_index: float
    amse: float | None = None


def _standardize(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std = np.where(std < 1e-8, 1.0, std)
    return (X - mean) / std, mean, std


class CoxBaseline:
    """Semi-parametric Cox PH via lifelines."""

    def __init__(self) -> None:
        self._model = None
        self._mean: np.ndarray | None = None
        self._std: np.ndarray | None = None

    def fit(self, X: np.ndarray, time: np.ndarray, event: np.ndarray) -> None:
        from lifelines import CoxPHFitter

        Xs, self._mean, self._std = _standardize(X)
        df = pd.DataFrame(Xs, columns=[f"x{i}" for i in range(X.shape[1])])
        df["time"] = time
        df["event"] = event
        self._model = CoxPHFitter(penalizer=0.01)
        self._model.fit(df, duration_col="time", event_col="event")

    def predict_time(self, X: np.ndarray) -> np.ndarray:
        assert self._model is not None and self._mean is not None and self._std is not None
        Xs = (X - self._mean) / self._std
        df = pd.DataFrame(Xs, columns=[f"x{i}" for i in range(X.shape[1])])
        # Median survival from predicted partial hazard
        surv = self._model.predict_survival_function(df)
        times = surv.index.values
        medians = []
        for col in surv.columns:
            s = surv[col].values
            idx = np.searchsorted(s, 0.5)
            medians.append(times[min(idx, len(times) - 1)])
        return np.asarray(medians, dtype=np.float64)


class LogNormalAFTBaseline:
    """Parametric log-normal AFT via lifelines."""

    def __init__(self) -> None:
        self._model = None
        self._mean: np.ndarray | None = None
        self._std: np.ndarray | None = None

    def fit(self, X: np.ndarray, time: np.ndarray, event: np.ndarray) -> None:
        from lifelines import LogNormalAFTFitter

        Xs, self._mean, self._std = _standardize(X)
        df = pd.DataFrame(Xs, columns=[f"x{i}" for i in range(X.shape[1])])
        df["time"] = time
        df["event"] = event
        self._model = LogNormalAFTFitter(penalizer=0.01)
        self._model.fit(df, duration_col="time", event_col="event")

    def predict_time(self, X: np.ndarray) -> np.ndarray:
        assert self._model is not None and self._mean is not None and self._std is not None
        Xs = (X - self._mean) / self._std
        df = pd.DataFrame(Xs, columns=[f"x{i}" for i in range(X.shape[1])])
        return self._model.predict_expectation(df).values.ravel()


class RSFBaseline:
    """Random survival forest via scikit-survival."""

    def __init__(self, n_estimators: int = 100, random_state: int = 42) -> None:
        self.n_estimators = n_estimators
        self.random_state = random_state
        self._model = None
        self._mean: np.ndarray | None = None
        self._std: np.ndarray | None = None

    def fit(self, X: np.ndarray, time: np.ndarray, event: np.ndarray) -> None:
        from sksurv.ensemble import RandomSurvivalForest

        Xs, self._mean, self._std = _standardize(X)
        y = np.array(
            [(bool(e), float(t)) for t, e in zip(time, event)],
            dtype=[("event", bool), ("time", float)],
        )
        self._model = RandomSurvivalForest(
            n_estimators=self.n_estimators,
            random_state=self.random_state,
            n_jobs=-1,
        )
        self._model.fit(Xs, y)

    def predict_time(self, X: np.ndarray) -> np.ndarray:
        assert self._model is not None and self._mean is not None and self._std is not None
        Xs = (X - self._mean) / self._std
        surv_fns = self._model.predict_survival_function(Xs)
        medians = []
        for fn in surv_fns:
            times = fn.x
            probs = fn.y
            idx = np.searchsorted(probs, 0.5)
            medians.append(times[min(idx, len(times) - 1)])
        return np.asarray(medians, dtype=np.float64)


class DeepSurvBaseline:
    """Minimal DeepSurv-style Cox partial likelihood network."""

    def __init__(
        self,
        hidden: tuple[int, ...] = (8, 4),
        epochs: int = 100,
        lr: float = 1e-3,
        random_state: int = 42,
    ) -> None:
        self.hidden = hidden
        self.epochs = epochs
        self.lr = lr
        self.random_state = random_state
        self._net = None
        self._mean: np.ndarray | None = None
        self._std: np.ndarray | None = None

    def fit(self, X: np.ndarray, time: np.ndarray, event: np.ndarray) -> None:
        import torch
        import torch.nn as nn

        torch.manual_seed(self.random_state)
        Xs, self._mean, self._std = _standardize(X)
        X_t = torch.as_tensor(Xs, dtype=torch.float32)
        time_t = torch.as_tensor(time, dtype=torch.float32)
        event_t = torch.as_tensor(event, dtype=torch.float32)

        layers: list[nn.Module] = []
        prev = X.shape[1]
        for h in self.hidden:
            layers.extend([nn.Linear(prev, h), nn.ReLU()])
            prev = h
        layers.append(nn.Linear(prev, 1))
        self._net = nn.Sequential(*layers)
        opt = torch.optim.Adam(self._net.parameters(), lr=self.lr)

        for _ in range(self.epochs):
            opt.zero_grad()
            risk = self._net(X_t).squeeze(-1)
            loss = torch.tensor(0.0)
            n_events = 0
            for i in range(len(time_t)):
                if event_t[i] < 0.5:
                    continue
                n_events += 1
                denom = torch.logsumexp(risk[time_t >= time_t[i]], dim=0)
                loss = loss - (risk[i] - denom)
            if n_events > 0:
                (loss / n_events).backward()
                opt.step()

    def predict_time(self, X: np.ndarray) -> np.ndarray:
        import torch

        assert self._net is not None and self._mean is not None and self._std is not None
        Xs = (X - self._mean) / self._std
        X_t = torch.as_tensor(Xs, dtype=torch.float32)
        self._net.eval()
        with torch.no_grad():
            risk = self._net(X_t).squeeze(-1).numpy()
        # Higher risk => shorter survival; invert for C-index on time
        return -risk


def available_baselines() -> dict[str, type]:
    out: dict[str, type] = {}
    try:
        import lifelines  # noqa: F401

        out["cox"] = CoxBaseline
        out["lognormal"] = LogNormalAFTBaseline
    except ImportError:
        pass
    try:
        import sksurv  # noqa: F401

        out["rsf"] = RSFBaseline
    except ImportError:
        pass
    out["deepsurv"] = DeepSurvBaseline
    return out
