"""Stub del contrato (§6.3): firmas y constantes; lo implementa 1A."""
from pathlib import Path
import numpy as np

PRIORITY_WEIGHTS: dict[str, int] = {"Alta": 3, "Media": 2, "Normal": 1}
FITNESS_MODES = ("penalty", "strict")


def load_scenario(source: str | Path | dict) -> dict:
    """Carga y valida un escenario. Devuelve un dict nuevo (copia profunda si recibe un dict).

    Valida: claves obligatorias (§4.7); MAJOR de contract_version == MAJOR de CONTRACT_VERSION;
    ids únicos dentro de regions y dentro de debris_zones ∪ occupied; weight == PRIORITY_WEIGHTS[priority];
    rangos de lat/lon; radius_deg > 0; n_sats >= 1; footprint_deg > 0.
    Raises: FileNotFoundError, json.JSONDecodeError, ValueError (con un mensaje que nombra el campo).
    No requiere jsonschema (es solo una dependencia de desarrollo).
    """
    raise NotImplementedError


def coverage_matrix(sats: np.ndarray, sc: dict) -> np.ndarray:
    """Matriz c_iρ (§5.1) con forma (n_regions, n_sats), valores en [0, 1].

    El orden de las filas es el de sc["regions"] y el de las columnas, el de las filas de sats. Vectorizado.
    """
    raise NotImplementedError


def coverage(sats: np.ndarray, sc: dict) -> dict[str, float]:
    """{region_id: c_ρ} con c_ρ = max_i c_iρ (§5.2), como float de Python en [0, 1].

    Las claves están en el orden de sc["regions"]. Un valor de exactamente 1.0 significa "cubierta".
    """
    raise NotImplementedError


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
    raise NotImplementedError


def fitness(sats: np.ndarray, sc: dict, mode: str = "penalty") -> float:
    """Aptitud (§5.5) como float de Python. mode="penalty" → finita; mode="strict" → -inf si hay violaciones.

    Raises ValueError si mode no está en FITNESS_MODES. Objetivo de rendimiento: ≤ 100 µs con n=8 y 6 regiones.
    """
    raise NotImplementedError


def snapshot(sats: np.ndarray, sc: dict, mode: str = "penalty") -> dict:
    """Bloque `initial`/`final` del resultado:
    {"sats": list[list[float]], "coverage": dict, "fitness": float | None, "violations": list[dict]}.
    Si la aptitud es -inf, se escribe None. Todo es serializable a JSON tal cual.
    """
    raise NotImplementedError
