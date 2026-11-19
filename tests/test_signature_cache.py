from dataclasses import replace
from pathlib import Path
import shutil
from unittest.mock import patch

import numpy as np

from hybrid_sfm.backends import ExecutionConfig
from hybrid_sfm.ghdl_backend import GhdlBackend, PROJECT_ROOT, SOURCES
from hybrid_sfm.manager import ExecutionManager, Requirements
from hybrid_sfm.metrics import implementation_signature
from hybrid_sfm.profiles import characterize
from tests.test_essential import WorkspaceTest


class SignatureCacheTests(WorkspaceTest):
    def test_warm_hit_and_decision_matches_uncached(self):
        matrices = (np.eye(3), np.eye(3))
        config = ExecutionConfig(ghdl="absent-stage4")
        profiles = characterize([matrices], config=config, backends=("software",))
        warm = ExecutionManager(profiles, config=config)
        cold = ExecutionManager(profiles, config=config, reuse_signatures=False)
        with patch("hybrid_sfm.manager.implementation_signature", wraps=implementation_signature) as signature:
            warm.execute(*matrices)
            cached = warm.execute(*matrices)
            self.assertEqual(signature.call_count, 1)
        self.assertEqual(cached["metrics"]["signature_cache_hits"], 1)
        self.assertEqual(cached["decision"], cold.execute(*matrices)["decision"])
        warm.config = replace(config, timeout=10)
        self.assertEqual(warm.execute(*matrices)["metrics"]["signature_cache_hits"], 0)

    def test_source_and_tool_changes_invalidate_including_disappearance(self):
        root = self.directory / "rtl"
        for name in SOURCES:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PROJECT_ROOT / name, path)
        executable = root / "ghdl.exe"
        executable.write_bytes(b"first")
        executable.chmod(0o755)
        rtl = GhdlBackend(ghdl=executable, project_root=root, build_dir=root / "build")
        manager = ExecutionManager(rtl_backend=rtl)
        with patch("hybrid_sfm.metrics._run_process") as version:
            version.return_value.stdout = "same version"
            first, hit = manager._signature("rtl_simulated")
            self.assertFalse(hit)
            self.assertTrue(manager._signature("rtl_simulated")[1])
            self.assertEqual(version.call_count, 1)
            source = root / SOURCES[-1]
            source.write_bytes(source.read_bytes() + b"\n-- Changed")
            second, hit = manager._signature("rtl_simulated")
            self.assertFalse(hit)
            self.assertNotEqual(first, second)
            executable.write_bytes(b"replacement")
            third, hit = manager._signature("rtl_simulated")
            self.assertFalse(hit)
            self.assertNotEqual(second["ghdl_executable_sha256"], third["ghdl_executable_sha256"])
            executable.unlink()
            candidate = manager.execute(np.eye(3), np.eye(3))["decision"]["candidates"][1]
            self.assertEqual(candidate["reasons"][0]["code"], "unavailable_or_unsupported")
            self.assertNotIn("rtl_simulated", manager._signatures)

    def test_unprofiled_fallback_is_opt_in_and_post_validated(self):
        manager = ExecutionManager(config=ExecutionConfig(ghdl="absent-stage4"))
        eye = np.eye(3)
        self.assertEqual(manager.execute(eye, eye)["status"], "no_feasible_configuration")
        options = Requirements(verify_unprofiled_software=True, max_error=0)
        result = manager.execute(eye, eye, requirements=options)
        self.assertTrue(result["valid"])
        self.assertIsNone(result["selected_backend"])
        self.assertFalse(result["metrics"]["initial_selection_success"])
        self.assertFalse(result["fallback"]["reason"]["prior_guarantee"])
        self.assertEqual(result["metrics"]["fallback_count"], 1)
        self.assertFalse(manager.execute(eye, eye, requirements=replace(options, max_seconds=0))["valid"])
        self.assertFalse(manager.execute(eye, eye, requirements=replace(options, fallback="none"))["valid"])
        self.assertFalse(manager.execute(eye * 1e308, eye * 1e308, requirements=options)["valid"])
