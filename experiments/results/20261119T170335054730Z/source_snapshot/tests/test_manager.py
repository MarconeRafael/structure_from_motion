"""Perfis sintéticos desta suíte exercitam lógica; não são dados experimentais."""

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import Mock, patch

import numpy as np

from hybrid_sfm.backends import ExecutionConfig, run_backend
from hybrid_sfm.ghdl_backend import BackendError, GhdlBackend, PROJECT_ROOT
from hybrid_sfm.manager import ExecutionManager, Requirements
from hybrid_sfm.metrics import ERROR_METRIC, TIME_SCOPE, json_value, write_json
from hybrid_sfm.profiles import characterize, load_profiles, validate_profiles
from hybrid_sfm.reference import essential_matrix
from hybrid_sfm.sfm import estimate_essential, require_valid_essential
from tests.test_essential import WorkspaceTest

I = np.eye(3)
GHDL = shutil.which(os.environ.get("GHDL", "ghdl"))


def signature(backend, *_args):
    return {"backend": backend, "implementation_sha256": "unit-synthetic"}


def synthetic_profile(backend, seconds=0.001, error=0.0, valid=True):
    return {"id": backend, "backend": backend, "signature": signature(backend),
            "experiment_id": "unit-synthetic-only", "input_class": "controlled", "conditions": {},
            "domain": {name: {"min": (-10 * np.ones((3, 3))).tolist(),
                              "max": (10 * np.ones((3, 3))).tolist()} for name in ("F", "K")},
            "error_metric": ERROR_METRIC, "time_scope": TIME_SCOPE,
            "samples": [{"valid": valid, "observed_seconds": seconds, "max_abs_error": error}],
            "summary": {"failure_rate": 0.0 if valid else 1.0, "max_seconds": seconds,
                        "max_abs_error": error if valid else None}}


def document(*profiles):
    return {"schema_version": 1, "profiles": list(profiles)}


