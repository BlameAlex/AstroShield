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


def latlon_to_xyz(lat: ArrayLike, lon: ArrayLike, r: float = 1.0) -> np.ndarray:
    """Convierte a cartesianas con forma (..., 3).

    x = r·cos(lat)·cos(lon), y = r·cos(lat)·sin(lon), z = r·sin(lat).
    Polo norte → (0, 0, r); (0, 0) → (r, 0, 0).
    """
    p = np.radians(np.asarray(lat, dtype=float))
    l = np.radians(np.asarray(lon, dtype=float))
    # z solo depende de lat: broadcast_arrays iguala las formas antes de apilar.
    x, y, z = np.broadcast_arrays(np.cos(p) * np.cos(l), np.cos(p) * np.sin(l), np.sin(p))
    return r * np.stack((x, y, z), axis=-1)


def sample_sphere(n: int, rng: np.random.Generator) -> np.ndarray:
    """n puntos uniformes sobre la esfera, con forma (n, 2) [lat, lon].

    lat = degrees(arcsin(rng.uniform(-1, 1, n))); después lon = rng.uniform(-180, 180, n).
    El orden de consumo del RNG es fijo: primero las n latitudes, luego las n longitudes.
    Pre: n >= 0. Post: lat en [-90, 90], lon en [-180, 180).
    """
    lat = np.degrees(np.arcsin(rng.uniform(-1.0, 1.0, n)))
    lon = rng.uniform(-180.0, 180.0, n)
    return np.column_stack((lat, lon))


def normalize_latlon(sats: np.ndarray) -> np.ndarray:
    """Devuelve una copia normalizada de un array (..., 2).

    Si lat > 90 o lat < -90, refleja sobre el polo (lat → ±180 − lat, lon → lon + 180)
    hasta que quede en rango; después aplica wrap_lon solo a las longitudes fuera de [-180, 180).
    Los valores que ya estaban en rango (lat y lon) se conservan bit a bit: si x ya está
    normalizado, normalize_latlon(x) es igual a x.
    No muta la entrada.
    """
    out = np.array(sats, dtype=float)
    lat, lon = out[..., 0], out[..., 1]
    m = np.abs(lat) > 90.0
    if m.any():
        # Forma cerrada de las reflexiones sucesivas: t es la posición sobre el meridiano
        # completo (periodo 360°); t > 180 equivale a un número impar de cruces de polo.
        t = np.mod(lat[m] + 90.0, 360.0)
        flip = t > 180.0
        lat[m] = np.where(flip, 270.0 - t, t - 90.0)
        lon[m] += np.where(flip, 180.0, 0.0)
    fuera = (lon < -180.0) | (lon >= 180.0)
    lon[fuera] = wrap_lon(lon[fuera])
    return out
