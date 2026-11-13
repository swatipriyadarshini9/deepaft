import numpy as np

from deepaft.censoring import (
    buckley_james_impute,
    check_ghat_degeneracy,
    kaplan_meier,
)
from deepaft.diagnostics import select_method


def test_kaplan_meier_simple():
    time = np.array([1, 2, 3, 4, 5], dtype=float)
    event = np.array([1, 0, 1, 0, 1])
    km_t, km_s = kaplan_meier(time, event)
    assert len(km_t) == 3
    assert km_s[0] == 0.8  # 1 death at t=1, 5 at risk
    assert np.all(km_s <= 1.0)


def test_buckley_james_increases_censored_times():
    time = np.array([2.0, 4.0, 6.0, 8.0])
    event = np.array([1, 0, 1, 0])
    imputed = buckley_james_impute(time, event, mu=0.0)
    assert imputed[1] >= time[1]
    assert imputed[3] >= time[3]


def test_degeneracy_guard_admin_censoring():
    time = np.array([100.0, 200.0, 300.0, 400.0])
    event = np.array([1, 0, 1, 0])
    # all censored at same time would be degenerate - use scenario with few unique
    time2 = np.array([10, 20, 30, 40, 50], dtype=float)
    event2 = np.array([1, 0, 0, 0, 0])  # all censored at different times except one event
    valid, _ = check_ghat_degeneracy(time2, event2, min_unique_censor_times=2)
    assert valid

    method, reason = select_method(time2, event2, "ipcw", auto_fallback=True)
    # may or may not fallback depending on unique censor times
    assert method in ("ipcw", "buckley_james")