def fake_rtl_result(F, K):
    return {"E": essential_matrix(F, K), "valid": True, "status": "ok", "bit_exact": True}


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.signature_patch = patch("hybrid_sfm.manager.implementation_signature", side_effect=signature)
        self.signature_patch.start()
        self.addCleanup(self.signature_patch.stop)
        self.rtl = Mock()
        self.rtl.run.side_effect = fake_rtl_result
        self.profiles = document(synthetic_profile("software"), synthetic_profile("rtl_simulated", .1))

    def manager(self, profiles=None):
        return ExecutionManager(profiles if profiles is not None else self.profiles, rtl_backend=self.rtl)

    def test_uniform_software_and_rtl_interface(self):
        for name in ("software", "rtl_simulated"):
            result = run_backend(name, I, I, rtl_backend=self.rtl)
            self.assertEqual(result["backend"], name)
            self.assertTrue(result["valid"])
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["metrics"]["max_abs_error"], 0)
            np.testing.assert_array_equal(result["E"], I)

    def test_fixed_modes_ignore_preferences_and_profiles(self):
        manager = self.manager(document())
        result = manager.execute(I, I, mode="software", requirements=Requirements(preference="prefer_rtl"))
        self.assertEqual(result["backend"], "software")
        self.rtl.run.assert_not_called()
        self.rtl.run.side_effect = BackendError("timeout", "injected timeout")
        result = manager.execute(I, I, mode="rtl_simulated")
        self.assertEqual(result["selected_backend"], "rtl_simulated")
        self.assertFalse(result["valid"])
        self.assertFalse(result["fallback"]["used"])
        self.assertEqual(len(result["attempts"]), 1)

    def test_fastest_selection_and_no_current_rtl_error_leakage(self):
        result = self.manager().execute(I, I)
        self.assertEqual(result["backend"], "software")
        self.assertEqual(result["decision"]["basis"], "prior_observations")
        self.rtl.run.assert_not_called()

    def test_rtl_preference_respects_error_constraint(self):
        requirements = Requirements(preference="prefer_rtl", max_error=.01)
        result = self.manager().execute(I, I, requirements=requirements)
        self.assertEqual(result["backend"], "rtl_simulated")
        profiles = document(synthetic_profile("software"), synthetic_profile("rtl_simulated", .1, .02))
        result = self.manager(profiles).execute(I, I, requirements=requirements)
        self.assertEqual(result["backend"], "software")

    def test_tie_and_reproducible_decision(self):
        profiles = document(synthetic_profile("rtl_simulated"), synthetic_profile("software"))
        results = [self.manager(profiles).execute(I, I) for _ in range(3)]
        self.assertTrue(all(r["selected_backend"] == "software" for r in results))
        self.assertEqual(results[0]["decision"], results[1]["decision"])

    def test_impossible_constraints_and_no_profiles_do_not_execute(self):
        profiles = document(synthetic_profile("software", error=.1), synthetic_profile("rtl_simulated", error=.1))
        for manager, requirements in ((self.manager(profiles), Requirements(max_error=0)),
                                      (self.manager(), Requirements(max_seconds=0)),
                                      (self.manager(document()), Requirements())):
            with self.subTest(requirements=requirements):
                result = manager.execute(I, I, requirements=requirements)
                self.assertEqual(result["status"], "no_feasible_configuration")
                self.assertEqual(result["attempts"], [])
                self.assertIsNone(result["E"])
        self.rtl.run.assert_not_called()

    def test_stale_profile_domain_and_class_rejected(self):
        profiles = deepcopy(self.profiles)
        for profile in profiles["profiles"]:
            profile["signature"]["implementation_sha256"] = "stale"
        for manager, F, input_class in ((self.manager(profiles), I, "controlled"),
                                        (self.manager(), I * 11, "controlled"),
                                        (self.manager(), I, "different")):
            result = manager.execute(F, I, input_class=input_class)
            self.assertEqual(result["status"], "no_feasible_configuration")

    def test_unavailable_rtl_uses_software(self):
        def unavailable(backend, *_args):
            if backend == "rtl_simulated":
                raise BackendError("tool", "missing ghdl")
            return signature(backend)
        with patch("hybrid_sfm.manager.implementation_signature", side_effect=unavailable):
            result = self.manager().execute(I, I, requirements=Requirements(preference="prefer_rtl"))
        self.assertEqual(result["backend"], "software")
        self.assertFalse(result["fallback"]["used"])

    def test_observed_failures_and_warmup_failures_disqualify(self):
        for warmup in (False, True):
            rtl_profile = synthetic_profile("rtl_simulated", valid=warmup)
            if warmup:
                rtl_profile["warmup_observations"] = [{"valid": False}]
            profiles = document(synthetic_profile("software"), rtl_profile)
            result = self.manager(profiles).execute(I, I, requirements=Requirements(preference="prefer_rtl"))
            self.assertEqual(result["backend"], "software")

    def test_all_compatible_profiles_are_used_conservatively(self):
        profiles = deepcopy(self.profiles)
        other = synthetic_profile("rtl_simulated", error=1)
        other["id"] = "other-rtl-profile"
        profiles["profiles"].append(other)
        result = self.manager(profiles).execute(I, I, requirements=Requirements(preference="prefer_rtl"))
        self.assertEqual(result["backend"], "software")

    def test_failure_stages_trigger_recorded_fallback(self):
        for stage in ("timeout", "simulation", "parsing", "compilation", "numerical_mismatch"):
            with self.subTest(stage=stage):
                self.rtl.run.side_effect = BackendError(stage, "injected failure")
                result = self.manager().execute(I, I, requirements=Requirements(preference="prefer_rtl"))
                self.assertEqual(result["status"], "fallback_ok")
                self.assertEqual(result["selected_backend"], "rtl_simulated")
                self.assertEqual(result["backend"], "software")
                self.assertEqual(result["attempts"][0]["diagnostic"]["stage"], stage)
                self.assertEqual(result["metrics"]["failure_count"], 1)
                self.assertEqual(result["metrics"]["fallback_count"], 1)
                self.assertFalse(result["metrics"]["initial_selection_success"])
                self.assertGreaterEqual(result["fallback"]["time_before_fallback_seconds"], 0)

    def test_invalid_nan_and_overflow_results_trigger_fallback(self):
        for raw in (None, {"E": I, "valid": False, "status": "numeric_overflow", "bit_exact": True},
                    {"E": np.full((3, 3), np.nan), "valid": True, "status": "ok", "bit_exact": True}):
            self.rtl.run.side_effect = None
            self.rtl.run.return_value = raw
            result = self.manager().execute(I, I, requirements=Requirements(preference="prefer_rtl"))
            self.assertEqual(result["status"], "fallback_ok")
            np.testing.assert_array_equal(result["E"], I)

    def test_post_execution_error_violation(self):
        self.rtl.run.side_effect = lambda F, K: {**fake_rtl_result(F, K), "E": I + .1}
        result = self.manager().execute(I, I, requirements=Requirements(preference="prefer_rtl"))
        self.assertEqual(result["status"], "fallback_ok")
        initial = result["attempts"][0]
        self.assertEqual(initial["status"], "constraint_violation")
        self.assertIn("max_error", initial["diagnostic"]["violations"])
        self.assertIsNone(initial["E"])

    def test_no_fallback_or_no_feasible_fallback(self):
        self.rtl.run.side_effect = BackendError("simulation", "injected")
        result = self.manager().execute(I, I, requirements=Requirements(preference="prefer_rtl", fallback="none"))
        self.assertEqual(result["status"], "error")
        self.assertFalse(result["fallback"]["used"])
        profiles = document(synthetic_profile("software", error=1), synthetic_profile("rtl_simulated"))
        result = self.manager(profiles).execute(I, I, requirements=Requirements(preference="prefer_rtl"))
        self.assertFalse(result["fallback"]["used"])
        self.assertEqual(result["fallback"]["not_executed_reason"], "no_feasible_fallback")

    def test_other_fallback_can_execute_rtl_after_software_failure(self):
        original = run_backend
        def injected(backend, *args, **kwargs):
            if backend == "software":
                return {"backend": backend, "status": "error", "valid": False, "E": None,
                        "diagnostic": {"stage": "injected"}, "metrics": {"observed_seconds": .00001}}
            return original(backend, *args, **kwargs)
        with patch("hybrid_sfm.manager.run_backend", side_effect=injected):
            result = self.manager().execute(I, I, requirements=Requirements(fallback="other"))
        self.assertEqual(result["status"], "fallback_ok")
        self.assertEqual(result["backend"], "rtl_simulated")

    def test_wall_time_violation_blocks_infeasible_fallback(self):
        def slow(F, K):
            time.sleep(.02)
            return fake_rtl_result(F, K)
        self.rtl.run.side_effect = slow
        profiles = document(synthetic_profile("software", .00001), synthetic_profile("rtl_simulated", .00001))
        result = self.manager(profiles).execute(I, I, requirements=Requirements(preference="prefer_rtl", max_seconds=.01))
        self.assertEqual(result["status"], "constraint_violation")
        self.assertIsNone(result["E"])
        self.assertFalse(result["fallback"]["used"])

    def test_request_budget_includes_failed_attempt_and_fallback(self):
        original = run_backend
        def delayed(backend, *args, **kwargs):
            time.sleep(.02)
            return original(backend, *args, **kwargs)
        self.rtl.run.side_effect = BackendError("parsing", "injected")
        profiles = document(synthetic_profile("software", .00001), synthetic_profile("rtl_simulated", .00001))
        with patch("hybrid_sfm.manager.run_backend", side_effect=delayed):
            result = self.manager(profiles).execute(I, I, requirements=Requirements(preference="prefer_rtl", max_seconds=.035))
        self.assertTrue(result["fallback"]["used"])
        self.assertEqual(result["status"], "constraint_violation")
        self.assertFalse(result["valid"])
        self.assertIsNone(result["E"])

    def test_metrics_serialization_and_sfm_barrier(self):
        self.rtl.run.side_effect = BackendError("parsing", "injected")
        result = estimate_essential(I, F=I, manager=self.manager(), mode="auto",
                                    requirements=Requirements(preference="prefer_rtl"))
        restored = json.loads(json.dumps(result, default=json_value, allow_nan=False))
        self.assertEqual(restored["metrics"]["fallback_count"], 1)
        self.assertEqual(restored["estimation"]["method"], "provided_F")
        np.testing.assert_array_equal(require_valid_essential(restored), I)
        invalid = self.manager().execute(I, I, mode="rtl_simulated")
        with self.assertRaises(ValueError):
            require_valid_essential(invalid)
        with self.assertRaises(ValueError):
            require_valid_essential({"valid": True, "status": "ok", "E": np.zeros((3, 3))})

    def test_invalid_requirements(self):
        for kwargs in ({"max_error": -1}, {"max_error": float("nan")}, {"max_seconds": -1},
                       {"max_seconds": float("inf")}, {"preference": "energy"}, {"fallback": "always"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Requirements(**kwargs)


class ProfileAndCliTests(WorkspaceTest):
    def test_real_software_characterization_roundtrip(self):
        profile_doc = characterize([(I, I), (I * 2, I)], backends=("software",), repeats=2, warmup=1)
        profile = profile_doc["profiles"][0]
        self.assertEqual(len(profile["samples"]), 4)
        self.assertEqual(profile["summary"]["failure_rate"], 0)
        self.assertEqual(profile["signature"]["numpy"], np.__version__)
        path = self.directory / "profile.json"
        write_json(path, profile_doc)
        result = ExecutionManager(load_profiles(path)).execute(I, I)
        self.assertEqual(result["backend"], "software")

    def test_profile_validation_rejects_invalid_measurements(self):
        for field, value in (("observed_seconds", -1), ("max_abs_error", float("nan")), ("valid", 1)):
            profiles = document(synthetic_profile("software"))
            profiles["profiles"][0]["samples"][0][field] = value
            with self.assertRaises(ValueError):
                validate_profiles(profiles)
        profiles = document(synthetic_profile("software"))
        profiles["profiles"][0]["summary"]["max_seconds"] = 0
        with self.assertRaises(ValueError):
            validate_profiles(profiles)

    def test_characterization_records_failures_without_fabricated_errors(self):
        for details in (None, ["malformed"]):
            with patch("hybrid_sfm.profiles.implementation_signature", side_effect=signature), \
                    patch("hybrid_sfm.profiles.run_backend", return_value={"valid": False, "status": "error",
                          "metrics": {"observed_seconds": .1}, "diagnostic": {"stage": "injected"}, "details": details}):
                result = characterize([(I, I)], backends=("software",), warmup=0)
            self.assertEqual(result["profiles"][0]["summary"]["failure_rate"], 1)
            self.assertIsNone(result["profiles"][0]["summary"]["max_abs_error"])

    def test_cli_fixed_auto_and_characterization(self):
        profile = self.directory / "profile.json"
        def cli(*args):
            completed = subprocess.run([sys.executable, "-m", "hybrid_sfm", *args], cwd=PROJECT_ROOT,
                                       capture_output=True, text=True, timeout=20)
            return completed.returncode, json.loads(completed.stdout) if completed.stdout else None
        code, result = cli("--backend", "software")
        self.assertEqual(code, 0)
        self.assertEqual(result["backend"], "software")
        code, result = cli("--backend", "auto")
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "no_feasible_configuration")
        code, _ = cli("--characterize", "--backend", "software", "--output", str(profile))
        self.assertEqual(code, 0)
        code, result = cli("--backend", "auto", "--profiles", str(profile))
        self.assertEqual(code, 0)
        self.assertEqual(result["backend"], "software")
        invalid_input = self.directory / "invalid.json"
        invalid_input.write_text("[]", encoding="utf-8")
        code, result = cli("--characterize", "--input", str(invalid_input))
        self.assertEqual(code, 1)
        self.assertEqual(result["stage"], "input")

    def test_input_correspondences_validation(self):
        for points in (None, np.zeros((7, 2)), np.zeros((8, 3)), np.full((8, 2), np.nan)):
            with self.assertRaises(ValueError):
                estimate_essential(I, points1=points, points2=points, mode="software")
        with self.assertRaises(ValueError):
            estimate_essential(I, F=I, points1=np.zeros((8, 2)), mode="software")

    def test_opencv_correspondences_to_valid_essential(self):
        if importlib.util.find_spec("cv2") is None:
            if os.environ.get("REQUIRE_OPENCV") == "1":
                self.fail("REQUIRE_OPENCV=1, mas OpenCV ausente")
            self.skipTest("OpenCV opcional ausente")
        rng = np.random.default_rng(12)
        world = rng.uniform(-1, 1, (20, 3))
        world[:, 2] += 4
        first = world[:, :2] / world[:, 2, None]
        moved = world + np.array([.3, .05, .1])
        second = moved[:, :2] / moved[:, 2, None]
        result = estimate_essential(I, points1=first, points2=second, mode="software")
        self.assertEqual(result["estimation"]["method"], "opencv.FM_8POINT")
        self.assertTrue(result["valid"])
        self.assertEqual(require_valid_essential(result).shape, (3, 3))


class ManagerRtlTests(WorkspaceTest):
    @classmethod
    def setUpClass(cls):
        if not GHDL:
            if os.environ.get("REQUIRE_GHDL") == "1":
                raise RuntimeError("GHDL ausente")
            raise unittest.SkipTest("GHDL ausente")

    def test_real_profiles_selection_and_both_fixed_backends(self):
        config = ExecutionConfig(ghdl=GHDL)
        rtl = GhdlBackend(ghdl=GHDL, build_dir=self.directory / "rtl")
        profiles = characterize([(I, I)], config=config, rtl_backend=rtl, repeats=2, warmup=1)
        self.assertEqual(len(profiles["profiles"]), 2)
        manager = ExecutionManager(profiles, config=config, rtl_backend=rtl)
        for backend in ("software", "rtl_simulated"):
            result = manager.execute(I, I, mode=backend)
            self.assertTrue(result["valid"])
            np.testing.assert_array_equal(result["E"], I)
        chosen = manager.execute(I, I)
        fastest = min(profiles["profiles"], key=lambda p: (p["summary"]["max_seconds"], p["backend"] != "software"))
        self.assertEqual(chosen["selected_backend"], fastest["backend"])
        result = manager.execute(I, I, requirements=Requirements(preference="prefer_rtl"))
        self.assertEqual(result["backend"], "rtl_simulated")

    def test_real_simulator_failure_falls_back_without_changing_selection_record(self):
        config = ExecutionConfig(ghdl=GHDL)
        rtl = GhdlBackend(ghdl=GHDL, build_dir=self.directory / "rtl")
        profiles = characterize([(I, I)], config=config, rtl_backend=rtl, repeats=1, warmup=0)
        with patch.object(rtl, "run", side_effect=BackendError("timeout", "injected after characterization")):
            result = ExecutionManager(profiles, config=config, rtl_backend=rtl).execute(
                I, I, requirements=Requirements(preference="prefer_rtl"))
        self.assertEqual(result["status"], "fallback_ok")
        self.assertFalse(result["metrics"]["initial_selection_success"])

    def test_real_subprocess_timeout_falls_back(self):
        from hybrid_sfm.ghdl_backend import _run_process
        config = ExecutionConfig(ghdl=GHDL)
        rtl = GhdlBackend(ghdl=GHDL, build_dir=self.directory / "rtl")
        profiles = characterize([(I, I)], config=config, rtl_backend=rtl, repeats=1, warmup=1)
        def force_simulation_timeout(command, cwd, timeout, stage):
            return _run_process(command, cwd, 0.000001 if stage == "simulation" else timeout, stage)
        with patch("hybrid_sfm.ghdl_backend._run_process", side_effect=force_simulation_timeout):
            result = ExecutionManager(profiles, config=config, rtl_backend=rtl).execute(
                I, I, requirements=Requirements(preference="prefer_rtl"))
        self.assertEqual(result["status"], "fallback_ok")
        failure = result["attempts"][0]["diagnostic"]
        self.assertEqual(failure["stage"], "timeout")
        self.assertIsNone(failure["process"].returncode)


if __name__ == "__main__":
    unittest.main()
