"""Compilação mínima e protocolo de arquivos do kernel essencial."""

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

import numpy as np

from .fixed_point import MAX_RAW, MIN_RAW, SCALE, essential_matrix_raw, quantize
from .reference import essential_matrix, matrix3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("src/fixed_pkg.vhd", "src/algebra_pkg.vhd", "src/algebra_pkg_body.vhd",
           "src/essential_matrix.vhd", "tb/tb_essential_io.vhd")
ENTITY = "tb_essential_io"
FLAGS = ("--std=08",)


@dataclass
class ProcessRecord:
    command: list
    stdout: str
    stderr: str
    returncode: int | None
    seconds: float


class BackendError(RuntimeError):
    def __init__(self, stage, message, process=None):
        super().__init__(message)
        self.stage = stage
        self.process = process


def _run_process(command, cwd, timeout, stage):
    started = time.perf_counter()
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=timeout,
                                shell=False)
    except subprocess.TimeoutExpired as exc:
        def decode(value):
            return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""
        record = ProcessRecord(command, decode(exc.stdout), decode(exc.stderr), None,
                               time.perf_counter() - started)
        raise BackendError("timeout", f"Timeout em {stage}", record) from exc
    except OSError as exc:
        raise BackendError(stage, f"Não foi possível executar {command[0]}: {exc}") from exc
    record = ProcessRecord(command, result.stdout, result.stderr, result.returncode,
                           time.perf_counter() - started)
    if result.returncode != 0:
        raise BackendError(stage, f"Falha em {stage} (exit {result.returncode})", record)
    return record


