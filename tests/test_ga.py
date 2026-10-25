"""Pruebas de ga.run_ga (§6.4, §7) con una aptitud sintética que no depende de model."""
import numpy as np
import pytest

from astroshield import ga, geometry


def toward_origin(sats):
    # Máximo (0) con todos los satélites en (0, 0).
    return -float(np.mean(geometry.central_angle(sats[:, 0], sats[:, 1], 0.0, 0.0)))


def run(seed=0, **params):
    p = {"pop_size": 20, "gens": 15, **params}
    return ga.run_ga(toward_origin, 3, p, np.random.default_rng(seed))


def test_misma_semilla_mismo_resultado():
    best_a, hist_a = run(7)
    best_b, hist_b = run(7)
    assert np.array_equal(best_a, best_b)
    assert hist_a == hist_b


def test_historia_y_forma():
    best, hist = run(gens=15)
    assert best.shape == (3, 2)
    assert [h["gen"] for h in hist] == list(range(16))
    keys = {"gen", "best", "mean", "worst", "diversity", "n_invalid", "n_covered", "best_sats"}
    assert all(keys <= set(h) for h in hist)
    assert all(h["n_covered"] is None for h in hist)
    assert hist[-1]["best_sats"] == best.tolist()


def test_elitismo_no_empeora_y_mejora():
    _, hist = run(3, gens=30)
    bests = [h["best"] for h in hist]
    assert all(b2 >= b1 for b1, b2 in zip(bests, bests[1:]))
    assert bests[-1] > bests[0]


def test_initial_reemplaza_primeros_individuos():
    seed_ind = np.zeros((1, 3, 2))
    _, hist = ga.run_ga(toward_origin, 3, {"pop_size": 10, "gens": 0},
                        np.random.default_rng(0), initial=seed_ind)
    assert hist[0]["best"] == pytest.approx(0.0, abs=1e-9)


def test_stats_fn_se_combina():
    _, hist = ga.run_ga(toward_origin, 3, {"pop_size": 4, "gens": 2}, np.random.default_rng(0),
                        stats_fn=lambda pop, fits: {"n_covered": 1, "extra": len(pop)})
    assert all(h["n_covered"] == 1 and h["extra"] == 4 for h in hist)


def test_menos_inf_cuenta_como_invalido():
    _, hist = ga.run_ga(lambda s: -np.inf, 2, {"pop_size": 4, "gens": 1}, np.random.default_rng(0))
    assert hist[0]["best"] is None and hist[0]["n_invalid"] == 4


@pytest.mark.parametrize("params", [
    {"desconocida": 1}, {"pop_size": 1}, {"elitism": 20}, {"gens": -1},
    {"p_mut": 1.5}, {"tournament_k": 0}, {"sigma_mut": -1.0},
])
def test_parametros_invalidos(params):
    with pytest.raises(ValueError):
        run(**params)
