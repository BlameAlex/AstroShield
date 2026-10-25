"""Modelo del problema (§6.3): carga de escenarios, cobertura, violaciones y aptitud."""
import copy
import json
from pathlib import Path

import numpy as np

from astroshield import CONTRACT_VERSION, geometry

PRIORITY_WEIGHTS: dict[str, int] = {"Alta": 3, "Media": 2, "Normal": 1}
FITNESS_MODES = ("penalty", "strict")

_REQUIRED_KEYS = ("contract_version", "id", "name", "n_sats", "footprint_deg",
                  "regions", "debris_zones", "occupied", "fitness")


def load_scenario(source: str | Path | dict) -> dict:
    """Carga y valida un escenario. Devuelve un dict nuevo (copia profunda si recibe un dict).

    Valida: claves obligatorias (§4.7); MAJOR de contract_version == MAJOR de CONTRACT_VERSION;
    ids únicos dentro de regions y dentro de debris_zones ∪ occupied; weight == PRIORITY_WEIGHTS[priority];
    rangos de lat/lon; radius_deg > 0; n_sats >= 1; footprint_deg > 0.
    Raises: FileNotFoundError, json.JSONDecodeError, ValueError (con un mensaje que nombra el campo).
    No requiere jsonschema (es solo una dependencia de desarrollo).
    """
    if isinstance(source, dict):
        sc = copy.deepcopy(source)
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Archivo de escenario no encontrado: {source}")
        sc = json.loads(path.read_text(encoding="utf-8"))

    for key in _REQUIRED_KEYS:
        if key not in sc:
            raise ValueError(f"Falta la clave requerida en escenario: {key}")

    if str(sc["contract_version"]).split(".")[0] != CONTRACT_VERSION.split(".")[0]:
        raise ValueError(f"contract_version: MAJOR no coincide: {sc['contract_version']} != {CONTRACT_VERSION}")

    if not isinstance(sc["n_sats"], int) or sc["n_sats"] < 1:
        raise ValueError(f"n_sats debe ser un entero >= 1: {sc['n_sats']}")
    if sc["footprint_deg"] <= 0:
        raise ValueError(f"footprint_deg debe ser > 0: {sc['footprint_deg']}")

    fit_block = sc["fitness"]
    if "k_penalty" not in fit_block or fit_block["k_penalty"] < 0:
        raise ValueError(f"fitness.k_penalty inválido: {fit_block.get('k_penalty')}")
    if "redundancy_bonus" not in fit_block or fit_block["redundancy_bonus"] < 0:
        raise ValueError(f"fitness.redundancy_bonus inválido: {fit_block.get('redundancy_bonus')}")

    if not sc["regions"] or not isinstance(sc["regions"], list):
        raise ValueError("regions debe ser una lista no vacía")

    region_ids = []
    for r in sc["regions"]:
        r_id = r.get("id")
        if not r_id:
            raise ValueError("regions: región sin id")
        region_ids.append(r_id)
        if r.get("priority") not in PRIORITY_WEIGHTS:
            raise ValueError(f"priority desconocida en región {r_id}: {r.get('priority')}")
        if r.get("weight") != PRIORITY_WEIGHTS[r["priority"]]:
            raise ValueError(f"weight no coincide con priority en región {r_id}")
        if not (-90.0 <= r.get("lat", 0.0) <= 90.0):
            raise ValueError(f"lat fuera de rango en región {r_id}")
        if not (-180.0 <= r.get("lon", 0.0) < 180.0):
            raise ValueError(f"lon fuera de rango en región {r_id}")
        if r.get("radius_deg", 0.0) <= 0:
            raise ValueError(f"radius_deg debe ser > 0 en región {r_id}")

    if len(region_ids) != len(set(region_ids)):
        raise ValueError("regions: ids duplicados")

    zone_ids = []
    for group_name in ("debris_zones", "occupied"):
        for z in sc[group_name]:
            z_id = z.get("id")
            if not z_id:
                raise ValueError(f"{group_name}: zona sin id")
            zone_ids.append(z_id)
            if not (-90.0 <= z.get("lat", 0.0) <= 90.0):
                raise ValueError(f"lat fuera de rango en zona {z_id}")
            if not (-180.0 <= z.get("lon", 0.0) < 180.0):
                raise ValueError(f"lon fuera de rango en zona {z_id}")
            if z.get("radius_deg", 0.0) <= 0:
                raise ValueError(f"radius_deg debe ser > 0 en zona {z_id}")

    if len(zone_ids) != len(set(zone_ids)):
        raise ValueError("debris_zones/occupied: ids duplicados")

    return sc


