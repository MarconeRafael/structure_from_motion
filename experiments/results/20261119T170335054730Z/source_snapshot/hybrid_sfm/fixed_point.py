"""Modelo bit-exato de Mat3Mul: soma signed64 e fatia (47 downto 16)."""

from dataclasses import dataclass

import numpy as np

from .reference import matrix3

SCALE = 1 << 16
MIN_RAW = -(1 << 31)
MAX_RAW = (1 << 31) - 1
MIN_VALUE = MIN_RAW / SCALE
MAX_VALUE = MAX_RAW / SCALE


def quantize(value):
    matrix = matrix3(value)
    if np.any(matrix < MIN_VALUE) or np.any(matrix > MAX_VALUE):
        raise ValueError(f"Entrada fora de Q15.16: [{MIN_VALUE}, {MAX_VALUE}]")
    # O gerador original usa int(x * 65536), inclusive para negativos.
    return np.array([[int(x * SCALE) for x in row] for row in matrix], dtype=np.int64)


def signed_wrap(value, bits):
    return (value + (1 << (bits - 1))) % (1 << bits) - (1 << (bits - 1))


@dataclass
class FixedResult:
    raw: np.ndarray
    overflow_events: list

    @property
    def value(self):
        return self.raw.astype(np.float64) / SCALE

    @property
    def overflow(self):
        return bool(self.overflow_events)


def _multiply(A, B, stage, events):
    result = np.zeros((3, 3), dtype=np.int64)
    for i in range(3):
        for j in range(3):
            accumulator = 0
            for k in range(3):
                total = accumulator + int(A[i, k]) * int(B[k, j])
                if not -(1 << 63) <= total < (1 << 63):
                    events.append({"stage": stage, "kind": "accumulator64", "row": i,
                                   "column": j, "term": k})
                accumulator = signed_wrap(total, 64)
            shifted = accumulator >> 16
            if not MIN_RAW <= shifted <= MAX_RAW:
                events.append({"stage": stage, "kind": "result32", "row": i,
                               "column": j})
            result[i, j] = signed_wrap(shifted, 32)
    return result


def essential_matrix_raw(F_raw, K_raw):
    """Recebe inteiros já quantizados; não permite conversões silenciosas."""
    matrices = []
    for value in (F_raw, K_raw):
        matrix = np.asarray(value)
        if (matrix.shape != (3, 3) or matrix.dtype.kind not in "iu"
                or np.any(matrix < MIN_RAW) or np.any(matrix > MAX_RAW)):
            raise ValueError("Esperada matriz 3x3 de inteiros signed32")
        matrices.append(matrix)
    F, K = matrices
    events = []
    intermediate = _multiply(F, K, "F*K", events)
    raw = _multiply(K.T, intermediate, "K.T*(F*K)", events)
    return FixedResult(raw, events)


def essential_matrix_fixed(F, K):
    return essential_matrix_raw(quantize(F), quantize(K))
