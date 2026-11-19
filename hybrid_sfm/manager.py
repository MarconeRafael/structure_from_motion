"""Seleção determinística por restrições rígidas e perfis observados."""

from dataclasses import dataclass
import math
import time

from .backends import BACKENDS, ExecutionConfig, run_backend
from .fixed_point import quantize
from .ghdl_backend import BackendError, GhdlBackend
from .metrics import ERROR_METRIC, implementation_signature, signature_fingerprint
from .profiles import covers, validate_profiles
from .reference import matrix3


@dataclass(frozen=True)
class Requirements:
    max_error: float = 0.01
    max_seconds: float | None = None
    preference: str = "min_time"
    fallback: str = "software"
    verify_unprofiled_software: bool = False

    def __post_init__(self):
        if not math.isfinite(self.max_error) or self.max_error < 0:
            raise ValueError("max_error deve ser finito e não negativo")
        if self.max_seconds is not None and (not math.isfinite(self.max_seconds) or self.max_seconds < 0):
            raise ValueError("max_seconds deve ser finito e não negativo")
        if self.preference not in ("min_time", "prefer_rtl"):
            raise ValueError("preference deve ser min_time ou prefer_rtl")
        if self.fallback not in ("none", "software", "other"):
            raise ValueError("fallback deve ser none, software ou other")
        if type(self.verify_unprofiled_software) is not bool:
            raise ValueError("verify_unprofiled_software deve ser booleano")


