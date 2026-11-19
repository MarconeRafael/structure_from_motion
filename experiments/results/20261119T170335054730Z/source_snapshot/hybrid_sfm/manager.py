"""Seleção determinística por restrições rígidas e perfis observados."""

from dataclasses import dataclass
import math
import time

from .backends import BACKENDS, ExecutionConfig, run_backend
from .fixed_point import quantize
from .ghdl_backend import BackendError
from .metrics import ERROR_METRIC, implementation_signature
from .profiles import covers, validate_profiles
from .reference import matrix3


@dataclass(frozen=True)
class Requirements:
    max_error: float = 0.01
    max_seconds: float | None = None
    preference: str = "min_time"
    fallback: str = "software"

    def __post_init__(self):
        if not math.isfinite(self.max_error) or self.max_error < 0:
            raise ValueError("max_error deve ser finito e não negativo")
        if self.max_seconds is not None and (not math.isfinite(self.max_seconds) or self.max_seconds < 0):
            raise ValueError("max_seconds deve ser finito e não negativo")
        if self.preference not in ("min_time", "prefer_rtl"):
            raise ValueError("preference deve ser min_time ou prefer_rtl")
        if self.fallback not in ("none", "software", "other"):
            raise ValueError("fallback deve ser none, software ou other")


class ExecutionManager:
    def __init__(self, profiles=None, *, config=None, rtl_backend=None):
        self.profiles = validate_profiles(profiles if profiles is not None else {"schema_version": 1, "profiles": []})
        self.config = config or ExecutionConfig()
        self.rtl_backend = rtl_backend

    def _candidates(self, F, K, requirements, input_class):
        candidates = []
        for backend in BACKENDS:
            candidate = {"backend": backend, "eligible": False, "reasons": [], "profile_ids": []}
            candidates.append(candidate)
            try:
                if backend == "rtl_simulated":
                    quantize(F)
                    quantize(K)
                signature = implementation_signature(backend, self.config, self.rtl_backend)
            except (BackendError, ValueError, OSError) as exc:
                candidate["reasons"].append({"code": "unavailable_or_unsupported", "message": str(exc)})
                continue
            compatible = [p for p in self.profiles["profiles"]
                          if p["backend"] == backend and p["signature"] == signature
                          and covers(p, F, K, input_class)]
            if not compatible:
                candidate["reasons"].append({"code": "no_compatible_profile"})
                continue
            candidate["profile_ids"] = sorted(p["id"] for p in compatible)
            if any(p["summary"]["failure_rate"] > 0
                   or any(not s["valid"] for s in p.get("warmup_observations", [])) for p in compatible):
                candidate["reasons"].append({"code": "observed_failures"})
                continue
            error = max(p["summary"]["max_abs_error"] for p in compatible)
            seconds = max(p["summary"]["max_seconds"] for p in compatible)
            candidate.update(predicted_max_abs_error=error, predicted_seconds=seconds)
            if error > requirements.max_error:
                candidate["reasons"].append({"code": "predicted_error_limit"})
            candidate["eligible"] = not candidate["reasons"]
        return candidates

    @staticmethod
    def _check_attempt(attempt, requirements, elapsed):
        violations = []
        if attempt["valid"]:
            if attempt["metrics"]["max_abs_error"] > requirements.max_error:
                violations.append("max_error")
            if requirements.max_seconds is not None and (
                    elapsed > requirements.max_seconds
                    or attempt["metrics"]["observed_seconds"] > requirements.max_seconds):
                violations.append("max_seconds")
            if violations:
                attempt.update(status="constraint_violation", valid=False, E=None,
                               diagnostic={"stage": "post_validation", "violations": violations})
        return attempt

    def execute(self, F, K, *, mode="auto", requirements=None, input_class="controlled"):
        started = time.perf_counter()
        if mode not in (*BACKENDS, "auto"):
            raise ValueError("mode deve ser software, rtl_simulated ou auto")
        if not isinstance(input_class, str) or not input_class:
            raise ValueError("input_class deve ser uma identificação não vazia")
        requirements = requirements or Requirements()
        F, K = matrix3(F).copy(), matrix3(K).copy()
        decision = {"mode": mode, "preference": requirements.preference, "input_class": input_class,
                    "error_metric": ERROR_METRIC, "requirements": requirements,
                    "basis": "prior_observations" if mode == "auto" else "fixed_policy",
                    "candidates": [], "selected_backend": None}
        candidates = []
        selected = mode
        if mode == "auto":
            candidates = self._candidates(F, K, requirements, input_class)
            elapsed = time.perf_counter() - started
            for candidate in candidates:
                if (candidate["eligible"] and requirements.max_seconds is not None
                        and candidate["predicted_seconds"] + elapsed > requirements.max_seconds):
                    candidate["eligible"] = False
                    candidate["reasons"].append({"code": "predicted_time_limit"})
            eligible = [c for c in candidates if c["eligible"]]
            if requirements.preference == "prefer_rtl":
                eligible.sort(key=lambda c: (c["backend"] != "rtl_simulated", c["predicted_seconds"]))
            else:
                eligible.sort(key=lambda c: (c["predicted_seconds"], BACKENDS.index(c["backend"])))
            selected = eligible[0]["backend"] if eligible else None
            decision["candidates"] = candidates
        decision["selected_backend"] = selected
        decision_seconds = time.perf_counter() - started
        result = {"status": "no_feasible_configuration", "valid": False, "E": None, "backend": None,
                  "selected_backend": selected, "decision": decision, "attempts": [],
                  "fallback": {"used": False, "policy": requirements.fallback}, "metrics": {}}
        attempts = result["attempts"]
        if selected is not None:
            initial = run_backend(selected, F, K, self.config, rtl_backend=self.rtl_backend)
            attempts.append(self._check_attempt(initial, requirements, time.perf_counter() - started))
            if not initial["valid"] and mode == "auto" and requirements.fallback != "none":
                target = ("software" if requirements.fallback == "software"
                          else next(b for b in BACKENDS if b != selected))
                elapsed = time.perf_counter() - started
                fallback_candidate = next((c for c in candidates if c["backend"] == target and c["eligible"]
                                           and target != selected), None)
                permitted = fallback_candidate is not None and (
                    requirements.max_seconds is None
                    or elapsed + fallback_candidate["predicted_seconds"] <= requirements.max_seconds)
                result["fallback"].update(reason=initial["diagnostic"], from_backend=selected,
                                           to_backend=target, time_before_fallback_seconds=elapsed)
                if permitted:
                    result["fallback"]["used"] = True
                    fallback = run_backend(target, F, K, self.config, rtl_backend=self.rtl_backend)
                    attempts.append(self._check_attempt(fallback, requirements, time.perf_counter() - started))
                else:
                    result["fallback"]["not_executed_reason"] = "no_feasible_fallback"
            final = attempts[-1]
            result.update(status=("fallback_ok" if len(attempts) == 2 else "ok") if final["valid"] else final["status"],
                          valid=final["valid"], E=final["E"], backend=final["backend"])
        # A verificação final inclui decisão e eventual tentativa anterior no orçamento.
        total = time.perf_counter() - started
        if result["valid"] and requirements.max_seconds is not None and total > requirements.max_seconds:
            self._check_attempt(attempts[-1], requirements, total)
            result.update(status="constraint_violation", valid=False, E=None)
        result["metrics"] = {"decision_seconds": decision_seconds, "total_seconds": total,
                             "initial_attempt_seconds": attempts[0]["metrics"]["observed_seconds"] if attempts else 0.0,
                             "fallback_seconds": attempts[1]["metrics"]["observed_seconds"] if len(attempts) == 2 else 0.0,
                             "failure_count": sum(not a["valid"] for a in attempts),
                             "fallback_count": int(result["fallback"]["used"]),
                             "initial_selection_success": bool(attempts and attempts[0]["valid"])}
        return result
