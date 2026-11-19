"""Geometria calibrada com ruído medido separadamente da quantização RTL."""

from itertools import product

import numpy as np

from experiments.analysis import numerical_metrics
from experiments.datasets import skew
from hybrid_sfm.fixed_point import quantize


def cases(seed):
    import cv2

    for split, child in zip(("characterization", "development", "evaluation"),
                            np.random.SeedSequence(seed).spawn(3)):
        rng = np.random.default_rng(child)
        for focal, motion, noise in product((220, 525, 1100), (.05, .2, .5), (0., .5, 1.5)):
            angle = rng.uniform(.03, .1)
            c, s = np.cos(angle), np.sin(angle)
            R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
            t = motion * np.array([1, rng.uniform(-.2, .2), rng.uniform(.02, .15)])
            K = np.array([[focal, 0, 320], [0, focal, 240], [0, 0, 1.]])
            E = skew(t) @ R
            inverse = np.linalg.inv(K)
            exact = inverse.T @ E @ inverse
            world = rng.uniform((-0.8, -.6, 4), (.8, .6, 7), size=(48, 3))
            moved = (R @ world.T).T + t
            points = []
            for camera in (world, moved):
                homogeneous = (K @ camera.T).T
                points.append(homogeneous[:, :2] / homogeneous[:, 2, None])
            noisy = [p + rng.normal(0, noise, p.shape) for p in points]
            F, _ = cv2.findFundamentalMat(*noisy, cv2.FM_8POINT)
            if F is None or F.shape != (3, 3) or np.linalg.matrix_rank(F) != 2:
                raise ValueError("Falha de estimação sintética")
            # Torna as escalas comparáveis à norma da F teórica de cada cena.
            F *= np.linalg.norm(exact) / np.linalg.norm(F)
            if np.sum(F * exact) < 0:
                F = -F
            clean1, clean2 = (np.column_stack((p, np.ones(len(p)))) for p in points)
            for scale in (.01, 1., 100., 100000.):
                yield {"id": f"{split}/{focal}/{motion}/{noise}/{scale}", "split": split,
                       "focal": focal, "motion": motion, "noise_px": noise, "scale": scale,
                       "F_source": "theoretical" if noise == 0 else "FM_8POINT",
                       "F": scale * (exact if noise == 0 else F), "K": K,
                       "E_theory": scale * E, "F_theory": scale * exact, "R": R, "t": t,
                       "world": world, "clean_points": points, "noisy_points": noisy,
                       "minimum_depth": float(min(world[:, 2].min(), moved[:, 2].min())),
                       "clean_epipolar_max": float(np.max(np.abs(np.einsum("ni,ij,nj->n", clean2, exact, clean1))))}


def evaluate(dataset, rtl, shape_limit):
    final = [case for case in dataset if case["split"] == "evaluation"]
    outputs = rtl.run_batch([(c["F"], c["K"]) for c in final])["results"]
    for case, result in zip(final, outputs):
        epsilon = 1e-12
        theory = case["E_theory"]
        float64 = result["reference_float64"]
        shape = numerical_metrics(result["E"], float64, epsilon, geometric=True)["scale_invariant_error"]
        quantized = quantize(case["F"])
        yield {**{key: case[key] for key in ("id", "focal", "motion", "noise_px", "scale", "F_source",
                                             "minimum_depth", "clean_epipolar_max")},
               "bit_exact": result["bit_exact"], "valid_no_overflow": result["valid"],
               "overflow_events": result["overflow_events"],
               "entries_lost_to_quantization": int(np.count_nonzero((case["F"] != 0) & (quantized == 0))),
               "max_abs_error": result["max_abs_error"],
               "input_quantization_max_abs_error": result["input_quantization_max_abs_error"],
               "rtl_shape_vs_float64": shape,
               "float64_shape_vs_theory": numerical_metrics(float64, theory, epsilon, geometric=True)["scale_invariant_error"],
               "rtl_shape_vs_theory": numerical_metrics(result["E"], theory, epsilon, geometric=True)["scale_invariant_error"],
               "distorted_without_overflow": bool(result["valid"] and (shape is None or shape > shape_limit)),
               "E_rtl_raw": result["E_raw"], "E_reference": float64, "E_theory": theory,
               "model_raw": result["reference_integer_raw"]}