def coverage_matrix(sats: np.ndarray, sc: dict) -> np.ndarray:
    """Matriz c_iρ (§5.1) con forma (n_regions, n_sats), valores en [0, 1].

    El orden de las filas es el de sc["regions"] y el de las columnas, el de las filas de sats. Vectorizado.
    """
    sats_arr = np.asarray(sats, dtype=float)
    regions = sc["regions"]
    reg_lats = np.array([r["lat"] for r in regions], dtype=float)[:, None]
    reg_lons = np.array([r["lon"] for r in regions], dtype=float)[:, None]
    reg_rads = np.array([r["radius_deg"] for r in regions], dtype=float)[:, None]

    dists = geometry.central_angle(sats_arr[None, :, 0], sats_arr[None, :, 1], reg_lats, reg_lons)
    foot = float(sc["footprint_deg"])
    # Umbral explícito (§5.1): en d = F − r la fórmula da 0.9999999999999997 por redondeo.
    partial = np.clip((foot + reg_rads - dists) / (2.0 * reg_rads), 0.0, 1.0)
    return np.where(dists <= foot - reg_rads, 1.0, partial)


def coverage(sats: np.ndarray, sc: dict) -> dict[str, float]:
    """{region_id: c_ρ} con c_ρ = max_i c_iρ (§5.2), como float de Python en [0, 1].

    Las claves están en el orden de sc["regions"]. Un valor de exactamente 1.0 significa "cubierta".
    """
    c_reg = np.max(coverage_matrix(sats, sc), axis=1)
    return {r["id"]: float(c_reg[i]) for i, r in enumerate(sc["regions"])}


def violations(sats: np.ndarray, sc: dict) -> list[dict]:
    """Lista de violaciones (§5.4), ordenada por sat ascendente; para cada sat, primero
    debris_zones y luego occupied, cada grupo en el orden del escenario.

    Cada elemento tiene EXACTAMENTE estas claves:
      {"sat": int,              # índice de fila en sats
       "zone_id": str,
       "kind": "debris" | "occupied",
       "distance_deg": float,   # ángulo central sat-centro
       "radius_deg": float,
       "depth_deg": float}      # radius_deg - distance_deg > 0
    Devuelve una lista vacía si la configuración es válida. No verifica n_sats.
    """
    sats_arr = np.asarray(sats, dtype=float)
    viols = []
    for i in range(len(sats_arr)):
        s_lat, s_lon = sats_arr[i, 0], sats_arr[i, 1]
        for kind, group in (("debris", sc["debris_zones"]), ("occupied", sc["occupied"])):
            for z in group:
                d = float(geometry.central_angle(s_lat, s_lon, z["lat"], z["lon"]))
                r = float(z["radius_deg"])
                if d < r:
                    viols.append({"sat": i, "zone_id": z["id"], "kind": kind,
                                  "distance_deg": d, "radius_deg": r, "depth_deg": r - d})
    return viols


def fitness(sats: np.ndarray, sc: dict, mode: str = "penalty") -> float:
    """Aptitud (§5.5) como float de Python. mode="penalty" → finita; mode="strict" → -inf si hay violaciones.

    Raises ValueError si mode no está en FITNESS_MODES. Objetivo de rendimiento: ≤ 100 µs con n=8 y 6 regiones.
    """
    if mode not in FITNESS_MODES:
        raise ValueError(f"Modo de aptitud no reconocido: {mode}")

    cov_mat = coverage_matrix(sats, sc)
    c_reg = np.max(cov_mat, axis=1)
    weights = np.array([r["weight"] for r in sc["regions"]], dtype=float)
    w_sum = np.sum(weights)
    cov = float(np.sum(weights * c_reg) / w_sum)
    red = float(np.sum(weights * (np.sum(cov_mat == 1.0, axis=1) >= 2)) / w_sum)
    base = cov + float(sc["fitness"]["redundancy_bonus"]) * red

    n_viol = len(violations(sats, sc))
    if mode == "penalty":
        return float(base - float(sc["fitness"]["k_penalty"]) * n_viol)
    return float(base) if n_viol == 0 else -float("inf")


def snapshot(sats: np.ndarray, sc: dict, mode: str = "penalty") -> dict:
    """Bloque `initial`/`final` del resultado:
    {"sats": list[list[float]], "coverage": dict, "fitness": float | None, "violations": list[dict]}.
    Si la aptitud es -inf, se escribe None. Todo es serializable a JSON tal cual.
    """
    sats_arr = np.asarray(sats, dtype=float)
    fit = fitness(sats_arr, sc, mode=mode)
    return {
        "sats": [[float(c) for c in row] for row in sats_arr],
        "coverage": coverage(sats_arr, sc),
        "fitness": float(fit) if np.isfinite(fit) else None,
        "violations": violations(sats_arr, sc),
    }
