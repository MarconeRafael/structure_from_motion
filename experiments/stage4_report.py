"""Tabelas e figuras da comparação pareada e da geometria adicional."""

from collections import Counter
import os

import numpy as np

from experiments.analysis import quantiles, write_csv
from hybrid_sfm.ghdl_backend import PROJECT_ROOT
from hybrid_sfm.metrics import write_json


def report(out, rows, geometry, config):
    policies = []
    changes = []
    exclusions = []
    for scenario in dict.fromkeys(r["scenario"] for r in rows):
        group = [r for r in rows if r["scenario"] == scenario]
        original = {(r["case_id"], r["repetition"]): r for r in group if r["variant"] == "original"}
        for variant in dict.fromkeys(r["variant"] for r in group):
            subset = [r for r in group if r["variant"] == variant]
            eligible = sum(r["ex_post_viable"] for r in subset)
            valid = sum(r["valid"] for r in subset)
            policies.append({"scenario": scenario, "variant": variant, "n": len(subset), "valid": valid,
                             "viable_baseline": eligible, "valid_and_viable_baseline": sum(r["valid"] and r["ex_post_viable"] for r in subset),
                             "valid_rate": valid / len(subset), "profile_backed_choices": sum(r["selected"] is not None for r in subset),
                             **{field: sum(r.get(field, 0) for r in subset) for field in (
                                 "false_refusal", "false_acceptance", "error_violation", "time_overrun", "fallback_count")},
                             **{k: v for field in ("decision_seconds", "signature_seconds", "profile_lookup_seconds",
                                                  "filter_seconds", "ranking_seconds", "total_seconds",
                                                  "initial_attempt_seconds", "fallback_seconds", "overhead_vs_software_seconds")
                                for k, v in quantiles((r[field] for r in subset if field in r), field).items()}})
            reason_counts = Counter(reason for r in subset for reason in r["reasons"])
            exclusions.extend({"scenario": scenario, "variant": variant, "reason": reason, "count": number}
                              for reason, number in sorted(reason_counts.items()))
            if variant in ("optimized", "verified_fallback"):
                pairs = [(original[(r["case_id"], r["repetition"])], r) for r in subset]
                changes.append({"scenario": scenario, "variant": variant, "n": len(pairs),
                                "different_initial_choice": sum(a["selected"] != b["selected"] for a, b in pairs),
                                "different_status": sum(a["status"] != b["status"] for a, b in pairs),
                                "different_E_on_joint_success": sum(a["valid"] and b["valid"] and a["E_hash"] != b["E_hash"]
                                                                    for a, b in pairs),
                                **quantiles((a["decision_seconds"] - b["decision_seconds"] for a, b in pairs),
                                            "paired_decision_saving_seconds")})
    scales = sorted({r["scale"] for r in geometry})
    geometric = []
    for scale in scales:
        group = [row for row in geometry if row["scale"] == scale]
        valid = [r for r in group if r["valid_no_overflow"]]
        geometric.append({"scale": scale, "n": len(group), "bit_exact": sum(r["bit_exact"] for r in group),
                          "overflow": len(group) - len(valid),
                          "distorted_without_overflow": sum(r["distorted_without_overflow"] for r in group),
                          "undefined_shape_without_overflow": sum(r["rtl_shape_vs_float64"] is None for r in valid),
                          "lost_entries": sum(r["entries_lost_to_quantization"] for r in group),
                          **quantiles((r["rtl_shape_vs_float64"] for r in valid if r["rtl_shape_vs_float64"] is not None),
                                      "valid_shape_error")})
    summary = {"policies": policies, "candidate_exclusions": exclusions, "paired_changes": changes,
               "geometry_by_scale": geometric, "geometry_shape_threshold": config["shape_threshold"]}
    for name in ("policies", "candidate_exclusions", "paired_changes", "geometry_by_scale"):
        write_csv(out / f"table_{name}.csv", summary[name])
    write_json(out / "summary.json", summary)

    os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / "build/matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), layout="constrained")
    for variant, label in (("software_fixed", "Software fixo"), ("original", "Original"),
                           ("optimized", "Otimizado"), ("verified_fallback", "Software verificado")):
        values = sorted(r["decision_seconds"] * 1000 for r in rows if r["scenario"] == "balanced" and r["variant"] == variant)
        if values:
            axes[0].step(values, np.arange(1, len(values) + 1) / len(values), where="post", label=label)
    axes[0].set(xscale="log", xlabel="Tempo de decisão (ms)", ylabel="Fração acumulada", title="Decisões pareadas medidas")
    axes[0].legend(fontsize=8)
    selected = [r for r in policies if r["scenario"] == "balanced" and r["variant"] != "rtl_fixed"]
    labels = {"software_fixed": "Software fixo", "original": "Original", "optimized": "Otimizado",
              "verified_fallback": "Software verificado"}
    axes[1].barh([labels[r["variant"]] for r in selected], [r["valid_rate"] for r in selected], color="#236786")
    axes[1].set(xlim=(0, 1.05), xlabel="Fração válida", title="Cobertura observada no cenário balanceado")
    for ax in axes:
        ax.grid(axis="x", alpha=.2)
    for ext in ("png", "pdf"):
        fig.savefig(out / f"manager_comparison.{ext}", dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 3.8), layout="constrained")
    ax.bar(range(len(scales)), [r["overflow"] for r in geometric], label="Overflow", color="#ac4629")
    ax.bar(range(len(scales)), [r["distorted_without_overflow"] for r in geometric],
           bottom=[r["overflow"] for r in geometric], label="Distorção sem overflow", color="#d9a23a")
    ax.set(xticks=range(len(scales)), xticklabels=[f"{s:g}" for s in scales], xlabel="Multiplicador de F",
           ylabel="Casos (27 por escala)", title="Geometria sintética. Eventos derivados da simulação")
    ax.legend()
    for ext in ("png", "pdf"):
        fig.savefig(out / f"geometry_scale.{ext}", dpi=180)
    plt.close(fig)
    return summary
