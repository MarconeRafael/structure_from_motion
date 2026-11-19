"""Kernel essencial, políticas fixas, gerenciador e caracterização de perfis."""

import argparse
import json
from pathlib import Path
import sys

from .backends import ExecutionConfig
from .ghdl_backend import BackendError, GhdlBackend
from .manager import ExecutionManager, Requirements
from .metrics import json_value
from .profiles import characterize, load_profiles
from .sfm import estimate_essential


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help='JSON com F/K, correspondências ou casos de caracterização')
    parser.add_argument("--backend", choices=("software", "rtl_simulated", "auto"),
                        help="Sem esta opção, preserva a CLI da Etapa 1")
    parser.add_argument("--profiles", type=Path, help="Perfis medidos para o modo auto")
    parser.add_argument("--max-error", type=float, default=0.01, help="Máximo erro absoluto por componente de E")
    parser.add_argument("--max-seconds", type=float, help="Orçamento de parede da requisição ao gerenciador")
    parser.add_argument("--prefer", choices=("min_time", "prefer_rtl"), default="min_time")
    parser.add_argument("--fallback", choices=("none", "software", "other"), default="software")
    parser.add_argument("--verify-unprofiled-software", action="store_true",
                        help="Permite software com validação posterior se não houver perfil compatível")
    parser.add_argument("--input-class", default="controlled")
    parser.add_argument("--characterize", action="store_true", help="Mede os backends e produz perfis JSON")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--experiment-id")
    parser.add_argument("--output", type=Path, help="Arquivo JSON; padrão: stdout")
    parser.add_argument("--ghdl", help="Executável GHDL; padrão: variável GHDL ou PATH")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    try:
        input_path = args.input or Path(__file__).resolve().parents[1] / "examples/essential_identity.json"
        data = json.loads(input_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("A entrada JSON deve ser um objeto")
        config = ExecutionConfig(ghdl=args.ghdl, timeout=args.timeout)
        if args.characterize:
            cases = data.get("cases", [data])
            selected_backends = (args.backend,) if args.backend in ("software", "rtl_simulated") else ("software", "rtl_simulated")
            result = characterize([(c["F"], c["K"]) for c in cases], config=config,
                                  repeats=args.repeats, warmup=args.warmup, input_class=args.input_class,
                                  experiment_id=args.experiment_id, backends=selected_backends)
            exit_code = 0 if result["profiles"] and not result["unavailable"] else 1
        elif args.backend:
            profiles = load_profiles(args.profiles) if args.profiles and args.backend == "auto" else None
            manager = ExecutionManager(profiles, config=config)
            requirements = Requirements(max_error=args.max_error, max_seconds=args.max_seconds,
                                        preference=args.prefer, fallback=args.fallback,
                                        verify_unprofiled_software=args.verify_unprofiled_software)
            result = estimate_essential(data["K"], F=data.get("F"), points1=data.get("points1"),
                                        points2=data.get("points2"), manager=manager, mode=args.backend,
                                        requirements=requirements, input_class=args.input_class)
            exit_code = 0 if result["valid"] else 2
        else:
            result = GhdlBackend(ghdl=args.ghdl, timeout=args.timeout).run(data["F"], data["K"])
            exit_code = 0 if result["valid"] else 2
    except BackendError as exc:
        result = {"status": "error", "stage": exc.stage, "message": str(exc), "process": exc.process}
        exit_code = 1
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        result = {"status": "error", "stage": "input", "message": str(exc)}
        exit_code = 1
    output = json.dumps(result, default=json_value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    if args.output:
        try:
            args.output.write_text(output, encoding="utf-8")
        except OSError as exc:
            sys.stderr.write(json.dumps({"status": "error", "stage": "output", "message": str(exc)}) + "\n")
            return 1
    else:
        sys.stdout.write(output)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
