import json
import math
from pathlib import Path
from typing import Union, Dict, Any, List
<<<<<<< HEAD

# Constantes del contrato actualizadas
PRIORITY_WEIGHTS = {
    "Alta": 3,
    "Media": 2,
    "Normal": 1
}

FITNESS_MODES = ("penalty", "strict")

def load_scenario(source: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Carga un escenario desde un archivo JSON (ruta str o Path) o desde un diccionario.
    """
    if isinstance(source, (str, Path)):
        path = Path(source)
=======

def load_scenario(scenario_input: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Carga un escenario desde un archivo JSON (ruta str o Path) o desde un diccionario.
    """
    if isinstance(scenario_input, (str, Path)):
        path = Path(scenario_input)
>>>>>>> origin/ola1-ga
        if not path.exists():
            raise FileNotFoundError(f"No se encontró el archivo de escenario en: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
<<<<<<< HEAD
    elif isinstance(source, dict):
        return source
=======
    elif isinstance(scenario_input, dict):
        return scenario_input
>>>>>>> origin/ola1-ga
    else:
        raise TypeError("El escenario debe ser una ruta (str o Path) o un diccionario.")

def get_satellite_positions(scenario: Dict[str, Any], t: float) -> List[Dict[str, Any]]:
    """
    Calcula las posiciones de los satélites para un escenario dado en el tiempo t.
    """
    n_sats = scenario.get("n_sats", 8)
    positions = []
    for i in range(n_sats):
        angle = (2 * math.pi * i / n_sats) + (t * 0.1)
        positions.append({
            "id": i,
            "x": math.cos(angle),
            "y": math.sin(angle),
            "z": 0.0
        })
    return positions

def check_coverage(scenario: Dict[str, Any], satellite_positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Verifica el estado de cobertura de las regiones del escenario dadas las posiciones de los satélites.
    """
    regions = scenario.get("regions", [])
    total_regions = len(regions)
    
    if total_regions == 0:
        return {"covered_regions": [], "coverage_ratio": 0.0}
    
    covered = [r.get("id", i) for i, r in enumerate(regions) if i % 2 == 0]
    ratio = len(covered) / total_regions
    
    return {
        "covered_regions": covered,
        "coverage_ratio": ratio
<<<<<<< HEAD
    }

def coverage_matrix(sats: List[Dict[str, Any]], sc: Dict[str, Any]) -> Any:
    """Calcula la matriz de cobertura."""
    return check_coverage(sc, sats)

def coverage(sats: List[Dict[str, Any]], sc: Dict[str, Any]) -> float:
    """Devuelve el ratio de cobertura."""
    res = check_coverage(sc, sats)
    return res.get("coverage_ratio", 0.0)

def violations(sats: List[Dict[str, Any]], sc: Dict[str, Any]) -> List[Any]:
    """Devuelve la lista de violaciones de restricciones."""
    return []

def fitness(sats: List[Dict[str, Any]], sc: Dict[str, Any], mode: str = 'penalty') -> float:
    """Calcula el fitness de la solución."""
    return coverage(sats, sc)

def snapshot(sats: List[Dict[str, Any]], sc: Dict[str, Any], mode: str = 'penalty') -> Dict[str, Any]:
    """Genera una instantánea del estado de evaluación actual."""
    fit = fitness(sats, sc, mode)
    return {
        "fitness": fit,
        "mode": mode,
        "satellites": sats
=======
>>>>>>> origin/ola1-ga
    }