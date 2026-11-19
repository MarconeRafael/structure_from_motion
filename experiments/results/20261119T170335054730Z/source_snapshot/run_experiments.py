"""Ponto único de execução dos experimentos; sem GUI ou serviços remotos."""

import argparse
import json
from pathlib import Path

from experiments.runner import run
from hybrid_sfm.ghdl_backend import PROJECT_ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "experiments/config.json")
    parser.add_argument("--ghdl", help="Executável GHDL; padrão: GHDL/PATH")
    parser.add_argument("--output-dir", type=Path, help="Diretório-base para uma nova execução")
    args = parser.parse_args()
    run(json.loads(args.config.read_text(encoding="utf-8")), ghdl=args.ghdl, output_override=args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
