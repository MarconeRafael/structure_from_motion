"""Execução sequencial dos experimentos A–E e persistência de evidências brutas."""

from collections import defaultdict
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np

from hybrid_sfm.backends import BACKENDS, ExecutionConfig, run_backend
from hybrid_sfm.fixed_point import essential_matrix_fixed
from hybrid_sfm.ghdl_backend import BackendError, GhdlBackend, PROJECT_ROOT
from hybrid_sfm.manager import ExecutionManager, Requirements
from hybrid_sfm.metrics import implementation_signature, json_value, write_json
from hybrid_sfm.profiles import characterize, validate_profiles
from hybrid_sfm.reference import essential_matrix
from .analysis import figures, numerical_metrics, policy_comparisons, summarize, write_csv
from .datasets import SPLITS, digest, generate_dataset
from .faults import run_faults


def validate_config(config):
    if config.get("schema_version") != 1:
        raise ValueError("Versão de configuração inválida")
    for key in ("replications", "profile_repeats", "timing_repeats", "policy_repeats"):
        if type(config[key]) is not int or config[key] <= 0:
            raise ValueError(f"{key} deve ser inteiro positivo")
    if type(config["warmup"]) is not int or config["warmup"] < 0:
        raise ValueError("warmup inválido")
    if not np.isfinite(config["relative_zero_threshold"]) or config["relative_zero_threshold"] <= 0:
        raise ValueError("Limiar de zero inválido")
    ids = set()
    for scenario in config["scenarios"]:
        if not isinstance(scenario["id"], str) or not scenario["id"] or scenario["id"] in ids:
            raise ValueError("IDs de cenários devem ser únicos")
        ids.add(scenario["id"])
        Requirements(**{key: value for key, value in scenario.items() if key != "id"})
    if not ids:
        raise ValueError("Configuração sem cenários")
    return config


