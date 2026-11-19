"""Avaliação pareada da Etapa 4. Executar com python -m experiments.stage4."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np

from experiments.analysis import quantiles, summarize, policy_comparisons, write_csv
from experiments.datasets import digest
from experiments.stage4_geometry import cases, evaluate
from hybrid_sfm.backends import BACKENDS, ExecutionConfig
from hybrid_sfm.ghdl_backend import GhdlBackend, PROJECT_ROOT
from hybrid_sfm.manager import ExecutionManager, Requirements
from hybrid_sfm.metrics import implementation_signature, write_json
from hybrid_sfm.profiles import characterize


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hash(path):
    return {p.relative_to(path).as_posix(): file_hash(p) for p in sorted(path.rglob("*")) if p.is_file()}


def matches_recorded_source(path, expected):
    data = path.read_bytes()
    lf = data.replace(b"\r\n", b"\n")
    # Git pode normalizar o snapshot em um checkout Linux. Aceita somente
    # equivalência demonstrável por conversão de finais de linha.
    return any(hashlib.sha256(candidate).hexdigest() == expected
               for candidate in (data, lf, lf.replace(b"\n", b"\r\n")))


def audit(historical):
    metadata = read_json(historical / "metadata.json")
    dataset = read_json(historical / "dataset.json")
    snapshot = historical / "source_snapshot"
    if digest(dataset) != metadata["dataset_sha256"] or digest(metadata["config"]) != metadata["config_sha256"]:
        raise ValueError("Hash histórico de dataset ou configuração inválido")
    historical_sources = {name.replace("\\", "/"): sha for name, sha in metadata["source_sha256"].items()}
    for name, sha in historical_sources.items():
        if not matches_recorded_source(snapshot / name, sha):
            raise ValueError(f"Snapshot não corresponde ao hash histórico: {name}")
    # Permite comparar gestores sobre o mesmo cálculo e simulador.
    for name in ("hybrid_sfm/backends.py", "hybrid_sfm/reference.py", "hybrid_sfm/fixed_point.py",
                 "hybrid_sfm/ghdl_backend.py", "src/essential_matrix.vhd", "src/algebra_pkg_body.vhd",
                 "src/algebra_pkg.vhd", "src/fixed_pkg.vhd", "tb/tb_essential_io.vhd"):
        sha = historical_sources[name]
        if file_hash(PROJECT_ROOT / name) != sha:
            # Git pode converter finais de linha entre plataformas.
            old = (snapshot / name).read_bytes().replace(b"\r\n", b"\n")
            if (PROJECT_ROOT / name).read_bytes().replace(b"\r\n", b"\n") != old:
                raise ValueError(f"Backend atual difere do histórico: {name}")
    by_kind = {key: [] for key in ("numeric", "timing", "policy", "fault")}
    with (historical / "raw.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["kind"] in by_kind:
                by_kind[row["kind"]].append(row["data"])
    n, t, p, f = (by_kind[key] for key in by_kind)
    if summarize(n, t, p, f, policy_comparisons(p)) != read_json(historical / "summary.json")["tables"]:
        raise ValueError("Tabelas históricas inconsistentes")
    all_cases = dataset["cases"]
    splits = {part: [case for case in all_cases if case["split"] == part]
              for part in ("characterization", "development", "evaluation")}
    image_pools = [{idx for case in group if case["category"] == "repository_images"
                    for idx in case["metadata"]["point_ids"]} for group in splits.values()]
    if (len({digest([c["F"], c["K"]]) for c in all_cases}) != len(all_cases)
            or sum(map(len, image_pools)) != len(set.union(*image_pools))):
        raise ValueError("Repetição cruzada de matrizes ou correspondências")
    return metadata, splits


def load_snapshot(historical, module):
    spec = importlib.util.spec_from_file_location(
        f"hybrid_sfm._historical_{module}", historical / "source_snapshot/hybrid_sfm" / f"{module}.py")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    source = Path(spec.origin)
    exec(compile(source.read_bytes(), str(source), "exec"), vars(loaded))
    return loaded


def _reason_labels(result):
    return [f"{c['backend']}:{r['code']}" + (f":{r['detail']}" if "detail" in r else "")
            for c in result["decision"]["candidates"] for r in c["reasons"]]


def run(config, ghdl):
    root = PROJECT_ROOT
    historical = (root / config["historical_run"]).resolve()
    bases = root / "experiments/results"
    hashes_before = tree_hash(bases)
    historical_meta, splits = audit(historical)
    original = load_snapshot(historical, "manager")
    original_metrics = load_snapshot(historical, "metrics")
    original_metrics.PROJECT_ROOT = historical / "source_snapshot"
    ec = ExecutionConfig(ghdl=ghdl, timeout=historical_meta["config"]["timeout"])
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    base = (root / config["output_dir"]).resolve()
    if any(base == path or path in base.parents for path in (bases.resolve(), historical)):
        raise ValueError("A saída deve ficar fora dos resultados históricos")
    out = base / run_id
    out.mkdir(parents=True, exist_ok=False)
    rtl = GhdlBackend(ghdl=ghdl, timeout=ec.timeout, build_dir=root / "build/stage4_cache" / run_id)
    _, compilation = rtl.compile()
    current_signatures = {b: implementation_signature(b, ec, rtl) for b in BACKENDS}
    old_signatures = {b: original_metrics.implementation_signature(b, ec, rtl) for b in BACKENDS}
    write_json(out / "config.json", config)
    write_json(out / "cold_compilation.json", compilation)
    print(f"Etapa 4 em {out}", flush=True)
    profiles = {"schema_version": 1, "profiles": [], "unavailable": []}
    training = splits["characterization"]
    for family in sorted({c["family"] for c in training}):
        result = characterize([(c["F"], c["K"]) for c in training if c["family"] == family],
                              config=ec, rtl_backend=rtl, repeats=config["profile_repeats"], warmup=1,
                              input_class=family, experiment_id=f"{run_id}/{family}")
        profiles["profiles"].extend(result["profiles"])
        profiles["unavailable"].extend(result["unavailable"])
    if profiles["unavailable"]:
        raise RuntimeError(profiles["unavailable"])
    old_profiles = deepcopy(profiles)
    for profile in old_profiles["profiles"]:
        profile["signature"] = old_signatures[profile["backend"]]
        profile["id"] = digest([profile["id"], profile["signature"]])
    write_json(out / "profiles_optimized.json", profiles)
    write_json(out / "profiles_original.json", old_profiles)

    # Temporiza a função original sem mudar as condições de seleção.
    legacy_signature_seconds = 0.

    def timed_signature(*args):
        nonlocal legacy_signature_seconds
        start = time.perf_counter()
        try:
            return original_metrics.implementation_signature(*args)
        finally:
            legacy_signature_seconds += time.perf_counter() - start

    original.implementation_signature = timed_signature
    start = time.perf_counter()
    optimized = ExecutionManager(profiles, config=ec, rtl_backend=rtl)
    optimized_setup = time.perf_counter() - start
    start = time.perf_counter()
    original_manager = original.ExecutionManager(old_profiles, config=ec, rtl_backend=rtl)
    original_setup = time.perf_counter() - start
    fixed = ExecutionManager(config=ec, rtl_backend=rtl)
    development = splits["development"][0]
    first = optimized.execute(development["F"], development["K"], input_class=development["family"])
    write_json(out / "cold_decision.json", first)
    rng = np.random.default_rng(config["order_seed"])
    rows = []
    trials = []
    scenarios = [s for s in historical_meta["config"]["scenarios"] if s["id"] in config["scenarios"]]
    variants = ("software_fixed", "rtl_fixed", "original", "optimized", "verified_fallback")
    print("Comparação pareada", flush=True)
    for scenario in scenarios:
        options = {k: v for k, v in scenario.items() if k != "id"}
        for repetition in range(config["repeats"]):
            for idx in rng.permutation(len(splits["evaluation"])):
                case = splits["evaluation"][int(idx)]
                trial = {}
                for value in rng.permutation(variants):
                    variant = str(value)
                    legacy_signature_seconds = 0.
                    arguments = (case["F"], case["K"])
                    if variant == "original":
                        decision = original_manager.execute(*arguments, input_class=case["family"],
                                                            requirements=original.Requirements(**options))
                        decision["metrics"]["signature_seconds"] = legacy_signature_seconds
                    elif variant == "rtl_fixed" or variant == "software_fixed":
                        mode = "software" if variant == "software_fixed" else "rtl_simulated"
                        decision = fixed.execute(*arguments, mode=mode, requirements=Requirements(**options))
                    else:
                        decision = optimized.execute(*arguments, input_class=case["family"], requirements=Requirements(
                            **options, verify_unprofiled_software=variant == "verified_fallback"))
                    trial[variant] = decision
                    trials.append({"case_id": case["id"], "scenario": scenario["id"], "repetition": repetition,
                                   "variant": variant, "result": decision})
                for variant, decision in trial.items():
                    absolute = decision["attempts"][-1]["metrics"].get("max_abs_error") if decision["attempts"] else None
                    oracle_viable = trial["software_fixed"]["valid"] or trial["rtl_fixed"]["valid"]
                    bound = scenario["max_seconds"]
                    rows.append({"case_id": case["id"], "family": case["family"], "scenario": scenario["id"],
                                 "repetition": repetition, "variant": variant, "status": decision["status"],
                                 "selected": decision["selected_backend"], "backend": decision["backend"],
                                 "valid": decision["valid"], "ex_post_viable": oracle_viable,
                                 "false_refusal": decision["status"] == "no_feasible_configuration" and oracle_viable,
                                 "false_acceptance": decision["selected_backend"] is not None and not decision["metrics"]["initial_selection_success"],
                                 "error_violation": absolute is not None and absolute > scenario["max_error"],
                                 "time_overrun": bound is not None and decision["metrics"]["total_seconds"] > bound,
                                 "observed_max_abs_error": absolute,
                                 "reasons": _reason_labels(decision), "E_hash": digest(decision["E"]) if decision["valid"] else None,
                                 "overhead_vs_software_seconds": decision["metrics"]["total_seconds"] - trial["software_fixed"]["metrics"]["total_seconds"],
                                 **decision["metrics"]})
    write_csv(out / "paired.csv", rows)
    # Requisitos vêm de duas classes em módulos distintos, ambas serializáveis.
    write_json(out / "paired_raw.json", trials)
    print("Geometria sintética ampliada", flush=True)
    dataset = list(cases(config["geometry_seed"]))
    geometry = list(evaluate(dataset, rtl, config["shape_threshold"]))
    write_json(out / "geometry_dataset.json", dataset)
    write_json(out / "geometry_raw.json", geometry)
    write_csv(out / "geometry.csv", [{k: v for k, v in row.items()
                                     if k not in ("E_rtl_raw", "E_reference", "E_theory", "model_raw")}
                                    for row in geometry])
    from experiments.stage4_report import report
    summary = report(out, rows, geometry, config)
    after = tree_hash(bases)
    if after != hashes_before:
        raise RuntimeError("Resultados históricos foram modificados")
    hashes = {str(p.relative_to(root)): file_hash(p) for p in (
        Path(__file__), Path(__file__).with_name("stage4_geometry.py"), Path(__file__).with_name("stage4_report.py"),
        root / "hybrid_sfm/manager.py", root / "hybrid_sfm/metrics.py")}
    metadata = {"run_id": run_id, "python": sys.version, "numpy": np.__version__,
                "platform": platform.platform(), "processor": platform.processor(),
                "cpu_model": next((line.split(":", 1)[1].strip() for line in
                                   Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("model name")), None)
                if Path("/proc/cpuinfo").exists() else platform.processor(),
                "ghdl": current_signatures["rtl_simulated"]["ghdl"], "signatures": current_signatures,
                "profile_validation_and_manager_setup_seconds": {"original": original_setup, "optimized": optimized_setup},
                "original_signatures": old_signatures, "config_sha256": digest(config), "source_sha256": hashes,
                "historical_artifact_sha256": hashes_before, "history_unchanged": True,
                "historical_dataset_sha256": historical_meta["dataset_sha256"],
                "geometry_dataset_sha256": digest(dataset),
                "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
                "summary": summary}
    write_json(out / "metadata.json", metadata)
    print(out, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "experiments/stage4_config.json")
    parser.add_argument("--ghdl")
    arguments = parser.parse_args()
    run(read_json(arguments.config), arguments.ghdl)
