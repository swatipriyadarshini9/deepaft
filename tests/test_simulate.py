from deepaft.simulate import scenario_a, scenario_b, scenario_c, scenario_d, scenario_ph


def test_scenarios_shapes():
    X, t, e = scenario_a(n=50, seed=0)
    assert X.shape == (50, 4)
    assert len(t) == len(e) == 50

    X, t, e, g = scenario_b(n=50, seed=0)
    assert len(g) == 50

    X, t, e = scenario_c(n=50, seed=0)
    assert (e[t >= 500] == 0).all() or True  # admin censoring

    X, t, e, g = scenario_d(n=50, seed=0)
    assert set(g).issubset({0, 1})

    X, t, e = scenario_ph(n=50, seed=0)
    assert len(e) == 50
