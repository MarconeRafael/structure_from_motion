"""Demonstração operacional; falhas injetadas não são falhas naturais do backend."""

import argparse
import json
from pathlib import Path
from unittest.mock import patch

from hybrid_sfm.backends import ExecutionConfig
from hybrid_sfm.ghdl_backend import PROJECT_ROOT, _run_process
from hybrid_sfm.manager import ExecutionManager, Requirements
from hybrid_sfm.metrics import write_json
from hybrid_sfm.profiles import characterize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "build/manager_demo")
    parser.add_argument("--ghdl")
    parser.add_argument("--inject-timeout", action="store_true")
    args = parser.parse_args()
    data = json.loads((PROJECT_ROOT / "examples/essential_identity.json").read_text(encoding="utf-8"))
    F, K = data["F"], data["K"]
    config = ExecutionConfig(ghdl=args.ghdl)
    profiles = characterize([(F, K)], config=config, repeats=3, warmup=1,
                             experiment_id="stage2-operational-demo")
    if profiles["unavailable"]:
        raise RuntimeError(f"A demonstração requer ambos os backends: {profiles['unavailable']}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "profiles.json", profiles)
    manager = ExecutionManager(profiles, config=config)
    results = {mode: manager.execute(F, K, mode=mode) for mode in ("software", "rtl_simulated", "auto")}
    results["prefer_rtl"] = manager.execute(F, K, requirements=Requirements(preference="prefer_rtl"))
    results["impossible_time"] = manager.execute(F, K, requirements=Requirements(max_seconds=0))
    if args.inject_timeout:
        def forced_timeout(command, cwd, timeout, stage):
            return _run_process(command, cwd, 0.000001 if stage == "simulation" else timeout, stage)
        # A assinatura e os perfis ficam intactos. Só o watchdog da tentativa
        # simulada é reduzido, para exercitar a recuperação de uma falha real.
        with patch("hybrid_sfm.ghdl_backend._run_process", side_effect=forced_timeout):
            results["injected_timeout"] = manager.execute(F, K, requirements=Requirements(preference="prefer_rtl"))
    write_json(args.output_dir / "decisions.json", {
        "purpose": "operational_demo_not_publication_benchmark",
        "fault_injection": {"enabled": args.inject_timeout, "simulation_timeout_seconds": 0.000001},
        "results": results})
    for name, result in results.items():
        print(f"{name}: {result['status']}, selected={result['selected_backend']}, used={result['backend']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
