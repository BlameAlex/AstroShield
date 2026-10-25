"""Restricciones espaciales y reparación de constelaciones (§6.5)."""
import numpy as np

from astroshield import geometry


def _push_along_great_circle(
    sat_lat: float,
    sat_lon: float,
    center_lat: float,
    center_lon: float,
    target_dist_deg: float,
) -> np.ndarray | None:
    """Mueve un satélite a lo largo del gran círculo centro->satélite hasta target_dist_deg.

    Implementado con vectores unitarios 3D cartesianos (geometry.latlon_to_xyz),
    sin usar rumbos ni fórmulas de trigonometría esférica propensas a singularidades
    en polos y en la línea de ±180°.
    Si el satélite está en el centro exacto (distancia ~ 0), la dirección queda
    indefinida y devuelve None.
    """
    C = geometry.latlon_to_xyz(center_lat, center_lon)
    S = geometry.latlon_to_xyz(sat_lat, sat_lon)

    # Componente tangencial de S respecto a C
    v = S - np.dot(C, S) * C
    norm_v = np.linalg.norm(v)
    if norm_v < 1e-12:
        return None

    u2 = v / norm_v
    theta_rad = np.radians(target_dist_deg)
    P = np.cos(theta_rad) * C + np.sin(theta_rad) * u2
    P = P / np.linalg.norm(P)

    lat = float(np.degrees(np.arcsin(np.clip(P[2], -1.0, 1.0))))
    lon = float(geometry.wrap_lon(np.degrees(np.arctan2(P[1], P[0]))))
    return np.array([lat, lon], dtype=float)


def _violations_impl(sats: np.ndarray, sc: dict) -> list[dict]:
    """Implementación fiel de violaciones (§5.4 y §6.3)."""
    viols = []
    n = len(sats)
    debris = sc.get("debris_zones", [])
    occupied = sc.get("occupied", [])

    for i in range(n):
        s_lat, s_lon = sats[i, 0], sats[i, 1]
        for z in debris:
            d = float(geometry.central_angle(s_lat, s_lon, z["lat"], z["lon"]))
            r = float(z["radius_deg"])
            if d < r:
                viols.append({
                    "sat": i,
                    "zone_id": z["id"],
                    "kind": "debris",
                    "distance_deg": d,
                    "radius_deg": r,
                    "depth_deg": r - d,
                })
        for z in occupied:
            d = float(geometry.central_angle(s_lat, s_lon, z["lat"], z["lon"]))
            r = float(z["radius_deg"])
            if d < r:
                viols.append({
                    "sat": i,
                    "zone_id": z["id"],
                    "kind": "occupied",
                    "distance_deg": d,
                    "radius_deg": r,
                    "depth_deg": r - d,
                })
    return viols


def _get_violations(sats: np.ndarray, sc: dict) -> list[dict]:
    """Obtiene violaciones delegando en model.violations o en el cálculo del contrato."""
    try:
        from astroshield import model
        return model.violations(sats, sc)
    except NotImplementedError:
        return _violations_impl(sats, sc)


def _find_zone(sc: dict, zone_id: str) -> dict:
    """Busca una zona por su identificador en debris_zones u occupied."""
    for z in sc.get("debris_zones", []) + sc.get("occupied", []):
        if z["id"] == zone_id:
            return z
    raise KeyError(f"Zona no encontrada: {zone_id}")


def repair(sats: np.ndarray, sc: dict, rng: np.random.Generator,
           margin_deg: float = 0.5, max_tries: int = 20) -> np.ndarray:
    """Devuelve un genoma NUEVO sin violaciones (si existe; la entrada no se muta).

    Para cada satélite, en orden de índice, que viole al menos una zona:
      1. Toma la zona de mayor depth_deg. Mueve el satélite a lo largo del gran círculo que une
         el centro de la zona con el satélite, hasta distancia radius + margin_deg del centro.
         Si el satélite está exactamente en el centro (dirección indefinida), pasa al paso 2.
      2. Si la nueva posición viola cualquier zona, remuestrea con geometry.sample_sphere(1, rng)
         hasta max_tries veces, hasta encontrar una posición válida. Si se agotan los intentos,
         conserva el último muestreo (la violación queda y run.py la reporta como valid=false).
    Post: misma forma; los satélites que no violaban quedan bit a bit iguales; salida normalizada;
      el rng solo se consume al remuestrear. Para el escenario base y los derivados factibles,
      violations(repair(s), sc) == [] con probabilidad práctica 1 (el área prohibida es el 2.7 %).
    Nota: en inviable.json la reparación SÍ deja configuraciones válidas (colocar satélites siempre
      es posible). Lo imposible es cubrir Yucatán: el problema es inviable en cobertura, no en colocación.
    Los helpers privados (_push_along_great_circle, etc.) viven en este archivo.
    """
    raise NotImplementedError
