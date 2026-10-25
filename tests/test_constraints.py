"""Pruebas de restricciones y reparación de constelaciones (§6.5)."""
import numpy as np
import pytest

from astroshield import geometry
from astroshield.constraints import _push_along_great_circle


def test_push_along_great_circle_standard():
    # Zona en Atlántico Norte (45.0, -35.0), satélite en (44.0, -30.0)
    lat_c, lon_c = 45.0, -35.0
    lat_s, lon_s = 44.0, -30.0
    radius = 12.0
    margin = 0.5
    target = radius + margin

    pushed = _push_along_great_circle(lat_s, lon_s, lat_c, lon_c, target)
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
