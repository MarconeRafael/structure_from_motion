import json
import importlib.util
import os
import unittest

import numpy as np

from experiments.analysis import numerical_metrics, policy_comparisons, quantiles, write_csv
from experiments.datasets import digest, generate_dataset, synthetic_camera_case
from experiments.runner import validate_config
from hybrid_sfm.ghdl_backend import PROJECT_ROOT
from hybrid_sfm.reference import essential_matrix
from tests.test_essential import WorkspaceTest


class DatasetTests(unittest.TestCase):
    def test_physical_geometry_independent_reference(self):
        F, K, info = synthetic_camera_case(np.random.default_rng(42))
        self.assertGreater(info["min_depth_camera1"], 0)
        self.assertGreater(info["min_depth_camera2"], 0)
        self.assertLess(info["max_epipolar_residual"], 1e-12)
        np.testing.assert_allclose(essential_matrix(F, K), info["E_ground_truth"], atol=1e-14, rtol=1e-12)

    def test_splits_reproducible_and_image_matches_disjoint(self):
        if importlib.util.find_spec("cv2") is None:
            if os.environ.get("REQUIRE_OPENCV") == "1":
                self.fail("OpenCV obrigatório ausente")
            self.skipTest("OpenCV opcional ausente")
        first, second = generate_dataset(7319), generate_dataset(7319)
        self.assertEqual(digest(first), digest(second))
        self.assertEqual(len({c["id"] for c in first["cases"]}), len(first["cases"]))
        indices = {}
        for split in ("characterization", "development", "evaluation"):
            indices[split] = {i for c in first["cases"] if c["category"] == "repository_images" and c["split"] == split
                              for i in c["metadata"]["point_ids"]}
        self.assertFalse(indices["characterization"] & indices["evaluation"])
        self.assertFalse(indices["development"] & indices["evaluation"])
        self.assertFalse(indices["characterization"] & indices["development"])


class AnalysisTests(WorkspaceTest):
    def test_near_zero_and_scale_sign_conventions(self):
        zero = np.zeros((3, 3))
        result = numerical_metrics(zero, zero, 1e-12, geometric=True)
        self.assertEqual(result["relative_error"], 0)
        self.assertIsNone(result["scale_invariant_error"])
        result = numerical_metrics(np.eye(3), zero, 1e-12)
        self.assertIsNone(result["relative_error"])
        self.assertTrue(result["relative_reference_near_zero"])
        result = numerical_metrics(-2 * np.eye(3), np.eye(3), 1e-12, geometric=True)
        self.assertLess(result["scale_invariant_error"], 1e-15)

    def test_oracle_is_post_hoc_and_failed_alternative_not_feasible(self):
        common = {"replication": 0, "case_id": "case", "scenario": "strict", "repetition": 0}
        rows = [{**common, "policy": "software", "valid": True, "total_seconds": .1},
                {**common, "policy": "rtl_simulated", "valid": False, "total_seconds": .01},
                {**common, "policy": "auto", "valid": True, "total_seconds": .3, "selected_backend": "software"}]
        result = policy_comparisons(rows)[0]
        self.assertEqual(result["oracle_backend"], "software")
        self.assertAlmostEqual(result["matched_fixed_overhead_seconds"], .2)
        self.assertTrue(result["initial_selection_feasible_ex_post"])

    def test_csv_and_percentiles_preserve_nulls(self):
        result = quantiles([1, 2, 3])
        self.assertEqual(result["seconds_median"], 2)
        self.assertAlmostEqual(result["seconds_p95"], 2.9)
        self.assertIsNone(quantiles([])["seconds_median"])
        path = self.directory / "out.csv"
        write_csv(path, [{"value": None, "raw": [1, -2]}, {"value": 0, "raw": []}])
        self.assertIn('"[1, -2]"', path.read_text(encoding="utf-8"))

    def test_config_rejects_duplicate_scenarios(self):
        config = json.loads((PROJECT_ROOT / "experiments/config.json").read_text(encoding="utf-8"))
        validate_config(config)
        config["scenarios"].append(config["scenarios"][0])
        with self.assertRaises(ValueError):
            validate_config(config)
