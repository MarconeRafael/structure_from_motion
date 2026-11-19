"""Métrica de erro, serialização e identidade das implementações medidas."""

from dataclasses import asdict, is_dataclass
import hashlib
import json
import platform
from pathlib import Path
import shutil
import sys

import numpy as np

from .ghdl_backend import BackendError, FLAGS, PROJECT_ROOT, SOURCES, _run_process

ERROR_METRIC = "max_abs_entry_vs_numpy_float64_v1"
TIME_SCOPE = "backend_attempt_including_validation_v1"


def json_value(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"Tipo não serializável: {type(value).__name__}")


def write_json(path, value):
    Path(path).write_text(json.dumps(value, default=json_value, ensure_ascii=False,
                                    allow_nan=False, indent=2) + "\n", encoding="utf-8")


def implementation_signature(backend, config, rtl_backend=None):
    files = [PROJECT_ROOT / "hybrid_sfm" / name for name in ("backends.py", "reference.py", "metrics.py")]
    identity = {"python": sys.version, "numpy": np.__version__,
                "platform": platform.platform(), "machine": platform.machine(),
                "processor": platform.processor(), "python_executable": sys.executable,
                "error_metric": ERROR_METRIC, "time_scope": TIME_SCOPE}
    if backend == "rtl_simulated":
        from .backends import rtl_instance
        rtl = rtl_backend or rtl_instance(config)
        executable = shutil.which(rtl.ghdl)
        if executable is None:
            raise BackendError("tool", f"GHDL não encontrado: {rtl.ghdl}")
        executable = str(Path(executable).resolve())
        version = _run_process([executable, "--version"], rtl.project_root, config.timeout, "tool")
        files.extend(PROJECT_ROOT / "hybrid_sfm" / name for name in ("ghdl_backend.py", "fixed_point.py"))
        files.extend(rtl.project_root / name for name in SOURCES)
        identity.update(ghdl=version.stdout.strip(), ghdl_executable=executable,
                        flags=list(FLAGS), timeout=rtl.timeout, max_cycles=rtl.max_cycles)
    else:
        identity["ghdl"] = None
    identity["implementation_sha256"] = hashlib.sha256(
        b"\0".join(path.read_bytes() for path in files)).hexdigest()
    return identity
