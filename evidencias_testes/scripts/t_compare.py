import numpy as np, re, glob, os, sys
d = sys.argv[1]
a = np.load(os.path.join(d, "orig_simulated_data.npz")); b = np.load(os.path.join(d, "run_sim_1.npz")); c = np.load(os.path.join(d, "run_sim_2.npz"))
for k in ("pts1", "pts2", "K"):
    print(k, "orig==run1:", np.array_equal(a[k], b[k]), "max|diff|=%.3g" % np.abs(a[k] - b[k]).max(), "| run1==run2:", np.array_equal(b[k], c[k]))
t0 = open(os.path.join(d, "orig_vhdl_testbench_data.txt"), "rb").read()
t1 = open(os.path.join(d, "run_tbdata_1.txt"), "rb").read()
print("tbdata bytes orig/run1:", len(t0), len(t1), "CRLF orig:", b"\r\n" in t0, "CRLF run1:", b"\r\n" in t1)
n0 = t0.replace(b"\r\n", b"\n"); n1 = t1.replace(b"\r\n", b"\n")
print("tbdata iguais apos normalizar CRLF:", n0 == n1)
if n0 != n1:
    l0 = n0.decode("utf-8", "replace").splitlines(); l1 = n1.decode("utf-8", "replace").splitlines()
    diff = [(i, x, y) for i, (x, y) in enumerate(zip(l0, l1)) if x != y]
    print("linhas diferentes:", len(diff), ascii(diff[:3]))

# logs de extract_points
print("--- extract_points (5 execucoes)")
for i in range(1, 6):
    s = open(os.path.join(d, f"log_extract_{i}.txt"), encoding="utf-8", errors="replace").read()
    kp = re.findall(r"Imagem \d: (\d+)\n", s)
    m = re.search(r"Correspond.*?: (\d+)", s); inl = re.search(r"inliers.*?: (\d+)", s)
    pts = re.findall(r"pts1_in\((\d), 0\) <= to_signed\((-?\d+)", open(os.path.join(d, f"run_points_{i}.txt"), encoding="utf-8", errors="replace").read())
    print(i, "kp:", kp[-2:], "good:", m.group(1) if m else None, "inliers:", inl.group(1) if inl else None, "n_pts_emitidos:", len(pts))
