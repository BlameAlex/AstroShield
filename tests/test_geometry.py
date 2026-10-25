"""Tests de geometry.py (contrato §6.2, PATCH 1.0.1)."""
import numpy as np
import pytest

from astroshield.geometry import central_angle, wrap_lon


# --- wrap_lon -------------------------------------------------------------

@pytest.mark.parametrize("lon, esperado", [
    (180, -180), (-180, -180), (540, -180), (-190, 170), (0, 0), (359, -1), (-540, -180),
])
def test_wrap_lon_bordes(lon, esperado):
    assert wrap_lon(lon) == esperado


def test_wrap_lon_justo_bajo_menos_180():
    # P1: sin la guarda, np.mod redondea a 360 y el resultado sería 180.0.
    r = wrap_lon(np.nextafter(-180.0, -np.inf))
    assert r == -180.0
    assert -180 <= r < 180


def test_wrap_lon_tipos_y_forma():
    escalar = wrap_lon(5.0)
    assert isinstance(escalar, np.ndarray) and escalar.shape == ()
    lons = np.random.default_rng(0).uniform(-1000, 1000, (3, 4))
    r = wrap_lon(lons)
    assert r.shape == (3, 4)
    assert np.all((r >= -180) & (r < 180))
    assert np.allclose(np.cos(np.radians(r)), np.cos(np.radians(lons)))
    assert np.allclose(np.sin(np.radians(r)), np.sin(np.radians(lons)))


# --- central_angle --------------------------------------------------------

def test_central_angle_mismo_punto():
    assert central_angle(20.5, -89.0, 20.5, -89.0) == pytest.approx(0, abs=1e-12)


def test_central_angle_cruce_antimeridiano():
    assert central_angle(0, 179.9, 0, -179.9) == pytest.approx(0.2, abs=1e-9)


def test_central_angle_polos():
    # P3: en el polo el resultado es ≈ 0 (6e-15), no 0 exacto.
    assert central_angle(90, 0, 90, 123) == pytest.approx(0, abs=1e-12)
    for x in (-170, 0, 45, 179):
        for y in (-170, 0, 45, 179):
            assert central_angle(90, x, 0, y) == pytest.approx(90, abs=1e-9)


def test_central_angle_antipodas():
    assert central_angle(0, 0, 0, 180) == pytest.approx(180, abs=1e-9)
    rng = np.random.default_rng(1)
    lat, lon = rng.uniform(-89, 89, 20), rng.uniform(-180, 180, 20)
    # P3: fuera del ecuador haversine pierde precisión cerca de 180° (~2e-6°).
    assert np.allclose(central_angle(lat, lon, -lat, lon + 180), 180, atol=1e-5)


def test_central_angle_un_grado():
    assert central_angle(0, 0, 1, 0) == pytest.approx(1.0, abs=1e-12)
    assert central_angle(0, 0, 0, 1) == pytest.approx(1.0, abs=1e-12)
    assert np.radians(central_angle(0, 0, 1, 0)) * 6371.0 == pytest.approx(111.19, abs=0.01)


def test_central_angle_propiedades():
    rng = np.random.default_rng(0)
    lat = np.degrees(np.arcsin(rng.uniform(-1, 1, (3, 1000))))
    lon = rng.uniform(-180, 180, (3, 1000))
    ab = central_angle(lat[0], lon[0], lat[1], lon[1])
    ba = central_angle(lat[1], lon[1], lat[0], lon[0])
    bc = central_angle(lat[1], lon[1], lat[2], lon[2])
    ac = central_angle(lat[0], lon[0], lat[2], lon[2])
    assert np.array_equal(ab, ba)
    assert np.all((ab >= 0) & (ab <= 180))
    assert np.all(ac <= ab + bc + 1e-9)


def test_central_angle_broadcasting():
    rng = np.random.default_rng(2)
    sats = np.column_stack((rng.uniform(-90, 90, 8), rng.uniform(-180, 180, 8)))
    regs = np.column_stack((rng.uniform(-90, 90, 6), rng.uniform(-180, 180, 6)))
    m = central_angle(sats[:, 0][:, None], sats[:, 1][:, None], regs[:, 0][None, :], regs[:, 1][None, :])
    assert m.shape == (8, 6)
    esperado = [[float(central_angle(*s, *r)) for r in regs] for s in sats]
    assert np.allclose(m, esperado, rtol=0, atol=1e-12)
    assert isinstance(central_angle(0, 0, 0, 1), np.ndarray)
