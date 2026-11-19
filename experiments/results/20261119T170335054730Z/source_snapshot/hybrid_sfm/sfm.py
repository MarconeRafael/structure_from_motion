"""Integração mínima: F fornecida ou estimada em Python, somente E é delegada."""

import numpy as np

from .manager import ExecutionManager
from .reference import matrix3


def estimate_essential(K, *, F=None, points1=None, points2=None, manager=None,
                       mode="auto", requirements=None, input_class="controlled"):
    if F is not None:
        if points1 is not None or points2 is not None:
            raise ValueError("Forneça F ou correspondências, sem combinar as duas entradas")
        F = matrix3(F)
        estimation = {"method": "provided_F"}
    else:
        first, second = np.asarray(points1, dtype=np.float64), np.asarray(points2, dtype=np.float64)
        if (first.ndim != 2 or first.shape[1] != 2 or first.shape != second.shape
                or len(first) < 8 or not np.isfinite(first).all() or not np.isfinite(second).all()):
            raise ValueError("Esperadas pelo menos oito correspondências finitas Nx2")
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("Instale as dependências OpenCV opcionais para estimar F") from exc
        F, mask = cv2.findFundamentalMat(first, second, cv2.FM_8POINT)
        if F is None:
            raise ValueError("OpenCV não conseguiu estimar F")
        F = matrix3(F)
        if np.linalg.norm(F) == 0 or np.linalg.matrix_rank(F) != 2:
            raise ValueError("Estimativa F degenerada")
        estimation = {"method": "opencv.FM_8POINT", "opencv_version": cv2.__version__,
                      "correspondences": len(first), "mask": mask}
    result = (manager or ExecutionManager()).execute(K=K, F=F, mode=mode,
                                                    requirements=requirements, input_class=input_class)
    result["estimation"] = {**estimation, "F": F}
    return result


def require_valid_essential(result):
    """Barreira explícita antes de continuar para pose/triangulação em Python."""
    if not result.get("valid") or result.get("status") not in ("ok", "fallback_ok"):
        raise ValueError("Etapa E inválida; continuação geométrica interrompida")
    E = matrix3(result["E"])
    if not np.any(E != 0):
        raise ValueError("Matriz E nula; continuação geométrica interrompida")
    return E.copy()
