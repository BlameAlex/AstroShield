"""Tests de geometry.py (contrato §6.2, PATCH 1.0.1)."""
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pytest

from astroshield.geometry import EARTH_RADIUS_KM, central_angle, latlon_to_xyz, normalize_latlon, sample_sphere, wrap_lon


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


# --- latlon_to_xyz --------------------------------------------------------

@pytest.mark.parametrize("lat, lon, xyz", [
    (90, 0, (0, 0, 1)), (-90, 33, (0, 0, -1)), (0, 0, (1, 0, 0)), (0, 90, (0, 1, 0)),
])
def test_latlon_to_xyz_puntos_clave(lat, lon, xyz):
    assert np.allclose(latlon_to_xyz(lat, lon), xyz, rtol=0, atol=1e-12)
    assert np.allclose(latlon_to_xyz(lat, lon, r=2.0), 2 * np.array(xyz), rtol=0, atol=1e-12)


def test_latlon_to_xyz_forma_y_norma():
    rng = np.random.default_rng(3)
    lat, lon = rng.uniform(-90, 90, 5), rng.uniform(-180, 180, 5)
    assert latlon_to_xyz(lat, lon).shape == (5, 3)
    rejilla = latlon_to_xyz(lat[:, None], lon[None, :4], r=3.0)
    assert rejilla.shape == (5, 4, 3)
    assert np.allclose(np.linalg.norm(rejilla, axis=-1), 3.0)


def test_xyz_coincide_con_central_angle():
    rng = np.random.default_rng(4)
    a, b = sample_sphere(500, rng), sample_sphere(500, rng)
    coseno = np.sum(latlon_to_xyz(a[:, 0], a[:, 1]) * latlon_to_xyz(b[:, 0], b[:, 1]), axis=-1)
    angulo = np.degrees(np.arccos(np.clip(coseno, -1, 1)))
    assert np.allclose(angulo, central_angle(a[:, 0], a[:, 1], b[:, 0], b[:, 1]), rtol=0, atol=1e-6)


# --- sample_sphere --------------------------------------------------------

def test_sample_sphere_forma_y_rangos():
    s = sample_sphere(10_000, np.random.default_rng(0))
    assert s.shape == (10_000, 2)
    assert np.all((s[:, 0] >= -90) & (s[:, 0] <= 90))
    assert np.all((s[:, 1] >= -180) & (s[:, 1] < 180))


def test_sample_sphere_reproducible():
    a = sample_sphere(50, np.random.default_rng(42))
    b = sample_sphere(50, np.random.default_rng(42))
    c = sample_sphere(50, np.random.default_rng(43))
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_sample_sphere_orden_consumo():
    rng = np.random.default_rng(7)
    u, lon = rng.uniform(-1, 1, 5), rng.uniform(-180, 180, 5)
    esperado = np.column_stack((np.degrees(np.arcsin(u)), lon))
    assert np.array_equal(sample_sphere(5, np.random.default_rng(7)), esperado)


def test_sample_sphere_uniforme():
    lat = sample_sphere(10_000, np.random.default_rng(0))[:, 0]
    assert np.mean(np.sin(np.radians(lat))) == pytest.approx(0, abs=0.03)
    # Uniforme en área: P(|lat| < 30) = sin(30°) = 0.5; con lat uniforme sería 1/3.
    assert np.mean(np.abs(lat) < 30) == pytest.approx(0.5, abs=0.02)


def test_sample_sphere_vacio():
    assert sample_sphere(0, np.random.default_rng(0)).shape == (0, 2)


# --- normalize_latlon -----------------------------------------------------

@pytest.mark.parametrize("entrada, esperado", [
    ([95, 10], [85, -170]), ([-95, -170], [-85, 10]), ([185, 0], [-5, -180]),
    ([0, 190], [0, -170]), ([0, 180], [0, -180]),
])
def test_normalize_reflexiones(entrada, esperado):
    r = normalize_latlon(np.array(entrada, dtype=float))
    assert r.shape == (2,)
    assert np.allclose(r, esperado, rtol=0, atol=1e-12)


def test_normalize_varias_vueltas():
    r = normalize_latlon(np.array([[270.0, 0.0], [450.0, 0.0], [1000.0, 5.0]]))
    assert r[0, 0] == pytest.approx(-90)
    assert r[1, 0] == pytest.approx(90)
    assert np.allclose(latlon_to_xyz(r[2, 0], r[2, 1]), latlon_to_xyz(1000.0, 5.0), atol=1e-12)


def test_normalize_identidad_bit_a_bit():
    # P2: lo que ya está normalizado no cambia ni en el último bit.
    x = np.vstack((sample_sphere(100, np.random.default_rng(5)),
                   [[-90.0, -180.0], [90.0, 0.0], [0.0, -180.0], [45.0, np.nextafter(180.0, 0.0)]]))
    assert np.array_equal(normalize_latlon(x), x)


def test_normalize_no_muta():
    x = np.random.default_rng(6).uniform(-400, 400, (5, 8, 2))
    copia = x.copy()
    r = normalize_latlon(x)
    assert np.array_equal(x, copia)
    assert r is not x and r.shape == x.shape


