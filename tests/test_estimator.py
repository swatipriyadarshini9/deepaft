import numpy as np
import pytest

from deepaft import DeepAFT, harrell_c_index
from deepaft.simulate import scenario_a, scenario_b, scenario_c, scenario_d


@pytest.fixture
def small_aft_data():
    X, time, event = scenario_a(n=120, seed=0)
    return X, time, event


def test_fit_buckley_james_runs(small_aft_data):
    X, time, event = small_aft_data
    model = DeepAFT(method="buckley_james", hidden=(8, 4), epochs=30, verbose=False)
    model.fit(X, time, event)
    pred = model.predict_time(X)
    c = harrell_c_index(pred, time, event)
    assert model.effective_method == "buckley_james"
    assert c > 0.55


def test_fit_ipcw_runs(small_aft_data):
    X, time, event = small_aft_data
    model = DeepAFT(method="ipcw", hidden=(8, 4), epochs=30)
    model.fit(X, time, event)
    assert model.effective_method in ("ipcw", "buckley_james")


def test_fit_transform_runs(small_aft_data):
    X, time, event = small_aft_data
    model = DeepAFT(method="transform", hidden=(8, 4), epochs=30)
    model.fit(X, time, event)
    assert model.effective_method in ("transform", "buckley_james")


def test_covariate_censoring_scenario_b():
    X, time, event, groups = scenario_b(n=120, seed=1)
    model = DeepAFT(
        method="buckley_james",
        censoring="covariate",
        hidden=(8, 4),
        epochs=40,
    )
    model.fit(X, time, event, groups=groups)
    pred = model.predict_time(X)
    c = harrell_c_index(pred, time, event)
    assert c > 0.5


def test_admin_censoring_fallback():
    X, time, event = scenario_c(n=100, admin_time=500.0, seed=2)
    model = DeepAFT(method="ipcw", auto_fallback=True, hidden=(6, 4), epochs=20)
    model.fit(X, time, event)
    assert model.effective_method == "buckley_james"
    assert model.fallback_reason is not None


def test_heteroscedastic_scale_group():
    X, time, event, groups = scenario_d(n=120, seed=3)
    model = DeepAFT(
        method="buckley_james",
        scale="group",
        hidden=(8, 4),
        epochs=40,
    )
    model.fit(X, time, event, groups=groups)
    surv = model.predict_survival(
        X[:5], times=np.array([100.0, 500.0]), groups=groups[:5]
    )
    assert surv.shape == (5, 2)
    assert np.all(surv <= 1.0)