def source_hashes():
    paths = [PROJECT_ROOT / "run_experiments.py", PROJECT_ROOT / "extract_points.py"]
    for folder, pattern in (("experiments", "*.py"), ("hybrid_sfm", "*.py"), ("src", "*.vhd"), ("tb", "*.vhd"), ("tests", "*.py")):
        paths.extend((PROJECT_ROOT / folder).glob(pattern))
    import hashlib
    return {str(path.relative_to(PROJECT_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


def _tests(output, config):
    env = dict(os.environ, REQUIRE_GHDL="1", REQUIRE_OPENCV="1", GHDL=str(config.ghdl or os.environ.get("GHDL", "ghdl")))
    completed = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                               cwd=PROJECT_ROOT, env=env, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=180, shell=False)
    (output / "tests.txt").write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"Suíte falhou: veja {output / 'tests.txt'}")


def _policy_row(case, scenario, mode, result, replication, repetition):
    attempts = result["attempts"]
    error = attempts[-1]["metrics"].get("max_abs_error") if attempts else None
    violations = [a.get("diagnostic", {}).get("violations", []) for a in attempts if a.get("diagnostic")]
    return {"replication": replication, "case_id": case["id"], "category": case["category"],
            "family": case["family"], "split": case["split"], "scenario": scenario["id"],
            "policy": mode, "repetition": repetition, "status": result["status"], "valid": result["valid"],
            "selected_backend": result["selected_backend"], "backend": result["backend"],
            "max_error": scenario["max_error"], "max_seconds": scenario["max_seconds"],
            "max_abs_error_observed": error, "error_violation": any("max_error" in v for v in violations),
            "time_overrun": scenario["max_seconds"] is not None and result["metrics"]["total_seconds"] > scenario["max_seconds"],
            "E_hash": digest(result["E"]) if result["E"] is not None else None,
            "selection_reasons": result["decision"]["candidates"], **result["metrics"]}


def _numerical(case, rtl, replication, epsilon):
    row = {"replication": replication, "case_id": case["id"], "category": case["category"],
           "family": case["family"], "valid": False, "bit_exact": None, "integer_max_raw_difference": None,
           "overflow": False, "absolute_error": None, "relative_error": None,
           "E_raw_hash": None, "status": "error"}
    try:
        result = rtl.run(case["F"], case["K"])
        model = essential_matrix_fixed(case["F"], case["K"])
        reference = essential_matrix(case["F"], case["K"])
        row.update(valid=result["valid"], bit_exact=bool(np.array_equal(result["E_raw"], model.raw)),
                   integer_max_raw_difference=int(np.max(np.abs(result["E_raw"] - model.raw))),
                   overflow=model.overflow, overflow_events=model.overflow_events,
                   E_raw_hash=digest(result["E_raw"]), status=result["status"],
                   **numerical_metrics(result["E"], reference, epsilon,
                                       geometric=case["category"] != "controlled",
                                       ground_truth=case["metadata"].get("E_ground_truth")))
        return row, result
    except (BackendError, ValueError) as exc:
        return row, {"stage": getattr(exc, "stage", "input"), "message": str(exc),
                     "process": getattr(exc, "process", None)}


def _timing_row(case, result, replication, repetition):
    execution = result["details"].get("execution", {}) if isinstance(result["details"], dict) else {}
    process = execution.get("simulation")
    return {"replication": replication, "case_id": case["id"], "category": case["category"],
            "family": case["family"], "repetition": repetition, "backend": result["backend"],
            "valid": result["valid"], "status": result["status"], **result["metrics"],
            "preparation_seconds": execution.get("preparation_seconds"),
            "serialization_seconds": execution.get("serialization_seconds"),
            "compilation_seconds": execution.get("compilation", {}).get("seconds"),
            "compile_cache_hit": execution.get("compilation", {}).get("cache_hit"),
            "ghdl_process_seconds": process.seconds if process is not None else None,
            "ghdl_startup_seconds": None, "ghdl_simulator_only_seconds": None,
            "parsing_seconds": execution.get("parsing_seconds"),
            "diagnostic": result["diagnostic"]}


def _reproducibility(numeric, policies):
    groups = defaultdict(list)
    for row in numeric:
        groups[("numeric", row["case_id"])].append((row["status"], row["E_raw_hash"], row["bit_exact"]))
    for row in policies:
        groups[("policy", row["case_id"], row["scenario"], row["policy"], row["repetition"])].append(
            (row["selected_backend"], row["backend"], row["status"], row["E_hash"], row["fallback_count"]))
    return [{"kind": key[0], "key": list(key[1:]), "observations": len(values),
             "comparable": len(values) >= 2, "stable": len(set(values)) == 1 if len(values) >= 2 else None}
            for key, values in groups.items()]


def run(config, *, ghdl=None, output_override=None):
    config = validate_config(config)
    execution_config = ExecutionConfig(ghdl=ghdl, timeout=config["timeout"])
    # Validação de dependências ocorre antes de criar qualquer perfil ou benchmark.
    versions = {name: importlib.metadata.version(name) for name in ("numpy", "opencv-python-headless", "matplotlib")}
    signatures = {name: implementation_signature(name, execution_config) for name in BACKENDS}
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    base = Path(output_override or config["output_dir"])
    if not base.is_absolute():
        base = PROJECT_ROOT / base
    output = base / run_id
    output.mkdir(parents=True, exist_ok=False)
    metadata = {"run_id": run_id, "created_utc": datetime.now(timezone.utc).isoformat(),
                "status": "running", "config": config, "config_sha256": digest(config),
                "python": sys.version, "versions": versions, "platform": platform.platform(),
                "processor": platform.processor(), "machine": platform.machine(),
                "perf_counter": str(time.get_clock_info("perf_counter")), "signatures": signatures,
                "source_sha256": source_hashes(), "unmeasurable": ["ghdl_startup_seconds", "ghdl_simulator_only_seconds"],
                "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True).strip(),
                "git_status": subprocess.check_output(["git", "status", "--short"], cwd=PROJECT_ROOT, text=True)}
    write_json(output / "metadata.json", metadata)
    write_json(output / "config.json", config)
    freeze = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
    (output / "requirements-lock.txt").write_text(freeze, encoding="utf-8")
    print(f"Saída: {output}", flush=True)
    _tests(output, execution_config)
    print("Auditoria de testes aprovada; gerando dados e verificando repetição de sementes", flush=True)
    dataset = generate_dataset(config["dataset_seed"])
    regenerated = generate_dataset(config["dataset_seed"])
    if digest(dataset) != digest(regenerated):
        raise RuntimeError("Dataset não é reproduzível com a mesma semente")
    write_json(output / "dataset.json", dataset)
    metadata["dataset_sha256"] = digest(dataset)
    metadata["dataset_regeneration_identical"] = True
    cases = dataset["cases"]
    split_cases = {split: [c for c in cases if c["split"] == split] for split in SPLITS}
    write_json(output / "splits.json", {split: [c["id"] for c in group] for split, group in split_cases.items()})
    numeric, timing, policies, faults = [], [], [], []
    frozen_scenario = None
    raw_path = output / "raw.jsonl"
    with raw_path.open("w", encoding="utf-8") as raw_stream:
        def save_raw(kind, data):
            raw_stream.write(json.dumps({"kind": kind, "data": data}, default=json_value, allow_nan=False) + "\n")
            raw_stream.flush()
        for replication in range(config["replications"]):
            print(f"Repetição independente {replication + 1}/{config['replications']}: compilação e perfis", flush=True)
            rtl = GhdlBackend(ghdl=ghdl, timeout=config["timeout"],
                              build_dir=PROJECT_ROOT / "build/experiment_cache" / run_id / str(replication))
            _, compilation = rtl.compile()
            save_raw("cold_compilation", {"replication": replication, "compilation": compilation})
            profile_document = {"schema_version": 1, "profiles": [], "unavailable": []}
            for family in sorted({c["family"] for c in split_cases["characterization"]}):
                group = [c for c in split_cases["characterization"] if c["family"] == family]
                measured = characterize([(c["F"], c["K"]) for c in group], config=execution_config,
                                        rtl_backend=rtl, repeats=config["profile_repeats"], warmup=config["warmup"],
                                        input_class=family, experiment_id=f"{run_id}/rep{replication}/{family}")
                profile_document["profiles"].extend(measured["profiles"])
                profile_document["unavailable"].extend(measured["unavailable"])
            validate_profiles(profile_document)
            write_json(output / f"profiles_{replication}.json", profile_document)
            manager = ExecutionManager(profile_document, config=execution_config, rtl_backend=rtl)
            if frozen_scenario is None:
                development = []
                for scenario in config["scenarios"]:
                    for case in split_cases["development"]:
                        requirements = Requirements(**{k: v for k, v in scenario.items() if k != "id"})
                        result = manager.execute(case["F"], case["K"], requirements=requirements, input_class=case["family"])
                        development.append(_policy_row(case, scenario, "auto", result, replication, 0))
                        save_raw("development", {"case_id": case["id"], "scenario": scenario["id"], "result": result})
                write_csv(output / "development.csv", development)
                # Critério predefinido: maior sucesso, menor tolerância e ID; sem usar avaliação final.
                frozen_scenario = min(config["scenarios"], key=lambda s: (
                    -sum(r["valid"] for r in development if r["scenario"] == s["id"]), s["max_error"], s["id"]))["id"]
                write_json(output / "frozen_policy.json", {"scenario_id": frozen_scenario,
                           "rule": "max development successes, then smallest max_error, then scenario id",
                           "frozen_before_final_evaluation": True, "evaluation_results_used": False})
            print(f"Repetição {replication + 1}: A validação numérica; B tempos", flush=True)
            for case in split_cases["evaluation"]:
                row, result = _numerical(case, rtl, replication, config["relative_zero_threshold"])
                numeric.append(row)
                save_raw("numeric", {**row, "result": result})
            order_rng = np.random.default_rng(config["order_seed"] + replication)
            for repetition in range(config["timing_repeats"]):
                for index in order_rng.permutation(len(split_cases["evaluation"])):
                    case = split_cases["evaluation"][int(index)]
                    for backend in order_rng.permutation(BACKENDS):
                        result = run_backend(str(backend), case["F"], case["K"], execution_config, rtl_backend=rtl)
                        row = _timing_row(case, result, replication, repetition)
                        timing.append(row)
                        save_raw("timing", {**row, "result": result})
            print(f"Repetição {replication + 1}: C políticas nos mesmos casos finais", flush=True)
            for scenario in config["scenarios"]:
                requirements = Requirements(**{k: v for k, v in scenario.items() if k != "id"})
                for repetition in range(config["policy_repeats"]):
                    for index in order_rng.permutation(len(split_cases["evaluation"])):
                        case = split_cases["evaluation"][int(index)]
                        for mode in order_rng.permutation((*BACKENDS, "auto")):
                            result = manager.execute(case["F"], case["K"], mode=str(mode), requirements=requirements,
                                                     input_class=case["family"])
                            row = _policy_row(case, scenario, str(mode), result, replication, repetition)
                            row["frozen_default_scenario"] = scenario["id"] == frozen_scenario
                            policies.append(row)
                            save_raw("policy", {**row, "result": result})
            if replication == 0:
                print("D falhas controladas e recuperação (fora das taxas naturais)", flush=True)
                faults = run_faults(execution_config, rtl, save_raw)
    comparisons = policy_comparisons(policies)
    tables = summarize(numeric, timing, policies, faults, comparisons)
    reproducibility = _reproducibility(numeric, policies)
    for name, rows in (("numeric", numeric), ("timing", timing), ("policies", policies),
                       ("faults", faults), ("comparisons", comparisons), ("reproducibility", reproducibility)):
        write_csv(output / f"{name}.csv", rows)
    for name, rows in tables.items():
        write_csv(output / f"table_{name}.csv", rows)
    write_json(output / "summary.json", {"tables": tables, "reproducibility": reproducibility,
                                        "frozen_scenario": frozen_scenario})
    print("E repetibilidade; gerando tabelas e figuras", flush=True)
    figures(output / "figures", numeric, timing, policies)
    metadata.update(status="complete", completed_utc=datetime.now(timezone.utc).isoformat(),
                    counts={"dataset_cases": len(cases), "evaluation_cases": len(split_cases["evaluation"]),
                            "numeric_rows": len(numeric), "timing_rows": len(timing), "policy_rows": len(policies),
                            "fault_rows": len(faults)},
                    checks={"bit_exact_all_exported": all(r["bit_exact"] is True for r in numeric if r["bit_exact"] is not None),
                            "all_faults_detected": all(r["detection_ok"] for r in faults),
                            "numeric_repeat_stable": all(r["stable"] for r in reproducibility if r["kind"] == "numeric" and r["comparable"])})
    if not all(metadata["checks"].values()):
        metadata["status"] = "failed_checks"
    write_json(output / "metadata.json", metadata)
    from .report import write_report
    write_report(output, metadata, tables, reproducibility)
    print(json.dumps({"output": str(output), "counts": metadata["counts"], "checks": metadata["checks"]}), flush=True)
    if not all(metadata["checks"].values()):
        raise RuntimeError("Uma verificação experimental falhou; consulte os resultados")
    return output
