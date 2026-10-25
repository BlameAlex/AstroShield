"""Pruebas de restricciones y reparación de constelaciones (§6.5)."""
import numpy as np
import pytest

from astroshield import geometry
from astroshield.constraints import _push_along_great_circle, repair


def test_push_along_great_circle_standard():
    # Zona en Atlántico Norte (45.0, -35.0), satélite en (44.0, -30.0)
    lat_c, lon_c = 45.0, -35.0
    lat_s, lon_s = 44.0, -30.0
    radius = 12.0
    margin = 0.5
    target = radius + margin

    pushed = _push_along_great_circle(lat_s, lon_s, lat_c, lon_c, target)
    assert pushed is not None
    assert pushed.shape == (2,)

    # Distancia al centro debe ser exactamente target (12.5°)
    dist = float(geometry.central_angle(lat_c, lon_c, pushed[0], pushed[1]))
    assert pytest.approx(target, abs=1e-9) == dist


def test_push_along_great_circle_north_pole():
    # Centro en el polo norte (90.0, 0.0), satélite en lat 85.0, lon 45.0
    lat_c, lon_c = 90.0, 0.0
    lat_s, lon_s = 85.0, 45.0
    target = 8.5

    pushed = _push_along_great_circle(lat_s, lon_s, lat_c, lon_c, target)
    assert pushed is not None
    assert pytest.approx(90.0 - target, abs=1e-9) == pushed[0]
    assert pytest.approx(45.0, abs=1e-9) == pushed[1]

    dist = float(geometry.central_angle(lat_c, lon_c, pushed[0], pushed[1]))
    assert pytest.approx(target, abs=1e-9) == dist


def test_push_along_great_circle_south_pole():
    # Centro en el polo sur (-90.0, 0.0), satélite en lat -85.0, lon -120.0
    lat_c, lon_c = -90.0, 0.0
    lat_s, lon_s = -85.0, -120.0
    target = 10.5

    pushed = _push_along_great_circle(lat_s, lon_s, lat_c, lon_c, target)
    assert pushed is not None
    assert pytest.approx(-90.0 + target, abs=1e-9) == pushed[0]
    assert pytest.approx(-120.0, abs=1e-9) == pushed[1]

    dist = float(geometry.central_angle(lat_c, lon_c, pushed[0], pushed[1]))
    assert pytest.approx(target, abs=1e-9) == dist


def test_push_along_great_circle_antimeridian():
    # Cruzando la línea de cambio de fecha (±180°)
    lat_c, lon_c = 0.0, 179.0
    lat_s, lon_s = 0.0, 179.8
    target = 2.0

    pushed = _push_along_great_circle(lat_s, lon_s, lat_c, lon_c, target)
    assert pushed is not None
    # Empuja 2° hacia el este desde 179°: 179° + 2° = 181° -> -179°
    assert pytest.approx(0.0, abs=1e-9) == pushed[0]
    assert pytest.approx(-179.0, abs=1e-9) == pushed[1]

    dist = float(geometry.central_angle(lat_c, lon_c, pushed[0], pushed[1]))
    assert pytest.approx(target, abs=1e-9) == dist


def test_push_along_great_circle_at_center():
    # Si el satélite está exactamente en el centro, la dirección es indefinida (devuelve None)
    lat_c, lon_c = 10.0, 45.0
    lat_s, lon_s = 10.0, 45.0
    pushed = _push_along_great_circle(lat_s, lon_s, lat_c, lon_c, 5.5)
    assert pushed is None


def test_repair_non_violating_sats_unchanged_bit_for_bit():
    sc = {
        "debris_zones": [{"id": "z1", "lat": 45.0, "lon": -35.0, "radius_deg": 10.0}],
        "occupied": [],
    }
    rng = np.random.default_rng(123)
    sats = np.array([[0.0, 0.0], [-10.0, -20.0], [60.0, 90.0]], dtype=float)
    sats_copy = sats.copy()

    repaired = repair(sats, sc, rng)

    # La entrada no debe ser mutada
    assert np.array_equal(sats, sats_copy)

    # Los satélites que no violaban quedan bit a bit iguales
    assert repaired.shape == sats.shape
    for i in range(len(sats)):
        assert repaired[i, 0] == sats[i, 0]
        assert repaired[i, 1] == sats[i, 1]


def test_repair_pushes_violating_sat_and_preserves_rng_when_valid():
    sc = {
        "debris_zones": [{"id": "z1", "lat": 45.0, "lon": -35.0, "radius_deg": 10.0}],
        "occupied": [],
    }
    rng = np.random.default_rng(42)
    # sat 0 es válido, sat 1 está dentro de z1 a distancia ~ 3.7°
    sats = np.array([[0.0, 0.0], [44.0, -30.0]], dtype=float)

    state_before = rng.bit_generator.state
    repaired = repair(sats, sc, rng, margin_deg=0.5)
    state_after = rng.bit_generator.state

    # sat 0 sin cambios bit a bit
    assert repaired[0, 0] == sats[0, 0]
    assert repaired[0, 1] == sats[0, 1]

    # sat 1 fue empujado a exactamente radio + margin = 10.5°
    d = float(geometry.central_angle(45.0, -35.0, repaired[1, 0], repaired[1, 1]))
    assert pytest.approx(10.5, abs=1e-9) == d

    # El RNG NO debe consumirse si el empuje deja al satélite en posición válida
    assert state_before == state_after


