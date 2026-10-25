"""Stub del contrato (§6.5): firmas y constantes; lo implementa 2B."""
import numpy as np


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
    Los helpers privados (_destination, _bearing) viven en este archivo.
    """
    raise NotImplementedError
