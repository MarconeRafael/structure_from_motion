"""Referência matemática float64, independente do modelo RTL."""

import numpy as np


def matrix3(value):
    raw = np.asarray(value)
    if np.iscomplexobj(raw):
        raise ValueError("A matriz deve conter valores reais")
    matrix = np.asarray(value, dtype=np.float64)
    if matrix.shape != (3, 3) or not np.isfinite(matrix).all():
        raise ValueError("Esperada matriz 3x3 com valores finitos")
    return matrix


def essential_matrix(F, K):
    F, K = matrix3(F), matrix3(K)
    with np.errstate(over="raise", invalid="raise"):
        return K.T @ F @ K
