"""Entradas independentes por split, com geometria e procedência explícitas."""

from contextlib import redirect_stdout
import hashlib
import io
import json

import numpy as np

from hybrid_sfm.fixed_point import MAX_VALUE, MIN_VALUE
from hybrid_sfm.ghdl_backend import PROJECT_ROOT
from hybrid_sfm.metrics import json_value

SPLITS = ("characterization", "development", "evaluation")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=json_value,
                                     allow_nan=False).encode()).hexdigest()


def skew(t):
    x, y, z = t
    return np.array([[0, -z, y], [z, 0, -x], [-y, x, 0.]])


def _case(category, family, split, index, F, K, **metadata):
    return {"id": f"{family}/{split}/{index:02}", "category": category, "family": family,
            "split": split, "F": np.asarray(F).tolist(), "K": np.asarray(K).tolist(),
            "metadata": metadata}


def synthetic_camera_case(rng):
    angle = rng.uniform(-.15, .15)
    c, s = np.cos(angle), np.sin(angle)
    R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    t = np.array([rng.uniform(.15, .4), rng.uniform(-.05, .05), rng.uniform(-.02, .02)])
    K = np.array([[525., 0, 320], [0, 525., 240], [0, 0, 1.]])
    E = skew(t) @ R
    inverse = np.linalg.inv(K)
    F = inverse.T @ E @ inverse
    world = rng.uniform(-1, 1, (24, 3))
    world[:, 2] += 5
    camera2 = (R @ world.T).T + t
    first = (K @ world.T).T
    second = (K @ camera2.T).T
    first, second = first[:, :2] / first[:, 2, None], second[:, :2] / second[:, 2, None]
    homogeneous1 = np.column_stack((first, np.ones(len(first))))
    homogeneous2 = np.column_stack((second, np.ones(len(second))))
    residual = np.einsum("ni,ij,nj->n", homogeneous2, F, homogeneous1)
    return F, K, {"R": R, "t": t, "E_ground_truth": E, "world": world,
                  "points1": first, "points2": second, "max_epipolar_residual": float(np.max(np.abs(residual))),
                  "min_depth_camera1": float(np.min(world[:, 2])),
                  "min_depth_camera2": float(np.min(camera2[:, 2])), "intrinsics": "known_synthetic"}


def generate_dataset(seed):
    import cv2
    from extract_points import extract_feature_points
    cv2.setNumThreads(1)
    seeds = np.random.SeedSequence(seed).spawn(4)
    cases = []
    K_mixed = np.array([[1, .25, .5], [0, 1, -.5], [0, 0, 1.]])
    for split_index, split in enumerate(SPLITS):
        rng = np.random.default_rng(seeds[split_index])
        count = 4 if split == "characterization" else (1 if split == "development" else 2)
        for family, amplitude, K in (("bounded", .5, np.eye(3)), ("tiny", 3e-6, np.eye(3)),
                                     ("mixed", 1., K_mixed)):
            for index in range(count):
                F = rng.uniform(-amplitude, amplitude, (3, 3))
                if split == "characterization" and index < 2:
                    F[:] = (-amplitude if index == 0 else amplitude)
                cases.append(_case("controlled", family, split, index, F, K,
                                   amplitude=amplitude, physical_geometry=False))
        for index in range(count):
            F = np.diag(rng.uniform(1, 2, 3))
            if split == "characterization" and index < 2:
                F = np.eye(3) * (1 if index == 0 else 2)
            cases.append(_case("controlled", "overflow32", split, index, F, np.eye(3) * 200,
                               physical_geometry=False, intended_stress="result32"))
            diag = rng.uniform(MIN_VALUE, MAX_VALUE, 3)
            if split == "characterization" and index < 2:
                diag[:] = MIN_VALUE if index == 0 else MAX_VALUE
            cases.append(_case("controlled", "limits", split, index, np.diag(diag), np.eye(3),
                               physical_geometry=False, intended_stress="representation_limits"))
        # Fronteiras signed64: diagnóstico de overflow, nunca baseline numérico válido.
        F = np.full((3, 3), MIN_VALUE if split == "characterization" else -32000 + split_index)
        cases.append(_case("controlled", "accumulator64", split, 0, F, np.full((3, 3), MIN_VALUE),
                           physical_geometry=False, intended_stress="accumulator64"))
        physical_count = 8 if split == "characterization" else (2 if split == "development" else 3)
        for index in range(physical_count):
            F, K, metadata = synthetic_camera_case(rng)
            cases.append(_case("synthetic_geometry", "calibrated_cameras", split, index, F, K, **metadata))

    image_seed = int(seeds[3].generate_state(1)[0] % (2**31 - 1))
    np.random.seed(image_seed)
    cv2.setRNGSeed(image_seed)
    image_paths = [PROJECT_ROOT / "images" / name for name in ("img1.jpeg", "img2.jpeg")]
    stream = io.StringIO()
    with redirect_stdout(stream):
        pts1, pts2 = extract_feature_points(*(str(p) for p in image_paths), max_points=100000)
    if pts1 is None or pts2 is None or len(pts1) < 96:
        raise ValueError("Correspondências insuficientes para splits de imagens independentes (mínimo 96)")
    order = np.random.default_rng(image_seed).permutation(len(pts1))
    pools = np.array_split(order, 3)
    K_estimated = np.array([[525., 0, 320], [0, 525., 240], [0, 0, 1.]])
    for split, pool, count in zip(SPLITS, pools, (4, 2, 2)):
        for index, indices in enumerate(np.array_split(pool, count)):
            F, _ = cv2.findFundamentalMat(pts1[indices], pts2[indices], cv2.FM_8POINT)
            if F is None or F.shape != (3, 3) or not np.isfinite(F).all():
                raise ValueError(f"Estimação F falhou em {split}/{index}")
            cases.append(_case("repository_images", "estimated_intrinsics", split, index, F, K_estimated,
                               points1=pts1[indices], points2=pts2[indices], point_ids=indices.tolist(),
                               intrinsics="estimated_not_calibrated", ground_truth=None,
                               estimation="OpenCV.FM_8POINT"))
    manifest = {"schema_version": 1, "seed": seed, "split_seed_sequences": [s.spawn_key for s in seeds],
                "cases": cases, "images": {"seed": image_seed, "opencv": cv2.__version__,
                "threads": 1, "pipeline": "extract_points.extract_feature_points",
                "pipeline_sha256": hashlib.sha256((PROJECT_ROOT / "extract_points.py").read_bytes()).hexdigest(),
                "parameters": {"SIFT": "OpenCV defaults", "FLANN_algorithm": 0, "trees": 5,
                               "checks": 50, "ratio": .7, "filter": "FM_RANSAC with OpenCV defaults",
                               "max_points": 100000}, "pipeline_stdout": stream.getvalue(),
                "inliers": len(pts1), "files_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in image_paths}}}
    # Normalização JSON também verifica ausência de NaN nos dados persistidos.
    return json.loads(json.dumps(manifest, default=json_value, allow_nan=False))
