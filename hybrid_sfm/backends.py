"""Contrato comum dos caminhos NumPy e GHDL, sem política de seleção."""

from dataclasses import dataclass
import math
import time

import numpy as np

from .ghdl_backend import BackendError, GhdlBackend
from .reference import essential_matrix, matrix3

BACKENDS = ("software", "rtl_simulated")


@dataclass(frozen=True)
class ExecutionConfig:
    ghdl: str | None = None
    timeout: float = 30.0
    max_cycles: int = 10

    def __post_init__(self):
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("timeout deve ser finito e positivo")
        if type(self.max_cycles) is not int or self.max_cycles <= 0:
            raise ValueError("max_cycles deve ser inteiro positivo")


def rtl_instance(config):
    return GhdlBackend(ghdl=config.ghdl, timeout=config.timeout, max_cycles=config.max_cycles)


def run_backend(backend, F, K, config=None, *, rtl_backend=None):
    """Retorna E válido ou diagnóstico; mede a tentativa inteira, incluindo validação."""
    if backend not in BACKENDS:
        raise ValueError(f"Backend desconhecido: {backend}")
    config = config or ExecutionConfig()
    started = time.perf_counter()
    result = {"backend": backend, "status": "error", "valid": False, "E": None,
              "metrics": {}, "diagnostic": None, "details": None}
    try:
        F, K = matrix3(F), matrix3(K)
        if backend == "software":
            compute_start = time.perf_counter()
            E = essential_matrix(F, K)
            result["metrics"]["numpy_seconds"] = time.perf_counter() - compute_start
            error = 0.0  # O contrato de referência é esta mesma operação float64.
        else:
            raw = (rtl_backend or rtl_instance(config)).run(F, K)
            result["details"] = raw
            if not isinstance(raw, dict):
                raise BackendError("invalid_result", "Resultado RTL deve ser um registro")
            if not raw.get("valid") or raw.get("status") != "ok" or not raw.get("bit_exact"):
                raise BackendError("invalid_result", raw.get("status", "Resultado RTL inválido"))
            E = matrix3(raw["E"])
            reference = essential_matrix(F, K)
            with np.errstate(over="raise", invalid="raise"):
                error = float(np.max(np.abs(E - reference)))
        result.update(status="ok", valid=True, E=E)
        result["metrics"]["max_abs_error"] = error
    except BackendError as exc:
        result["diagnostic"] = {"stage": exc.stage, "message": str(exc), "process": exc.process}
    except (ValueError, TypeError, KeyError, FloatingPointError, OSError) as exc:
        result["diagnostic"] = {"stage": "validation", "message": str(exc)}
    result["metrics"]["observed_seconds"] = time.perf_counter() - started
    return result
