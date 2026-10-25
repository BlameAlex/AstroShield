"""Geometría esférica de AstroShield (contrato §6.2).

Toda la API pública recibe y devuelve grados; los radianes solo existen dentro de las funciones.
"""
import numpy as np
from numpy.typing import ArrayLike

EARTH_RADIUS_KM = 6371.0


def wrap_lon(lon: ArrayLike) -> np.ndarray:
    """Envuelve longitudes a [-180, 180).

    Fórmula: w = ((lon + 180) % 360) - 180; si w >= 180 (np.mod redondea a 360 cuando lon
    queda apenas por debajo de -180), w -= 360.
    Bordes: wrap_lon(180) == -180; wrap_lon(-180) == -180; wrap_lon(540) == -180;
    wrap_lon(-190) == 170; wrap_lon(np.nextafter(-180, -inf)) == -180. Acepta escalares o
    arrays y devuelve np.ndarray (0-d para un escalar). Vectorizable.
    """
    w = np.mod(np.asarray(lon, dtype=float) + 180.0, 360.0) - 180.0
    return np.where(w >= 180.0, w - 360.0, w)


def central_angle(lat1: ArrayLike, lon1: ArrayLike, lat2: ArrayLike, lon2: ArrayLike) -> np.ndarray:
    """Ángulo central en grados entre puntos de una esfera (haversine).

    h = sin²(Δlat/2) + cos(lat1)·cos(lat2)·sin²(Δlon/2); resultado = 2·asin(sqrt(clip(h, 0, 1))).
    Pre: lat en [-90, 90]. Acepta cualquier lon (el seno absorbe la vuelta).
    Post: valores en [0, 180]; aplica broadcasting de numpy en los 4 argumentos.
    Bordes (float64): central_angle(0, 179.9, 0, -179.9) ≈ 0.2; central_angle(90, 0, 90, 123) ≈ 0
    (error < 1e-12); central_angle(90, x, 0, y) ≈ 90 (error < 1e-9) para cualquier x, y;
    antípodas ≈ 180 (exacto en el ecuador; cerca de 180° haversine pierde precisión, error ~2e-6°).
    """
    p1, l1, p2, l2 = (np.radians(np.asarray(v, dtype=float)) for v in (lat1, lon1, lat2, lon2))
    h = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin((l2 - l1) / 2) ** 2
    # asarray: con entradas escalares los ufuncs devuelven np.float64 y el contrato pide ndarray.
    return np.asarray(np.degrees(2.0 * np.arcsin(np.sqrt(np.clip(h, 0.0, 1.0)))))