def parse_output(path, expected_count, max_cycles):
    try:
        rows = Path(path).read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError) as exc:
        raise BackendError("parsing", f"Saída ausente ou ilegível: {exc}") from exc
    if len(rows) != expected_count + 1 or rows[0] != "essential-q15.16-v1":
        raise BackendError("parsing", "Cabeçalho ou quantidade de resultados inválidos")
    results = []
    for index, row in enumerate(rows[1:]):
        tokens = row.split()
        if len(tokens) != 11 or any(re.fullmatch(r"[+-]?[0-9]+", x) is None for x in tokens):
            raise BackendError("parsing", "Resultado deve conter índice, ciclos e nove inteiros")
        values = [int(x) for x in tokens]
        if (values[0] != index or not 1 <= values[1] <= max_cycles
                or any(not MIN_RAW <= x <= MAX_RAW for x in values[2:])):
            raise BackendError("parsing", "Índice, ciclos ou inteiro Q15.16 inválido")
        results.append((np.array(values[2:], dtype=np.int64).reshape(3, 3), values[1]))
    return results


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class GhdlBackend:
    def __init__(self, ghdl=None, project_root=PROJECT_ROOT, build_dir=None, timeout=30.0,
                 max_cycles=10):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout deve ser finito e positivo")
        if isinstance(max_cycles, bool) or not isinstance(max_cycles, int) or max_cycles <= 0:
            raise ValueError("max_cycles deve ser inteiro positivo")
        self.project_root = Path(project_root).resolve()
        self.build_dir = Path(build_dir or self.project_root / "build/essential").resolve()
        self.timeout = timeout
        self.max_cycles = max_cycles
        self.ghdl = str(ghdl or os.environ.get("GHDL", "ghdl"))

    def compile(self):
        executable = shutil.which(self.ghdl)
        if executable is None:
            raise BackendError("tool", f"GHDL não encontrado: {self.ghdl}. Configure PATH ou GHDL.")
        executable = str(Path(executable).resolve())
        version = _run_process([executable, "--version"], self.project_root, self.timeout, "tool")
        try:
            source_state = [(name, _hash(self.project_root / name),
                             (self.project_root / name).stat().st_mtime_ns) for name in SOURCES]
        except OSError as exc:
            raise BackendError("compilation", f"Dependência VHDL ausente: {exc}") from exc
        key = hashlib.sha256(json.dumps([executable, version.stdout, FLAGS, source_state],
                                       sort_keys=True).encode()).hexdigest()
        directory = self.build_dir / key
        manifest = directory / "manifest.json"
        if manifest.is_file():
            try:
                artifacts = json.loads(manifest.read_text(encoding="utf-8"))
                if (artifacts and (directory / "work-obj08.cf").is_file()
                        and all(Path(name).name == name and _hash(directory / name) == digest
                                for name, digest in artifacts.items())):
                    return directory, {"cache_hit": True, "seconds": 0.0,
                                       "processes": [], "version": version.stdout}
            except (OSError, ValueError, AttributeError, TypeError):
                pass
        directory.mkdir(parents=True, exist_ok=True)
        # Um manifesto só é publicado depois de análise e elaboração concluídas.
        manifest.unlink(missing_ok=True)
        (directory / "work-obj08.cf").unlink(missing_ok=True)
        records = []
        for source in SOURCES:
            records.append(_run_process([executable, "-a", *FLAGS, "--workdir=.",
                                         str(self.project_root / source)], directory,
                                        self.timeout, "compilation"))
        records.append(_run_process([executable, "-e", *FLAGS, "--workdir=.", ENTITY],
                                    directory, self.timeout, "compilation"))
        artifacts = {p.name: _hash(p) for p in directory.iterdir() if p.is_file()}
        manifest.write_text(json.dumps(artifacts, sort_keys=True), encoding="utf-8")
        return directory, {"cache_hit": False, "seconds": sum(p.seconds for p in records),
                           "processes": records, "version": version.stdout}

    def run(self, F, K):
        return self.run_batch([(F, K)])["results"][0]

    def run_batch(self, cases, reset_before=None):
        started = time.perf_counter()
        cases = [(matrix3(F).copy(), matrix3(K).copy()) for F, K in cases]
        if not cases:
            raise ValueError("Forneça pelo menos um par (F, K)")
        resets = list(reset_before) if reset_before is not None else [True] + [False] * (len(cases) - 1)
        if (len(resets) != len(cases) or any(type(x) is not bool for x in resets)
                or not resets[0]):
            raise ValueError("reset_before requer booleanos e reset no primeiro caso")
        prepared = []
        for F, K in cases:
            Fq, Kq = quantize(F), quantize(K)
            model = essential_matrix_raw(Fq, Kq)
            reference = essential_matrix(F, K)
            quantized_reference = essential_matrix(Fq / SCALE, Kq / SCALE)
            prepared.append((Fq, Kq, model, reference, quantized_reference))
        preparation_seconds = time.perf_counter() - started
        directory, compilation = self.compile()
        executable = shutil.which(self.ghdl)
        with tempfile.TemporaryDirectory(prefix="run-", dir=self.build_dir) as temporary:
            temporary = Path(temporary)
            input_path, output_path = temporary / "matrices.in", temporary / "matrices.out"
            serial_start = time.perf_counter()
            lines = [str(len(cases))]
            for reset, (Fq, Kq, *_rest) in zip(resets, prepared):
                lines.append(str(int(reset)))
                lines.extend(str(int(x)) for matrix in (Fq, Kq) for x in matrix.flat)
            input_path.write_text("\n".join(lines) + "\n", encoding="ascii")
            serialization_seconds = time.perf_counter() - serial_start
            process = _run_process([str(Path(executable).resolve()), "-r", *FLAGS, "--workdir=.",
                                    ENTITY, f"-ginput_file={input_path}", f"-goutput_file={output_path}",
                                    f"-gmax_cycles={self.max_cycles}", "--assert-level=error"],
                                   directory, self.timeout, "simulation")
            parse_start = time.perf_counter()
            outputs = parse_output(output_path, len(cases), self.max_cycles)
            parsing_seconds = time.perf_counter() - parse_start
        results = []
        for (raw, cycles), (_, _, model, reference, quantized_reference) in zip(outputs, prepared):
            if not np.array_equal(raw, model.raw):
                raise BackendError("numerical_mismatch", "GHDL difere do modelo inteiro", process)
            value = raw.astype(np.float64) / SCALE
            results.append({"status": "numeric_overflow" if model.overflow else "ok",
                            "valid": not model.overflow, "E": value, "E_raw": raw,
                            "reference_float64": reference, "reference_integer_raw": model.raw,
                            "reference_quantized_float64": quantized_reference, "bit_exact": True,
                            "overflow_events": model.overflow_events, "cycles": cycles,
                            "max_abs_error": float(np.max(np.abs(value - reference))),
                            "input_quantization_max_abs_error": float(np.max(np.abs(quantized_reference - reference))),
                            "arithmetic_max_abs_error": float(np.max(np.abs(value - quantized_reference)))})
        metadata = {"compilation": compilation, "simulation": process,
                    "preparation_seconds": preparation_seconds,
                    "serialization_seconds": serialization_seconds, "parsing_seconds": parsing_seconds,
                    "total_seconds": time.perf_counter() - started}
        for result in results:
            result["execution"] = metadata
        return {"results": results, "execution": metadata}
