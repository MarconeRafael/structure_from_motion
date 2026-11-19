"""Métrica de erro, serialização e identidade das implementações medidas."""

from dataclasses import asdict, is_dataclass
import hashlib
import json
import os
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


def _signature_inputs(backend, config, rtl_backend):
    files = [PROJECT_ROOT / "hybrid_sfm" / name for name in ("backends.py", "reference.py", "metrics.py")]
    rtl, executable = None, None
    if backend == "rtl_simulated":
        from .backends import rtl_instance
        rtl = rtl_backend or rtl_instance(config)
        executable = shutil.which(rtl.ghdl)
        if executable is None:
            raise BackendError("tool", f"GHDL não encontrado: {rtl.ghdl}")
        executable = Path(executable).resolve()
        files.extend(PROJECT_ROOT / "hybrid_sfm" / name for name in ("ghdl_backend.py", "fixed_point.py"))
        files.extend(rtl.project_root / name for name in SOURCES)
    return files, rtl, executable


def signature_fingerprint(backend, config, rtl_backend=None):
    """Identidade barata de arquivos, configuração e resolução da ferramenta."""
    files, rtl, executable = _signature_inputs(backend, config, rtl_backend)
    entries = []
    for path in files + ([executable] if executable is not None else []):
        stat = path.stat()
        entries.append((str(path), stat.st_dev, stat.st_ino, stat.st_size,
                        stat.st_mtime_ns, stat.st_ctime_ns))
    return (tuple(entries), config, sys.version, np.__version__, sys.executable, tuple(FLAGS),
            (rtl.ghdl, rtl.timeout, rtl.max_cycles) if rtl is not None else None,
            tuple(os.environ.get(key) for key in ("PATH", "PATHEXT", "GHDL", "GHDL_PREFIX", "LD_LIBRARY_PATH")))


def implementation_signature(backend, config, rtl_backend=None):
    files, rtl, executable = _signature_inputs(backend, config, rtl_backend)
    identity = {"python": sys.version, "numpy": np.__version__,
                "platform": platform.platform(), "machine": platform.machine(),
                "processor": platform.processor(), "python_executable": sys.executable,
                "error_metric": ERROR_METRIC, "time_scope": TIME_SCOPE}
    if backend == "rtl_simulated":
        version = _run_process([str(executable), "--version"], rtl.project_root, config.timeout, "tool")
        with executable.open("rb") as stream:
            digest = hashlib.sha256()
            for block in iter(lambda: stream.read(1 << 20), b""):
                digest.update(block)
        identity.update(ghdl=version.stdout.strip(), ghdl_executable=str(executable),
                        ghdl_executable_sha256=digest.hexdigest(),
                        ghdl_prefix=os.environ.get("GHDL_PREFIX"), ld_library_path=os.environ.get("LD_LIBRARY_PATH"),
                        flags=list(FLAGS), timeout=rtl.timeout, max_cycles=rtl.max_cycles)
    else:
        identity["ghdl"] = None
    identity["implementation_sha256"] = hashlib.sha256(
        b"\0".join(path.read_bytes() for path in files)).hexdigest()
    return identity