def test_normalize_mismo_punto_fisico():
    rng = np.random.default_rng(8)
    crudo = np.column_stack((rng.uniform(-500, 500, 1000), rng.uniform(-1000, 1000, 1000)))
    r = normalize_latlon(crudo)
    assert np.all((r[:, 0] >= -90) & (r[:, 0] <= 90))
    assert np.all((r[:, 1] >= -180) & (r[:, 1] < 180))
    assert np.allclose(latlon_to_xyz(r[:, 0], r[:, 1]), latlon_to_xyz(crudo[:, 0], crudo[:, 1]), atol=1e-9)


# --- Oráculos numéricos del escenario base (contrato §4.1 y §4.5) ---------

BASE = json.loads((Path(__file__).resolve().parents[1] / "scenarios" / "base.json").read_text(encoding="utf-8"))
REGIONES = {r["id"]: (r["lat"], r["lon"]) for r in BASE["regions"]}
ZONAS = {z["id"]: (z["lat"], z["lon"], z["radius_deg"]) for z in BASE["debris_zones"] + BASE["occupied"]}
F, R = BASE["footprint_deg"], BASE["regions"][0]["radius_deg"]

DISTANCIAS_REGIONES = {
    ("yucatan", "amazonia"): 35.74, ("yucatan", "california"): 31.05, ("yucatan", "sahel"): 83.89,
    ("yucatan", "japon"): 108.12, ("yucatan", "australia"): 141.16, ("amazonia", "california"): 66.79,
    ("amazonia", "sahel"): 64.10, ("amazonia", "japon"): 142.63, ("amazonia", "australia"): 147.99,
    ("california", "sahel"): 102.98, ("california", "japon"): 77.83, ("california", "australia"): 118.20,
    ("sahel", "japon"): 115.38, ("sahel", "australia"): 134.94, ("japon", "australia"): 61.18,
}

# Zona más cercana por distancia al centro (P5): (zona, distancia al centro, distancia al borde).
ZONA_MAS_CERCANA = {
    "yucatan": ("atlantico_norte", 50.44, 38.44), "amazonia": ("atlantico_norte", 54.15, 42.15),
    "california": ("atlantico_norte", 61.39, 49.39), "sahel": ("atlantico_norte", 42.05, 30.05),
    "japon": ("objeto_b", 57.46, 52.46), "australia": ("objeto_b", 23.76, 18.76),
}


def _distancia(region, zona):
    return float(central_angle(*REGIONES[region], *ZONAS[zona][:2]))


def test_radio_300_km():
    radio = np.degrees(300 / EARTH_RADIUS_KM)
    assert radio == pytest.approx(2.698, abs=1e-3)
    assert all(r["radius_deg"] == round(radio, 1) for r in BASE["regions"])


@pytest.mark.parametrize("par, esperado", DISTANCIAS_REGIONES.items(), ids=lambda v: "-".join(v) if isinstance(v, tuple) else "")
def test_distancias_entre_regiones(par, esperado):
    a, b = par
    assert float(central_angle(*REGIONES[a], *REGIONES[b])) == pytest.approx(esperado, abs=0.01)


@pytest.mark.parametrize("region", ZONA_MAS_CERCANA)
def test_zona_mas_cercana_por_centro(region):
    zona, centro, borde = ZONA_MAS_CERCANA[region]
    assert min(ZONAS, key=lambda z: _distancia(region, z)) == zona
    assert _distancia(region, zona) == pytest.approx(centro, abs=0.01)
    assert _distancia(region, zona) - ZONAS[zona][2] == pytest.approx(borde, abs=0.01)


def test_zona_mas_cercana_por_borde_japon():
    # Nota P5: por borde, a Japón le queda más cerca polar_norte que objeto_b.
    por_borde = min(ZONAS, key=lambda z: _distancia("japon", z) - ZONAS[z][2])
    assert por_borde == "polar_norte"
    assert _distancia("japon", "polar_norte") == pytest.approx(58.47, abs=0.01)
    assert _distancia("japon", "polar_norte") - ZONAS["polar_norte"][2] == pytest.approx(50.47, abs=0.01)


def test_restricciones_inactivas_en_optimo_base():
    minimo = min(_distancia(r, z) - ZONAS[z][2] for r in REGIONES for z in ZONAS)
    assert minimo == pytest.approx(18.76, abs=0.01)
    assert minimo > F - R


def test_regimen_no_trivial():
    separacion = min(float(central_angle(*REGIONES[a], *REGIONES[b])) for a, b in combinations(REGIONES, 2))
    assert separacion == pytest.approx(31.05, abs=0.01)
    assert separacion > 2 * (F + R)           # ningún satélite toca dos regiones
    assert separacion / 2 + R > F             # el régimen trivial empieza en 18.2°


def test_area_prohibida():
    casquete = lambda theta: (1 - np.cos(np.radians(theta))) / 2
    assert casquete(F - R) == pytest.approx(0.0041, abs=1e-4)
    assert casquete(F + R) == pytest.approx(0.0122, abs=1e-4)
    analitica = sum(casquete(r) for *_, r in ZONAS.values())
    assert analitica == pytest.approx(0.0272, abs=5e-4)
    puntos = sample_sphere(200_000, np.random.default_rng(0))
    dentro = np.zeros(len(puntos), dtype=bool)
    for lat, lon, radio in ZONAS.values():
        dentro |= central_angle(puntos[:, 0], puntos[:, 1], lat, lon) < radio
    assert dentro.mean() == pytest.approx(analitica, abs=2e-3)