class ExecutionManager:
    def __init__(self, profiles=None, *, config=None, rtl_backend=None, reuse_signatures=True):
        self.profiles = validate_profiles(profiles if profiles is not None else {"schema_version": 1, "profiles": []})
        self.config = config or ExecutionConfig()
        self.rtl_backend = rtl_backend
        self.reuse_signatures = reuse_signatures
        self._signatures = {}

    def _signature(self, backend):
        if not self.reuse_signatures or (
                backend == "rtl_simulated" and self.rtl_backend is not None
                and not isinstance(self.rtl_backend, GhdlBackend)):
            return implementation_signature(backend, self.config, self.rtl_backend), False
        try:
            fingerprint = signature_fingerprint(backend, self.config, self.rtl_backend)
            cached = self._signatures.get(backend)
            if cached is not None and cached[0] == fingerprint:
                return cached[1], True
            signature = implementation_signature(backend, self.config, self.rtl_backend)
            if signature_fingerprint(backend, self.config, self.rtl_backend) != fingerprint:
                raise BackendError("tool", "Identidade da implementação mudou durante a verificação")
            self._signatures[backend] = (fingerprint, signature)
            return signature, False
        except (BackendError, OSError, ValueError):
            self._signatures.pop(backend, None)
            raise

    def _candidates(self, F, K, requirements, input_class, breakdown):
        candidates = []
        for backend in BACKENDS:
            candidate = {"backend": backend, "eligible": False, "reasons": [], "profile_ids": []}
            candidates.append(candidate)
            if backend == "rtl_simulated":
                start = time.perf_counter()
                try:
                    quantize(F)
                    quantize(K)
                except ValueError as exc:
                    candidate["reasons"].append({"code": "unsupported_input", "message": str(exc)})
                    continue
                finally:
                    breakdown["filter_seconds"] += time.perf_counter() - start
            start = time.perf_counter()
            try:
                signature, hit = self._signature(backend)
                breakdown["signature_cache_hits"] += hit
            except (BackendError, ValueError, OSError) as exc:
                candidate["reasons"].append({"code": "unavailable_or_unsupported", "message": str(exc)})
                continue
            finally:
                breakdown["signature_seconds"] += time.perf_counter() - start
            start = time.perf_counter()
            matching = [p for p in self.profiles["profiles"]
                        if p["backend"] == backend and p["input_class"] == input_class]
            signed = [p for p in matching if p["signature"] == signature]
            compatible = [p for p in signed if covers(p, F, K, input_class)]
            breakdown["profile_lookup_seconds"] += time.perf_counter() - start
            if not compatible:
                detail = "out_of_domain" if signed else "signature_mismatch" if matching else "no_profile_for_class"
                candidate["reasons"].append({"code": "no_compatible_profile", "detail": detail})
                continue
            start = time.perf_counter()
            candidate["profile_ids"] = sorted(p["id"] for p in compatible)
            if any(p["summary"]["failure_rate"] > 0
                   or any(not s["valid"] for s in p.get("warmup_observations", [])) for p in compatible):
                candidate["reasons"].append({"code": "observed_failures"})
                breakdown["filter_seconds"] += time.perf_counter() - start
                continue
            error = max(p["summary"]["max_abs_error"] for p in compatible)
            seconds = max(p["summary"]["max_seconds"] for p in compatible)
            candidate.update(predicted_max_abs_error=error, predicted_seconds=seconds)
            if error > requirements.max_error:
                candidate["reasons"].append({"code": "predicted_error_limit"})
            candidate["eligible"] = not candidate["reasons"]
            breakdown["filter_seconds"] += time.perf_counter() - start
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
        breakdown = {"signature_seconds": 0., "profile_lookup_seconds": 0., "filter_seconds": 0.,
                     "ranking_seconds": 0., "signature_cache_hits": 0}
        if mode == "auto":
            candidates = self._candidates(F, K, requirements, input_class, breakdown)
            elapsed = time.perf_counter() - started
            for candidate in candidates:
                if (candidate["eligible"] and requirements.max_seconds is not None
                        and candidate["predicted_seconds"] + elapsed > requirements.max_seconds):
                    candidate["eligible"] = False
                    candidate["reasons"].append({"code": "predicted_time_limit"})
            breakdown["filter_seconds"] += time.perf_counter() - started - elapsed
            ranking_start = time.perf_counter()
            eligible = [c for c in candidates if c["eligible"]]
            if requirements.preference == "prefer_rtl":
                eligible.sort(key=lambda c: (c["backend"] != "rtl_simulated", c["predicted_seconds"]))
            else:
                eligible.sort(key=lambda c: (c["predicted_seconds"], BACKENDS.index(c["backend"])))
            selected = eligible[0]["backend"] if eligible else None
            decision["candidates"] = candidates
            breakdown["ranking_seconds"] = time.perf_counter() - ranking_start
        decision["selected_backend"] = selected
        decision_seconds = time.perf_counter() - started
        result = {"status": "no_feasible_configuration", "valid": False, "E": None, "backend": None,
                  "selected_backend": selected, "decision": decision, "attempts": [],
                  "fallback": {"used": False, "policy": requirements.fallback}, "metrics": {}}
        attempts = result["attempts"]
        if (mode == "auto" and selected is None and requirements.verify_unprofiled_software
                and requirements.fallback in ("software", "other")
                and any(c["backend"] == "software" and any(r["code"] == "no_compatible_profile" for r in c["reasons"])
                        for c in candidates)
                and (requirements.max_seconds is None or decision_seconds < requirements.max_seconds)):
            result["fallback"].update(used=True, from_backend=None, to_backend="software",
                                      reason={"stage": "no_compatible_profile", "prior_guarantee": False},
                                      time_before_fallback_seconds=decision_seconds)
            attempt = run_backend("software", F, K, self.config, rtl_backend=self.rtl_backend)
            attempts.append(self._check_attempt(attempt, requirements, time.perf_counter() - started))
            result.update(status="fallback_ok" if attempt["valid"] else attempt["status"],
                          valid=attempt["valid"], E=attempt["E"], backend="software")
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
        result["metrics"] = {**breakdown, "decision_seconds": decision_seconds, "total_seconds": total,
                             "initial_attempt_seconds": attempts[0]["metrics"]["observed_seconds"] if attempts and selected else 0.0,
                             "fallback_seconds": attempts[-1]["metrics"]["observed_seconds"] if result["fallback"]["used"] else 0.0,
                             "failure_count": sum(not a["valid"] for a in attempts),
                             "fallback_count": int(result["fallback"]["used"]),
                             "initial_selection_success": bool(selected and attempts[0]["valid"])}
        return result
