import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from hybrid_sfm.fixed_point import (MAX_RAW, MAX_VALUE, MIN_RAW, MIN_VALUE, SCALE,
                                    essential_matrix_fixed, essential_matrix_raw, quantize)
from hybrid_sfm.ghdl_backend import (BackendError, GhdlBackend, PROJECT_ROOT, SOURCES,
                                    _run_process, parse_output)
from hybrid_sfm.reference import essential_matrix

GHDL = shutil.which(os.environ.get("GHDL", "ghdl"))
I = np.eye(3)
F_MIXED = np.array([[0, -1, 0.5], [1, 0, -0.25], [-0.5, 0.25, 0]])
TEST_ROOT = PROJECT_ROOT / "build/tests"


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        TEST_ROOT.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=TEST_ROOT)
        self.directory = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)


class ReferenceTests(unittest.TestCase):
    def test_identity_and_zero(self):
        np.testing.assert_array_equal(essential_matrix(F_MIXED, I), F_MIXED)
        np.testing.assert_array_equal(essential_matrix(np.zeros((3, 3)), I), np.zeros((3, 3)))
        np.testing.assert_array_equal(essential_matrix(F_MIXED, np.zeros((3, 3))), np.zeros((3, 3)))

    def test_analytic_non_diagonal_transpose(self):
        F = np.diag([1., -2., 3.])
        K = np.array([[1., 2., 0.], [0., 1., 3.], [0., 0., 1.]])
        expected = [[1, 2, 0], [2, 2, -6], [0, -6, -15]]
        np.testing.assert_array_equal(essential_matrix(F, K), expected)
        np.testing.assert_array_equal(essential_matrix_fixed(F, K).value, expected)

    def test_quantization_and_negative_floor(self):
        matrix = np.zeros((3, 3))
        matrix[0, 0] = -1.75 / SCALE
        self.assertEqual(quantize(matrix)[0, 0], -1)
        F = np.zeros((3, 3))
        F[0, 0] = -1 / SCALE
        K = I.copy()
        K[0, 0] = 0.5
        self.assertEqual(essential_matrix_fixed(F, K).raw[0, 0], -1)
        self.assertEqual(essential_matrix(F, K)[0, 0], -0.25 / SCALE)

    def test_exact_limits(self):
        F = np.diag([MIN_VALUE, MAX_VALUE, -1 / SCALE])
        model = essential_matrix_fixed(F, I)
        self.assertFalse(model.overflow)
        np.testing.assert_array_equal(model.raw, quantize(F))

    def test_invalid_values_rejected_before_truncation(self):
        for value in (np.nextafter(MAX_VALUE, np.inf), np.nextafter(MIN_VALUE, -np.inf),
                      32768., -32769., np.nan, np.inf, -np.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                quantize(np.full((3, 3), value))

    def test_bad_matrix_and_raw_types(self):
        for matrix in ([1, 2, 3], np.zeros((2, 3)), I.astype(complex), [["x"]] * 3):
            with self.subTest(matrix=str(matrix)), self.assertRaises(ValueError):
                essential_matrix(matrix, I)
        for matrix in (I, np.full((3, 3), MAX_RAW + 1), np.full((3, 3), MIN_RAW - 1)):
            with self.subTest(matrix=str(matrix)), self.assertRaises(ValueError):
                essential_matrix_raw(matrix, quantize(I))

    def test_result_overflow_is_not_mathematical_correctness(self):
        model = essential_matrix_fixed(I, I * 200)
        self.assertTrue(model.overflow)
        self.assertEqual(model.value[0, 0], -25536)
        self.assertEqual(essential_matrix(I, I * 200)[0, 0], 40000)
        self.assertTrue(any(e["kind"] == "result32" for e in model.overflow_events))

    def test_accumulator64_overflow_is_detected(self):
        model = essential_matrix_fixed(np.full((3, 3), MIN_VALUE), np.full((3, 3), MIN_VALUE))
        self.assertTrue(any(e["kind"] == "accumulator64" for e in model.overflow_events))


class ProtocolTests(WorkspaceTest):
    def test_parse_valid(self):
        path = self.directory / "out.txt"
        path.write_text("essential-q15.16-v1\n0 1 -2147483648 2147483647 0 0 0 0 0 0 0\n", encoding="ascii")
        raw, cycles = parse_output(path, 1, 10)[0]
        self.assertEqual(raw[0, 0], MIN_RAW)
        self.assertEqual(raw[0, 1], MAX_RAW)
        self.assertEqual(cycles, 1)

    def test_parse_invalid_and_undefined(self):
        path = self.directory / "out.txt"
        header = "essential-q15.16-v1\n"
        for content in ("", "bad\n", header, header + "0 1 " + "X " * 9,
                        header + "0 1 " + "0 " * 8, header + "0 1 " + "0 " * 10,
                        header + "1 1 " + "0 " * 9, header + "0 0 " + "0 " * 9,
                        header + "0 11 " + "0 " * 9,
                        header + "0 1 2147483648 " + "0 " * 8,
                        header + "0 1 1.0 " + "0 " * 8,
                        header + "0 1 " + "0 " * 9 + "\nextra"):
            with self.subTest(content=content):
                path.write_text(content, encoding="ascii")
                with self.assertRaises(BackendError) as caught:
                    parse_output(path, 1, 10)
                self.assertEqual(caught.exception.stage, "parsing")
        with self.assertRaises(BackendError):
            parse_output(self.directory / "missing", 1, 10)

    def test_subprocess_capture_failure_and_timeout(self):
        with self.assertRaises(BackendError) as caught:
            _run_process([sys.executable, "-c",
                          "import sys; print('out'); print('err', file=sys.stderr); sys.exit(7)"],
                         self.directory, 10, "simulation")
        self.assertEqual(caught.exception.stage, "simulation")
        record = caught.exception.process
        self.assertEqual(record.returncode, 7)
        self.assertIn("out", record.stdout)
        self.assertIn("err", record.stderr)
        with self.assertRaises(BackendError) as caught:
            _run_process([sys.executable, "-c", "import time; print('started', flush=True); time.sleep(5)"],
                         self.directory, 0.2, "simulation")
        self.assertEqual(caught.exception.stage, "timeout")
        self.assertIsNone(caught.exception.process.returncode)

    def test_missing_tool(self):
        with self.assertRaises(BackendError) as caught:
            GhdlBackend(ghdl="ghdl-does-not-exist-123").compile()
        self.assertEqual(caught.exception.stage, "tool")

    def test_inputs_rejected_before_ghdl(self):
        backend = GhdlBackend(ghdl="ghdl-does-not-exist-123")
        for cases, resets in (([], None), ([(I, I)], [False]), ([(I, I)], [1]),
                              ([(I, I)], []), ([(I * 32768, I)], None)):
            with self.subTest(resets=resets), self.assertRaises(ValueError):
                backend.run_batch(cases, resets)
        for timeout in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                GhdlBackend(timeout=timeout)

    def test_cli_missing_tool_reports_json(self):
        result = subprocess.run([sys.executable, "-m", "hybrid_sfm", "--input",
                                 "examples/essential_identity.json", "--ghdl", "missing-ghdl-123"],
                                cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["stage"], "tool")


class IntegrationTests(WorkspaceTest):
    @classmethod
    def setUpClass(cls):
        if not GHDL:
            if os.environ.get("REQUIRE_GHDL") == "1":
                raise RuntimeError("REQUIRE_GHDL=1, mas GHDL não está disponível")
            raise unittest.SkipTest("GHDL ausente; testes RTL não executados")

    def backend(self, project_root=PROJECT_ROOT):
        return GhdlBackend(ghdl=GHDL, project_root=project_root,
                           build_dir=self.directory / "compiled", timeout=15)

    def modified_project(self, old, new, file="src/essential_matrix.vhd"):
        root = self.directory / "project"
        for source in SOURCES:
            target = root / source
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((PROJECT_ROOT / source).read_bytes())
        path = root / file
        content = path.read_bytes()
        self.assertIn(old, content)
        path.write_bytes(content.replace(old, new))
        return root

    def test_consecutive_and_reset_results(self):
        cases = [(I, I), (F_MIXED, I), (F_MIXED, I * 2), (np.zeros((3, 3)), I),
                 (F_MIXED, np.zeros((3, 3))), (F_MIXED, I)]
        batch = self.backend().run_batch(cases, [True, False, False, False, True, True])
        for result, (F, K) in zip(batch["results"], cases):
            self.assertTrue(result["valid"])
            self.assertTrue(result["bit_exact"])
            self.assertEqual(result["cycles"], 1)
            np.testing.assert_array_equal(result["E"], essential_matrix(F, K))
        np.testing.assert_array_equal(batch["results"][1]["E"], batch["results"][-1]["E"])
        self.assertFalse(np.array_equal(batch["results"][1]["E"], batch["results"][2]["E"]))

    def test_analytic_and_noncommuting_matrices(self):
        K = np.array([[1., 2., 0.], [0., 1., 3.], [0., 0., 1.]])
        result = self.backend().run(np.diag([1., -2., 3.]), K)
        np.testing.assert_array_equal(result["E"], [[1, 2, 0], [2, 2, -6], [0, -6, -15]])

    def test_limits_and_overflow(self):
        cases = [(np.diag([MIN_VALUE, MAX_VALUE, -1 / SCALE]), I), (I, I * 200),
                 (np.full((3, 3), MIN_VALUE), np.full((3, 3), MIN_VALUE))]
        results = self.backend().run_batch(cases)["results"]
        self.assertTrue(results[0]["valid"])
        for result in results[1:]:
            self.assertFalse(result["valid"])
            self.assertEqual(result["status"], "numeric_overflow")
            self.assertTrue(result["bit_exact"])
            self.assertGreater(result["max_abs_error"], 1)
        self.assertTrue(any(e["kind"] == "accumulator64" for e in results[2]["overflow_events"]))

    def test_report_calibration_overflow(self):
        F = np.array([[0.5, 0.25, 0.125], [0.0625, 0.03125, 0.015625],
                      [0.0078125, 0.00390625, 0.001953125]])
        K = np.array([[525., 0., 320.], [0., 525., 240.], [0., 0., 1.]])
        result = self.backend().run(F, K)
        self.assertFalse(result["valid"])
        self.assertTrue(result["bit_exact"])
        self.assertGreater(result["max_abs_error"], 100000)

    def test_seeded_quantization_and_truncation(self):
        rng = np.random.default_rng(42)
        cases = [(rng.uniform(-1, 1, (3, 3)), rng.uniform(-2, 2, (3, 3))) for _ in range(30)]
        for result in self.backend().run_batch(cases)["results"]:
            self.assertTrue(result["valid"])
            self.assertTrue(result["bit_exact"])
            self.assertLess(result["max_abs_error"], 0.002)
            self.assertGreater(result["input_quantization_max_abs_error"], 0)
            self.assertGreater(result["arithmetic_max_abs_error"], 0)

    def test_cache_reuse_and_deleted_artifact(self):
        backend = self.backend()
        first = backend.run(F_MIXED, I)
        second = backend.run(F_MIXED, I)
        self.assertFalse(first["execution"]["compilation"]["cache_hit"])
        self.assertEqual(len(first["execution"]["compilation"]["processes"]), 6)
        self.assertTrue(second["execution"]["compilation"]["cache_hit"])
        self.assertEqual(second["execution"]["compilation"]["seconds"], 0)
        directory, _ = backend.compile()
        (directory / "work-obj08.cf").unlink()
        third = backend.run(F_MIXED, I)
        self.assertFalse(third["execution"]["compilation"]["cache_hit"])
        (directory / "work-obj08.cf").write_text("corrupted cache", encoding="ascii")
        fourth = backend.run(F_MIXED, I)
        self.assertFalse(fourth["execution"]["compilation"]["cache_hit"])
        np.testing.assert_array_equal(fourth["E"], F_MIXED)

    def test_cache_source_change(self):
        root = self.modified_project(b"-- Computa E", b"-- Test cache: Computa E")
        backend = self.backend(root)
        directory, _ = backend.compile()
        path = root / "src/essential_matrix.vhd"
        path.write_bytes(path.read_bytes() + b"\n-- source changed\n")
        updated, report = backend.compile()
        self.assertNotEqual(directory, updated)
        self.assertFalse(report["cache_hit"])

    def test_compilation_failure(self):
        root = self.modified_project(b"architecture RTL", b"invalid syntax architecture RTL")
        with self.assertRaises(BackendError) as caught:
            self.backend(root).run(I, I)
        self.assertEqual(caught.exception.stage, "compilation")
        self.assertNotEqual(caught.exception.process.returncode, 0)

    def test_undefined_output_is_failure(self):
        for state in "UXZWLH-":
            with self.subTest(state=state):
                replacement = ("E_out <= E_temp when ready /= '1' else "
                               f"(others => (others => (others => '{state}')));").encode("ascii")
                root = self.modified_project(b"E_out <= E_temp;", replacement)
                with self.assertRaises(BackendError) as caught:
                    self.backend(root).run(I, I)
                self.assertEqual(caught.exception.stage, "simulation")
                self.assertIn("Undefined kernel output", caught.exception.process.stdout + caught.exception.process.stderr)

    def test_stalled_kernel_cycle_timeout(self):
        root = self.modified_project(b"ready <= '1';", b"ready <= '0';")
        with self.assertRaises(BackendError) as caught:
            self.backend(root).run(I, I)
        self.assertEqual(caught.exception.stage, "simulation")
        self.assertIn("Kernel cycle timeout", caught.exception.process.stdout + caught.exception.process.stderr)

    def test_wrong_defined_output_is_failure(self):
        root = self.modified_project(b"E_out <= E_temp;", b"E_out <= (others => (others => (others => '0')));")
        with self.assertRaises(BackendError) as caught:
            self.backend(root).run(I, I)
        self.assertEqual(caught.exception.stage, "numerical_mismatch")

    def test_successful_simulator_without_output_is_failure(self):
        backend = self.backend()
        directory, compilation = backend.compile()
        with patch.object(backend, "compile", return_value=(directory, compilation)), \
                patch("hybrid_sfm.ghdl_backend._run_process", return_value=None):
            with self.assertRaises(BackendError) as caught:
                backend.run(I, I)
        self.assertEqual(caught.exception.stage, "parsing")

    def test_cli_success_and_overflow_exit_codes(self):
        path = self.directory / "input.json"
        output = self.directory / "output.json"
        for K, expected_code in ((I, 0), (I * 200, 2)):
            path.write_text(json.dumps({"F": I.tolist(), "K": K.tolist()}), encoding="utf-8")
            result = subprocess.run([sys.executable, "-m", "hybrid_sfm", "--input", str(path),
                                     "--output", str(output), "--ghdl", GHDL],
                                    cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, expected_code, result.stdout + result.stderr)
            self.assertTrue(json.loads(output.read_text(encoding="utf-8"))["bit_exact"])


if __name__ == "__main__":
    unittest.main()
