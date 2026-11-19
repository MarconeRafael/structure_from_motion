"""Caracterização empírica e validação de perfis, sem executar o caso na seleção."""

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from .backends import BACKENDS, ExecutionConfig, run_backend
from .ghdl_backend import BackendError
from .metrics import ERROR_METRIC, TIME_SCOPE, implementation_signature, json_value
from .reference import matrix3


def _nonnegative(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def validate_profiles(document):
    """Recusa perfis malformados; a procedência dos dados deve ser auditada pelo usuário."""
    if (not isinstance(document, dict) or document.get("schema_version") != 1
            or not isinstance(document.get("profiles"), list)):
        raise ValueError("Documento de perfis inválido")
    ids = set()
    for profile in document["profiles"]:
        try:
            if (profile["backend"] not in BACKENDS or not isinstance(profile["id"], str)
                    or not profile["id"] or profile["id"] in ids
                    or not isinstance(profile["signature"], dict)
                    or profile["error_metric"] != ERROR_METRIC or profile["time_scope"] != TIME_SCOPE
                    or not isinstance(profile["input_class"], str) or not profile["input_class"]
                    or not isinstance(profile["conditions"], dict)
                    or not isinstance(profile["experiment_id"], str)):
                raise ValueError("Identidade/métrica do perfil inválida")
            ids.add(profile["id"])
            for name in ("F", "K"):
                low, high = (matrix3(profile["domain"][name][bound]) for bound in ("min", "max"))
                if np.any(low > high):
                    raise ValueError("Domínio de perfil inválido")
            samples = profile["samples"]
            if not isinstance(samples, list) or not samples:
                raise ValueError("Perfil sem observações")
            for sample in samples:
                if (type(sample["valid"]) is not bool or not _nonnegative(sample["observed_seconds"])
                        or (sample["valid"] and not _nonnegative(sample["max_abs_error"]))):
                    raise ValueError("Observação inválida")
            valid = [s for s in samples if s["valid"]]
            summary = profile["summary"]
            expected_error = max((s["max_abs_error"] for s in valid), default=None)
            if (summary["max_abs_error"] != expected_error
                    or summary["max_seconds"] != max(s["observed_seconds"] for s in samples)
                    or summary["failure_rate"] != (len(samples) - len(valid)) / len(samples)):
                raise ValueError("Resumo não corresponde às observações")
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError("Perfil incompleto ou inválido") from exc
    return document


def load_profiles(path):
    return validate_profiles(json.loads(Path(path).read_text(encoding="utf-8")))


def covers(profile, F, K, input_class):
    if profile["input_class"] != input_class:
        return False
    return all(np.all(matrix >= np.asarray(profile["domain"][name]["min"]))
               and np.all(matrix <= np.asarray(profile["domain"][name]["max"]))
               for name, matrix in (("F", F), ("K", K)))


def characterize(cases, *, config=None, repeats=3, warmup=1, input_class="controlled",
                 experiment_id=None, rtl_backend=None, backends=BACKENDS):
    """Mede entradas fornecidas; guarda amostras, falhas e envelope por componente."""
    if type(repeats) is not int or repeats <= 0 or type(warmup) is not int or warmup < 0:
        raise ValueError("repeats deve ser positivo e warmup não negativo")
    if not isinstance(input_class, str) or not input_class:
        raise ValueError("input_class deve ser uma identificação não vazia")
    if not backends or len(set(backends)) != len(backends) or any(b not in BACKENDS for b in backends):
        raise ValueError("Lista de backends inválida")
    config = config or ExecutionConfig()
    cases = [(matrix3(F).copy(), matrix3(K).copy()) for F, K in cases]
    if not cases:
        raise ValueError("Caracterização requer entradas")
    domain = {name: {"min": np.min(values, axis=0).tolist(), "max": np.max(values, axis=0).tolist()}
              for name, values in (("F", [F for F, K in cases]), ("K", [K for F, K in cases]))}
    created = datetime.now(timezone.utc).isoformat()
    experiment_id = experiment_id or created
    profiles, unavailable = [], []
    for backend in backends:
        try:
            signature = implementation_signature(backend, config, rtl_backend)
        except (BackendError, OSError) as exc:
            unavailable.append({"backend": backend, "message": str(exc),
                                "stage": getattr(exc, "stage", "tool")})
            continue
        warmups = []
        for _ in range(warmup):
            for F, K in cases:
                result = run_backend(backend, F, K, config, rtl_backend=rtl_backend)
                warmups.append({"valid": result["valid"], "diagnostic": result["diagnostic"]})
        samples = []
        for repetition in range(repeats):
            for index, (F, K) in enumerate(cases):
                result = run_backend(backend, F, K, config, rtl_backend=rtl_backend)
                samples.append({"case_index": index, "repetition": repetition,
                                "valid": result["valid"], "status": result["status"],
                                "observed_seconds": result["metrics"]["observed_seconds"],
                                "max_abs_error": result["metrics"].get("max_abs_error"),
                                "diagnostic": result["diagnostic"],
                                "execution": result["details"].get("execution")
                                if isinstance(result["details"], dict) else None})
        valid = [s for s in samples if s["valid"]]
        profile = {"backend": backend, "signature": signature, "created_utc": created,
                   "experiment_id": experiment_id, "input_class": input_class, "domain": domain,
                   "error_metric": ERROR_METRIC, "time_scope": TIME_SCOPE,
                   "conditions": {"repeats": repeats, "warmup": warmup,
                                  "cache_policy": "reuse_existing", "case_order": "provided",
                                  "cases": [{"F": F, "K": K} for F, K in cases]},
                   "warmup_observations": warmups, "samples": samples,
                   "summary": {"max_abs_error": max((s["max_abs_error"] for s in valid), default=None),
                               "max_seconds": max(s["observed_seconds"] for s in samples),
                               "failure_rate": (len(samples) - len(valid)) / len(samples)}}
        profile["id"] = hashlib.sha256(json.dumps(profile, default=json_value,
                                                  sort_keys=True, allow_nan=False).encode()).hexdigest()
        profiles.append(profile)
    # Converte arrays e registros de subprocesso para um documento pronto para JSON.
    document = json.loads(json.dumps({"schema_version": 1, "profiles": profiles,
                                      "unavailable": unavailable}, default=json_value, allow_nan=False))
    return validate_profiles(document)
