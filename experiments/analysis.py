"""Métricas derivadas, tabelas e figuras exclusivamente a partir das observações."""

from collections import defaultdict
import csv
import json
from pathlib import Path

import numpy as np

from hybrid_sfm.metrics import json_value


def numerical_metrics(value, reference, epsilon, geometric=False, ground_truth=None):
    value, reference = np.asarray(value), np.asarray(reference)
    absolute = float(np.max(np.abs(value - reference)))
    denominator = float(np.max(np.abs(reference)))
    near_zero = denominator <= epsilon
    relative = absolute / denominator if not near_zero else (0.0 if absolute <= epsilon else None)
    result = {"absolute_error": absolute, "relative_error": relative,
              "relative_reference_near_zero": near_zero,
              "relative_definition": "absolute/max_abs_reference" if not near_zero else "zero_within_threshold" if relative == 0 else "undefined_near_zero",
              "scale_invariant_error": None, "scale_metric_status": "not_geometric"}
    if geometric:
        first_norm, second_norm = np.linalg.norm(value), np.linalg.norm(reference)
        if first_norm <= epsilon or second_norm <= epsilon:
            result["scale_metric_status"] = "undefined_zero_matrix"
        else:
            first, second = value / first_norm, reference / second_norm
            result.update(scale_invariant_error=float(min(np.linalg.norm(first - second), np.linalg.norm(first + second))),
                          scale_metric_status="ok")
    result["float64_ground_truth_max_error"] = (
        float(np.max(np.abs(reference - np.asarray(ground_truth)))) if ground_truth is not None else None)
    return result


def quantiles(values, prefix="seconds"):
    values = list(values)
    return {f"{prefix}_{name}": float(np.percentile(values, percentile, method="linear")) if values else None
            for name, percentile in (("median", 50), ("p90", 90), ("p95", 95))}


def write_csv(path, rows):
    rows = list(rows)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, default=json_value, allow_nan=False) if isinstance(v, (dict, list, tuple)) else v
                             for k, v in row.items()})


def policy_comparisons(rows):
    grouped = defaultdict(dict)
    for row in rows:
        grouped[(row["replication"], row["case_id"], row["scenario"], row["repetition"])][row["policy"]] = row
    comparisons = []
    for key, group in grouped.items():
        auto = group["auto"]
        feasible = [group[name] for name in ("software", "rtl_simulated") if group[name]["valid"]]
        best = min(feasible, key=lambda row: row["total_seconds"]) if feasible else None
        initial = group.get(auto["selected_backend"])
        comparisons.append({"replication": key[0], "case_id": key[1], "scenario": key[2], "repetition": key[3],
                            "selected_backend": auto["selected_backend"], "auto_valid": auto["valid"],
                            "oracle_backend": best["policy"] if best else None,
                            "oracle_seconds": best["total_seconds"] if best else None,
                            "initial_selection_feasible_ex_post": bool(initial and initial["valid"]),
                            "missed_observed_feasible": bool(auto["selected_backend"] is None and best),
                            "matched_fixed_overhead_seconds": auto["total_seconds"] - initial["total_seconds"] if initial else None,
                            "oracle_excess_seconds": auto["total_seconds"] - best["total_seconds"] if best and auto["valid"] else None})
    return comparisons


