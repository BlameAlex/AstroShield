"""Pruebas de restricciones y reparación de constelaciones (§6.5)."""
import json
from pathlib import Path

import numpy as np
import pytest

from astroshield import geometry
from astroshield.constraints import _get_violations, _push_along_great_circle, repair

ROOT = Path(__file__).resolve().parents[1]


def _load_or_derive_scenario(name: str) -> dict:
    """Carga el escenario desde scenarios/ o lo deriva del base según §4.6 del contrato."""
    sc_file = ROOT / "scenarios" / f"{name}.json"
    if sc_file.exists():
        return json.loads(sc_file.read_text(encoding="utf-8"))

    base = json.loads((ROOT / "scenarios" / "base.json").read_text(encoding="utf-8"))
    if name == "base":
        return base
    elif name == "reducido":
        base["id"] = "reducido"
        base["name"] = "Escenario de espacio reducido"
        for z in base["debris_zones"] + base["occupied"]:
            z["radius_deg"] = round(z["radius_deg"] * 1.5, 1)
        base["debris_zones"].append({
            "id": "bloqueo_australia_este",
            "name": "Bloqueo Australia Este",
            "lat": -25.0,
            "lon": 141.0,
            "radius_deg": 6.0,
        })
        return base
    elif name == "inviable":
        base["id"] = "inviable"
        base["name"] = "Escenario inviable en cobertura"
        base["debris_zones"].append({
            "id": "bloqueo_yucatan",
            "name": "Bloqueo Yucatán",
            "lat": 20.5,
            "lon": -89.0,
            "radius_deg": 13.0,
        })
        return base
    elif name == "prioridad_cambiada":
        base["id"] = "prioridad_cambiada"
        base["name"] = "Escenario con prioridades cambiadas"
        for r in base["regions"]:
            if r["id"] == "australia":
                r["priority"] = "Alta"
                r["weight"] = 3
            elif r["id"] == "california":
                r["priority"] = "Normal"
                r["weight"] = 1
        return base
    elif name == "menos_sats":
        base["id"] = "menos_sats"
        base["name"] = "Escenario con 4 satélites"
        base["n_sats"] = 4
        return base
    elif name == "footprint_chico":
        base["id"] = "footprint_chico"
        base["name"] = "Escenario con footprint chico"
        base["footprint_deg"] = 5.0
        return base
    else:
        raise ValueError(f"Escenario no reconocido: {name}")


def _coverage_yucatan(sats: np.ndarray, sc: dict) -> float:
    """Calcula la cobertura de Yucatán según las fórmulas del contrato (§5.1 y §5.2)."""
    try:
        from astroshield import model
        cov = model.coverage(sats, sc)
        return float(cov["yucatan"])
    except NotImplementedError:
        yuc = next(r for r in sc["regions"] if r["id"] == "yucatan")
        f_deg = sc["footprint_deg"]
        r_deg = yuc["radius_deg"]
        covs = []
        for s in sats:
            d = float(geometry.central_angle(s[0], s[1], yuc["lat"], yuc["lon"]))
            c_val = np.clip((f_deg + r_deg - d) / (2.0 * r_deg), 0.0, 1.0)
            covs.append(c_val)
        return float(max(covs)) if covs else 0.0


# --- Pruebas de empuje sobre gran círculo (_push_along_great_circle) ---

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


# --- Pruebas unitarias de repair ---

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
    # Dos zonas solapadas con distinta profundidad:
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
    # B tiene mayor depth_deg (12 - 1 = 11 > 8 - 1 = 7)
    # Distancia al centro de B debe ser exactamente radio + margin = 12.5°
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
    # Zona 1 en (0, 0), radio 5; Zona 2 en (0, 6), radio 2.
    # Satélite en (0, 4). Empuje lleva a (0, 5.5), que viola Zona 2 (dist 0.5 < 2).
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


# --- Pruebas obligatorias de escenarios (§6.5) ---

@pytest.mark.parametrize("scenario_name", [
    "base",
    "reducido",
    "prioridad_cambiada",
    "menos_sats",
    "footprint_chico",
    "inviable",
])
def test_zero_violations_all_feasible_scenarios(scenario_name):
    """Cero violaciones tras reparar en todos los escenarios factibles en colocación (§6.5)."""
    sc = _load_or_derive_scenario(scenario_name)

    for seed in (42, 123, 2024):
        rng = np.random.default_rng(seed)
        n = sc["n_sats"]
        sats = geometry.sample_sphere(n, rng)

        # Introducir violaciones forzadas colocando satélites en el centro y bordes de zonas
        if sc["debris_zones"]:
            sats[0] = [sc["debris_zones"][0]["lat"], sc["debris_zones"][0]["lon"]]
        if sc["occupied"]:
            sats[1] = [sc["occupied"][0]["lat"], sc["occupied"][0]["lon"]]

        repaired = repair(sats, sc, rng, margin_deg=0.5, max_tries=20)

        # Verificación de invariantes
        assert repaired.shape == (n, 2)
        assert np.all(repaired[:, 0] >= -90.0) and np.all(repaired[:, 0] <= 90.0)
        assert np.all(repaired[:, 1] >= -180.0) and np.all(repaired[:, 1] < 180.0)

        # Cero violaciones tras reparar
        viols = _get_violations(repaired, sc)
        assert len(viols) == 0, f"Violaciones residuales en {scenario_name}: {viols}"