def test_repair_multiple_zones_picks_deepest():
    # Dos zonas solapadas:
    # Zona A: centro (0, 0), radio 10
    # Zona B: centro (0, 2), radio 10
    # Satélite en (0, 1):
    # dist a A = 1 -> depth_A = 10 - 1 = 9
    # dist a B = 1 -> pero hagamos radios distintos:
    # radio A = 8 -> dist = 1 -> depth_A = 7
    # radio B = 12 -> dist = 1 -> depth_B = 11
    # B tiene mayor depth_deg, debe empujar según la zona B!
    sc = {
        "debris_zones": [
            {"id": "za", "lat": 0.0, "lon": 0.0, "radius_deg": 8.0},
            {"id": "zb", "lat": 0.0, "lon": 2.0, "radius_deg": 12.0},
        ],
        "occupied": [],
    }
    rng = np.random.default_rng(42)
    sats = np.array([[0.0, 1.0]])

    repaired = repair(sats, sc, rng, margin_deg=0.5, max_tries=0)
    # Centro de B es (0, 2), satélite estaba en (0, 1).
    # La dirección desde B (0, 2) hacia sat (0, 1) es hacia el oeste (lon decreciente).
    # Radio B + margin = 12.5.
    # Distancia desde centro de B a la posición empujada debe ser 12.5°.
    dist_b = float(geometry.central_angle(0.0, 2.0, repaired[0, 0], repaired[0, 1]))
    assert pytest.approx(12.5, abs=1e-9) == dist_b


def test_repair_sat_at_center_resamples():
    # Satélite exactamente en el centro de la zona: la dirección es indefinida,
    # debe pasar al paso 2 y remuestrear con el RNG.
    sc = {
        "debris_zones": [{"id": "z1", "lat": 20.0, "lon": 30.0, "radius_deg": 5.0}],
        "occupied": [],
    }
    rng = np.random.default_rng(999)
    sats = np.array([[20.0, 30.0]])

    state_before = rng.bit_generator.state
    repaired = repair(sats, sc, rng, margin_deg=0.5, max_tries=20)
    state_after = rng.bit_generator.state

    # Se debió consumir el RNG para remuestrear
    assert state_before != state_after

    # La nueva posición ya no viola
    d = float(geometry.central_angle(20.0, 30.0, repaired[0, 0], repaired[0, 1]))
    assert d >= 5.0


def test_repair_pushed_into_another_zone_resamples():
    # Zona 1 en (0, 0), radio 5.
    # Zona 2 en (0, 6), radio 2.
    # Satélite en (0, 4). Empuje desde Zona 1 con margin 0.5 lleva a (0, 5.5).
    # Pero distancia de (0, 5.5) a Zona 2 (0, 6) es 0.5 < 2.0, ¡viola Zona 2!
    sc = {
        "debris_zones": [
            {"id": "z1", "lat": 0.0, "lon": 0.0, "radius_deg": 5.0},
            {"id": "z2", "lat": 0.0, "lon": 6.0, "radius_deg": 2.0},
        ],
        "occupied": [],
    }

    # Con max_tries = 0, conserva la posición empujada
    rng0 = np.random.default_rng(10)
    sats = np.array([[0.0, 4.0]])
    repaired_0 = repair(sats, sc, rng0, margin_deg=0.5, max_tries=0)
    d_z1 = float(geometry.central_angle(0.0, 0.0, repaired_0[0, 0], repaired_0[0, 1]))
    assert pytest.approx(5.5, abs=1e-9) == d_z1

    # Con max_tries = 20, remuestrea y encuentra una posición válida
    rng20 = np.random.default_rng(10)
    repaired_20 = repair(sats, sc, rng20, margin_deg=0.5, max_tries=20)
    d_z1_new = float(geometry.central_angle(0.0, 0.0, repaired_20[0, 0], repaired_20[0, 1]))
    d_z2_new = float(geometry.central_angle(0.0, 6.0, repaired_20[0, 0], repaired_20[0, 1]))
    assert d_z1_new >= 5.0
    assert d_z2_new >= 2.0


def test_repair_output_is_normalized():
    sc = {
        "debris_zones": [{"id": "z1", "lat": 89.0, "lon": 0.0, "radius_deg": 5.0}],
        "occupied": [],
    }
    rng = np.random.default_rng(1)
    sats = np.array([[88.0, 0.0]])
    repaired = repair(sats, sc, rng, margin_deg=0.5)

    assert -90.0 <= repaired[0, 0] <= 90.0
    assert -180.0 <= repaired[0, 1] < 180.0