def summarize(numeric, timing, policies, faults, comparisons):
    tables = {}
    numeric_summary = []
    for category in sorted({r["category"] for r in numeric}):
        group = [r for r in numeric if r["category"] == category]
        exported = [r for r in group if r["bit_exact"] is not None]
        valid = [r for r in group if r["valid"]]
        numeric_summary.append({"category": category, "samples": len(group), "exported": len(exported),
                                "bit_exact": sum(r["bit_exact"] is True for r in group),
                                "valid_no_overflow": len(valid), "overflow": sum(r["overflow"] for r in group),
                                "max_absolute_error_all": max((r["absolute_error"] for r in exported), default=None),
                                "max_absolute_error_valid": max((r["absolute_error"] for r in valid), default=None),
                                "relative_undefined": sum(r["relative_error"] is None for r in group),
                                "valid_rate": len(valid) / len(group)})
    tables["numeric"] = numeric_summary
    valid_pairs = {(r["replication"], r["case_id"], r["repetition"]) for r in timing
                   if r["backend"] == "rtl_simulated" and r["valid"]}
    time_summary = []
    for backend in ("software", "rtl_simulated"):
        for population in ("all_valid", "paired_valid"):
            group = [r for r in timing if r["backend"] == backend and r["valid"] and
                     (population == "all_valid" or (r["replication"], r["case_id"], r["repetition"]) in valid_pairs)]
            time_summary.append({"backend": backend, "population": population, "samples": len(group),
                                 **quantiles(r["observed_seconds"] for r in group)})
    tables["timing"] = time_summary
    policy_summary = []
    for scenario in sorted({r["scenario"] for r in policies}):
        for policy in ("software", "rtl_simulated", "auto"):
            group = [r for r in policies if r["scenario"] == scenario and r["policy"] == policy]
            policy_summary.append({"scenario": scenario, "policy": policy, "requests": len(group),
                                   "valid": sum(r["valid"] for r in group),
                                   "valid_rate": sum(r["valid"] for r in group) / len(group),
                                   "no_feasible": sum(r["status"] == "no_feasible_configuration" for r in group),
                                   "fallbacks": sum(r["fallback_count"] for r in group),
                                   "failed_attempts": sum(r["failure_count"] for r in group),
                                   "error_violations": sum(r["error_violation"] for r in group),
                                   "time_overruns": sum(r["time_overrun"] for r in group),
                                   **quantiles(r["total_seconds"] for r in group),
                                   **quantiles((r["decision_seconds"] for r in group), "decision_seconds")})
    tables["policies"] = policy_summary
    tables["faults"] = [{"fault": r["fault"], "fallback_policy": r["fallback_policy"],
                         "status": r["status"], "selected_backend": r["selected_backend"], "backend": r["backend"],
                         "fallback_count": r["fallback_count"], "initial_success": r["initial_success"],
                         "detection_ok": r["detection_ok"], "total_seconds": r["total_seconds"]} for r in faults]
    tables["comparisons"] = [{"scenario": scenario, "requests": len(group),
                              "initial_feasible_ex_post": sum(r["initial_selection_feasible_ex_post"] for r in group),
                              "missed_observed_feasible": sum(r["missed_observed_feasible"] for r in group),
                              **quantiles((r["matched_fixed_overhead_seconds"] for r in group
                                           if r["matched_fixed_overhead_seconds"] is not None), "overhead_seconds"),
                              **quantiles((r["oracle_excess_seconds"] for r in group
                                           if r["oracle_excess_seconds"] is not None), "oracle_excess_seconds")}
                             for scenario in sorted({r["scenario"] for r in comparisons})
                             for group in [[r for r in comparisons if r["scenario"] == scenario]]]
    return tables


def figures(output, numeric, timing, policies):
    import os
    os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / "build/matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    output = Path(output)
    output.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    categories = sorted({r["category"] for r in numeric})
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    for index, category in enumerate(categories):
        group = [r for r in numeric if r["category"] == category and r["absolute_error"] is not None]
        for valid, marker, label in ((True, "o", "sem overflow"), (False, "x", "inválido/overflow")):
            errors = [r["absolute_error"] for r in group if r["valid"] == valid]
            axes[0].scatter([index] * len(errors), errors, marker=marker, alpha=.6,
                            label=label if index == 0 else None)
        relative = [r["relative_error"] for r in group if r["relative_error"] is not None]
        axes[1].scatter([index] * len(relative), relative, alpha=.6)
    for ax, title in zip(axes, ("Erro absoluto máximo", "Erro relativo máximo")):
        ax.set_xticks(range(len(categories)), categories, rotation=15, ha="right")
        ax.set_yscale("symlog", linthresh=1e-8)
        ax.set_ylim(bottom=0)
        ax.set_title(title)
        ax.grid(axis="y", alpha=.2)
    axes[0].legend(fontsize=8)
    fig.suptitle("A — RTL simulado: medidas e erros derivados (inclui casos inválidos)")
    fig.savefig(output / "numeric_errors.png", dpi=180)
    fig.savefig(output / "numeric_errors.pdf")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
    pairs = {(r["replication"], r["case_id"], r["repetition"]) for r in timing
             if r["backend"] == "rtl_simulated" and r["valid"]}
    for backend in ("software", "rtl_simulated"):
        values = sorted(r["observed_seconds"] for r in timing if r["backend"] == backend and r["valid"]
                        and (r["replication"], r["case_id"], r["repetition"]) in pairs)
        if values:
            ax.step(values, np.arange(1, len(values) + 1) / len(values), where="post", label=f"{backend} (n={len(values)})")
    ax.set(xscale="log", xlabel="Tempo de parede por tentativa (s)", ylabel="Fração acumulada",
           title="B — Latência medida: entradas pareadas válidas, cache aquecido")
    ax.legend()
    ax.grid(alpha=.2)
    fig.savefig(output / "latency_ecdf.png", dpi=180)
    fig.savefig(output / "latency_ecdf.pdf")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4), layout="constrained")
    scenarios = sorted({r["scenario"] for r in policies})
    for index, policy in enumerate(("software", "rtl_simulated", "auto")):
        rates = [np.mean([r["valid"] for r in policies if r["policy"] == policy and r["scenario"] == scenario]) for scenario in scenarios]
        ax.bar(np.arange(len(scenarios)) + (index - 1) * .25, rates, width=.25, label=policy)
    ax.set_xticks(range(len(scenarios)), scenarios, rotation=15, ha="right")
    ax.set(ylim=(0, 1.08), ylabel="Fração de requisições válidas",
           title="C — Sucesso observado por política (derivado dos registros medidos)")
    ax.legend(ncol=3, fontsize=8)
    fig.savefig(output / "policy_success.png", dpi=180)
    fig.savefig(output / "policy_success.pdf")
    plt.close(fig)
