"""Injeção de falhas controladas, segregada das taxas de falhas naturais."""

from contextlib import nullcontext
import hashlib
from pathlib import Path
import tempfile
from unittest.mock import patch

import numpy as np

from hybrid_sfm.backends import ExecutionConfig
from hybrid_sfm.ghdl_backend import GhdlBackend, SOURCES, _run_process
from hybrid_sfm.manager import ExecutionManager, Requirements
from hybrid_sfm.profiles import characterize


def run_faults(config, rtl, save_raw):
    profiles = characterize([(np.eye(3), np.eye(3)), (-np.eye(3), np.eye(3))],
                             config=config, rtl_backend=rtl, repeats=2, warmup=1,
                             input_class="fault_fixture", experiment_id="controlled_fault_fixture")
    rows = []
    # Fontes mutantes existem apenas no diretório de build desta execução.
    with tempfile.TemporaryDirectory(prefix="fault-", dir=rtl.build_dir.parent) as temporary:
        mutant_root = Path(temporary)
        for source in SOURCES:
            target = mutant_root / source
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((rtl.project_root / source).read_bytes())
        path = mutant_root / "src/essential_matrix.vhd"
        content = path.read_bytes()
        original = b"E_out <= E_temp;"
        if original not in content:
            raise ValueError("Ponto de injeção de estado indefinido não encontrado")
        path.write_bytes(content.replace(original, b"E_out <= E_temp when ready /= '1' else (others => (others => (others => 'X')));"))
        mutant = GhdlBackend(ghdl=rtl.ghdl, project_root=mutant_root,
                             build_dir=mutant_root / "cache", timeout=config.timeout)
        mutant_directory, compilation = mutant.compile()
        save_raw("fault_setup", {"mutant_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                  "compilation": compilation, "profiles": profiles,
                                  "description": "X after ready in disposable RTL copy"})
        for fault in ("unavailable_before_selection", "unavailable_after_selection", "timeout",
                      "invalid_file", "incomplete_output", "undefined_rtl", "numeric_limit"):
            for fallback_policy in ("software", "none", "no_alternative"):
                used_profiles = profiles if fallback_policy != "no_alternative" else {
                    **profiles, "profiles": [p for p in profiles["profiles"] if p["backend"] == "rtl_simulated"]}
                active_config = config
                active_rtl = rtl
                if fault == "unavailable_before_selection":
                    active_config = ExecutionConfig(ghdl="ghdl-deliberately-unavailable-stage3", timeout=config.timeout)
                    active_rtl = GhdlBackend(ghdl=active_config.ghdl, build_dir=rtl.build_dir, timeout=config.timeout)
                manager = ExecutionManager(used_profiles, config=active_config, rtl_backend=active_rtl)
                def inject(command, cwd, timeout, stage):
                    if stage != "simulation":
                        return _run_process(command, cwd, timeout, stage)
                    if fault == "timeout":
                        return _run_process(command, cwd, .000001, stage)
                    if fault == "unavailable_after_selection":
                        return _run_process(["ghdl-deliberately-unavailable-stage3", *command[1:]], cwd, timeout, stage)
                    record = _run_process(command, mutant_directory if fault == "undefined_rtl" else cwd, timeout, stage)
                    if fault in ("invalid_file", "incomplete_output"):
                        output = Path(next(arg.split("=", 1)[1] for arg in command if arg.startswith("-goutput_file=")))
                        output.write_text("invalid\n" if fault == "invalid_file" else "essential-q15.16-v1\n0 1 0\n", encoding="ascii")
                    return record
                requirements = Requirements(max_error=0 if fault == "numeric_limit" else .01,
                                            preference="prefer_rtl",
                                            fallback="none" if fallback_policy == "none" else "software")
                context = nullcontext() if fault in ("unavailable_before_selection", "numeric_limit") else patch(
                    "hybrid_sfm.ghdl_backend._run_process", side_effect=inject)
                with context:
                    result = manager.execute(np.eye(3) * (.1 if fault == "numeric_limit" else 1), np.eye(3),
                                             requirements=requirements, input_class="fault_fixture")
                if fault == "unavailable_before_selection":
                    detected = result["selected_backend"] == (None if fallback_policy == "no_alternative" else "software")
                else:
                    detected = (result["selected_backend"] == "rtl_simulated" and
                                not result["metrics"]["initial_selection_success"] and
                                ((result["status"] == "fallback_ok" and result["backend"] == "software")
                                 if fallback_policy == "software" else not result["valid"]))
                row = {"fault": fault, "fallback_policy": fallback_policy, "injected": True,
                       "status": result["status"], "selected_backend": result["selected_backend"],
                       "backend": result["backend"], "valid": result["valid"],
                       "initial_success": result["metrics"]["initial_selection_success"],
                       "fallback_count": result["metrics"]["fallback_count"],
                       "failure_count": result["metrics"]["failure_count"],
                       "initial_attempt_seconds": result["metrics"]["initial_attempt_seconds"],
                       "fallback_seconds": result["metrics"]["fallback_seconds"],
                       "total_seconds": result["metrics"]["total_seconds"], "detection_ok": detected}
                save_raw("fault", {**row, "result": result})
                rows.append(row)
    return rows
