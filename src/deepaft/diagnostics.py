"""Diagnostics and automatic method selection."""

from __future__ import annotations

from typing import Literal

import numpy as np

from deepaft.censoring import check_ghat_degeneracy
from deepaft.methods import MethodName


def select_method(
    time: np.ndarray,
    event: np.ndarray,
    requested: MethodName,
    *,
    auto_fallback: bool = True,
) -> tuple[MethodName, str | None]:
    """
    Apply degeneracy guard: IPCW/Transform fall back to buckley_james when invalid.
    """
    if requested == "buckley_james":
        return requested, None
    valid, reason = check_ghat_degeneracy(time, event)
    if valid:
        return requested, None
    if auto_fallback:
        return "buckley_james", reason
    raise ValueError(f"method '{requested}' invalid: {reason}")


def proportional_hazards_test(
    time: np.ndarray,
    event: np.ndarray,
    X: np.ndarray,
) -> tuple[float, float]:
    """
    Global Grambsch-Therneau test via lifelines (optional dependency).

    Returns (chi2, p_value). Raises ImportError if lifelines is missing.
    """
    try:
        from lifelines.statistics import proportional_hazard_test
    except ImportError as exc:
        raise ImportError(
            "Install lifelines for PH testing: pip install deepaft[metrics]"
        ) from exc

    import pandas as pd

    df = pd.DataFrame(X, columns=[f"x{i}" for i in range(X.shape[1])])
    df["time"] = time
    df["event"] = event
    result = proportional_hazard_test(
        df,
        time_col="time",
        event_col="event",
    )
    return float(result.test_statistic), float(result.p_value)