def test_inviable_scenario_valid_placement_zero_yucatan_coverage():
    """Documentación y prueba del comportamiento en inviable.json.

    En inviable.json, colocar satélites siempre es posible (es factible en colocación),
    por lo que repair siempre produce configuraciones sin violaciones.
    Sin embargo, la zona de desechos bloqueo_yucatan (radio 13.0°) cubre todo el alcance
    de observación de Yucatán (footprint 10.0° + radio de Yucatán 2.7° = 12.7° < 13.0°).
    Por ello, ninguna configuración válida puede observar Yucatán (cobertura exactamente 0.0).
    El problema es inviable en cobertura, no en colocación (§4.6, §6.5).
    """
    sc = _load_or_derive_scenario("inviable")

    for seed in (42, 100, 999):
        rng = np.random.default_rng(seed)
        # Satélites intentando cubrir Yucatán forzadamente
        sats = geometry.sample_sphere(sc["n_sats"], rng)
        sats[0] = [20.5, -89.0]  # Exactamente en Yucatán
        sats[1] = [21.0, -88.5]  # Cerca de Yucatán

        repaired = repair(sats, sc, rng, margin_deg=0.5, max_tries=20)

        # 1. La reparación siempre deja configuraciones válidas
        viols = _get_violations(repaired, sc)
        assert len(viols) == 0, f"Configuración inválida en inviable.json: {viols}"

        # 2. Ninguna cubre Yucatán (cobertura exactamente 0.0)
        cov_yuc = _coverage_yucatan(repaired, sc)
        assert cov_yuc == 0.0, f"Se esperaba cobertura 0.0 en Yucatán, pero fue {cov_yuc}"


def test_no_space_scenario_terminates_and_consumes_exact_max_tries(monkeypatch):
    """Documentación y prueba del comportamiento en un escenario sin espacio disponible.

    En un escenario donde toda la superficie esférica está bloqueada por zonas prohibidas:
    1. La función repair termina sin entrar en bucle infinito.
    2. Devuelve violaciones residuales (ya que es imposible colocar satélites válidos).
    3. Consume exactamente max_tries llamadas a geometry.sample_sphere por cada satélite.
    4. Con max_tries = 0, conserva la posición empujada y consume 0 remuestreos.
    """
    # Dos zonas de radio 120° en polos opuestos del ecuador (0,0) y (0,-180).
    # La suma de distancias a cualquier punto es >= 180°, por lo que al menos
    # una de las dos distancias es <= 90° < 120°. Todo punto sobre la esfera viola.
    sc_sin_espacio = {
        "debris_zones": [
            {"id": "bloqueo_hemisferio_1", "lat": 0.0, "lon": 0.0, "radius_deg": 120.0},
            {"id": "bloqueo_hemisferio_2", "lat": 0.0, "lon": -180.0, "radius_deg": 120.0},
        ],
        "occupied": [],
    }

    n_sats = 3
    sats = np.array([[10.0, 20.0], [-30.0, 40.0], [50.0, -100.0]])
    max_tries = 7

    calls = 0
    orig_sample = geometry.sample_sphere

    def spy_sample_sphere(n, r):
        nonlocal calls
        calls += 1
        return orig_sample(n, r)

    monkeypatch.setattr(geometry, "sample_sphere", spy_sample_sphere)

    rng = np.random.default_rng(77)
    repaired = repair(sats, sc_sin_espacio, rng, margin_deg=0.5, max_tries=max_tries)

    # 1. Termina y tiene la forma correcta
    assert repaired.shape == (n_sats, 2)

    # 2. Consume exactamente max_tries remuestreos por satélite
    assert calls == n_sats * max_tries

    # 3. Devuelve violaciones residuales
    viols = _get_violations(repaired, sc_sin_espacio)
    assert len(viols) > 0

    # 4. Con max_tries = 0: consume 0 remuestreos y conserva las posiciones empujadas
    calls = 0
    repaired_0 = repair(sats, sc_sin_espacio, rng, margin_deg=0.5, max_tries=0)
    assert calls == 0
    assert repaired_0.shape == (n_sats, 2)
    assert len(_get_violations(repaired_0, sc_sin_espacio)) > 0
