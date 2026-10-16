import cv2, numpy as np, re, sys, os, time

root, d = sys.argv[1], sys.argv[2]
np.set_printoptions(precision=6, suppress=True, linewidth=140)

def readlog(p):
    b = open(p, "rb").read()
    t = b.decode("utf-16") if b[:2] == b"\xff\xfe" else b.decode("utf-8", "replace")
    return t.replace("\r", "").replace("\n", "")

def hom(x):
    return np.hstack([x, np.ones((len(x), 1))])

def sampson(F, x1, x2):
    X1, X2 = hom(x1), hom(x2)
    Fx1 = X1 @ F.T
    Ftx2 = X2 @ F
    num = np.sum(X2 * Fx1, axis=1) ** 2
    den = Fx1[:, 0] ** 2 + Fx1[:, 1] ** 2 + Ftx2[:, 0] ** 2 + Ftx2[:, 1] ** 2
    return np.sqrt(num / den)

def stats(a):
    return "media=%.3f mediana=%.3f max=%.3f" % (a.mean(), np.median(a), a.max())

img1 = cv2.imread(os.path.join(root, "images", "img1.jpeg"), 0)
img2 = cv2.imread(os.path.join(root, "images", "img2.jpeg"), 0)
sift = cv2.SIFT_create()

print("### SIFT por imagem (processamento individual)")
res = []
for name, im in (("img1", img1), ("img2", img2)):
    t = time.perf_counter(); kp, de = sift.detectAndCompute(im, None); dt = time.perf_counter() - t
    print("%s: keypoints=%d descritores=%s tempo=%.3f s" % (name, len(kp), de.shape, dt))
    res.append((kp, de))
(kp1, d1), (kp2, d2) = res

print("### Correspondencia conjunta (FLANN kd-tree 5, checks=50, knn k=2)")
flann = cv2.FlannBasedMatcher(dict(algorithm=0, trees=5), dict(checks=50))
t = time.perf_counter(); matches = flann.knnMatch(d1, d2, k=2); dt = time.perf_counter() - t
print("knnMatch: pares=%d tempo=%.3f s" % (len(matches), dt))
sel = {}
for ratio in (0.7, 0.8):
    g = [m for m, n in (p for p in matches if len(p) == 2) if m.distance < ratio * n.distance]
    p1 = np.float32([kp1[m.queryIdx].pt for m in g]); p2 = np.float32([kp2[m.trainIdx].pt for m in g])
    sel[ratio] = (p1, p2)
    print("razao %.1f: aceitas=%d  (%.2f%% dos keypoints img1; %.2f%% dos pares knn)" % (ratio, len(g), 100 * len(g) / len(kp1), 100 * len(g) / len(matches)))

p1, p2 = sel[0.7]
print("### RANSAC (cv2.FM_RANSAC, parametros padrao do OpenCV) repetido 10x sobre as correspondencias da razao 0.7")
cnt = []
for i in range(10):
    F, mask = cv2.findFundamentalMat(p1, p2, cv2.FM_RANSAC)
    cnt.append(int(mask.sum()))
print("inliers por execucao:", cnt, "| taxa de inliers = %.2f%% (media)" % (100 * np.mean(cnt) / len(p1)))
F, mask = cv2.findFundamentalMat(p1, p2, cv2.FM_RANSAC)
m = mask.ravel() == 1
q1, q2 = p1[m], p2[m]
print("F_ransac (normalizada F[2,2]=1?):\n", F / F[2, 2], "\nposto (valores singulares):", np.linalg.svd(F, compute_uv=False))
e_in = sampson(F.astype(float), q1.astype(float), q2.astype(float))
print("Erro de Sampson (px) nos %d inliers sob F_ransac: %s" % (len(q1), stats(e_in)))
e_out = sampson(F.astype(float), p1[~m].astype(float), p2[~m].astype(float))
print("Erro de Sampson (px) nos %d outliers: %s" % (int((~m).sum()), stats(e_out)))
disp = np.linalg.norm(q2 - q1, axis=1)
print("Deslocamento 2D entre imagens (px), inliers: %s" % stats(disp))

print("### Teste de planaridade (homografia RANSAC 3 px) sobre os inliers")
H, hm = cv2.findHomography(q1, q2, cv2.RANSAC, 3.0)
print("inliers de homografia: %d de %d (%.1f%%)" % (hm.sum(), len(q1), 100 * hm.sum() / len(q1)))

print("### Pontos do testbench (tb_top.vhd / visualize_vhdl_results.py)")
tb1 = np.array([[363.8,138.1],[268.8,129.0],[184.5,216.8],[318.0,288.0],[151.0,129.6],[154.6,143.0],[121.9,221.1],[198.8,135.6]])
tb2 = np.array([[506.3,131.3],[502.5,138.1],[237.5,226.1],[386.9,328.3],[217.3,150.2],[219.7,161.2],[195.3,224.3],[254.2,151.8]])
near = []
for a, b in zip(tb1, tb2):
    dd = np.linalg.norm(q1 - a, axis=1) + np.linalg.norm(q2 - b, axis=1)
    near.append(dd.min())
print("distancia (soma dos dois pontos, px) ao inlier SIFT mais proximo, por ponto:", np.round(near, 2))
print("Erro de Sampson (px) dos 8 pontos sob F_ransac(129 inliers): %s" % stats(sampson(F.astype(float), tb1, tb2)))
F8, _ = cv2.findFundamentalMat(tb1.astype(np.float32), tb2.astype(np.float32), cv2.FM_8POINT)
print("Erro de Sampson (px) dos 8 pontos sob F_8pontos (ajuste exato aos proprios pontos, pouco informativo): %s" % stats(sampson(F8, tb1, tb2)))
print("Erro de Sampson (px) dos 129 inliers sob F_8pontos (estimada so com os 8 pontos): %s" % stats(sampson(F8, q1.astype(float), q2.astype(float))))

print("### F constante do VHDL (SOLVE_SVD) como referencia numerica")
fv = np.array([32768,16384,8192,4096,2048,1024,512,256,128]).reshape(3, 3) / 65536.0
print("F_vhdl:\n", fv, "\nvalores singulares:", np.linalg.svd(fv, compute_uv=False))
print("Erro de Sampson (px) dos 8 pontos sob F_vhdl: %s" % stats(sampson(fv, tb1, tb2)))
print("Erro de Sampson (px) dos 129 inliers sob F_vhdl: %s" % stats(sampson(fv, q1.astype(float), q2.astype(float))))

print("### E = K^T F K : emulacao inteira de Mat3Mul vs simulacao GHDL (probe isolado de EssentialMatrixCalculator)")
K = np.zeros((3, 3), dtype=np.int64)
K[0,0] = K[1,1] = 34406400; K[2,2] = 65536; K[0,2] = 20971520; K[1,2] = 15728640
Fi = np.array([32768,16384,8192,4096,2048,1024,512,256,128], dtype=np.int64).reshape(3, 3)
def wrap32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v >= (1 << 31) else v
def mat3mul(A, B):
    C = np.zeros((3, 3), dtype=np.int64)
    for i in range(3):
        for j in range(3):
            s = sum(int(A[i, k]) * int(B[k, j]) for k in range(3))
            C[i, j] = wrap32(s >> 16)
    return C
Eemu = mat3mul(K.T, mat3mul(Fi, K))
txt = readlog(os.path.join(d, "log_ess_probe.txt"))
vals = {(int(a), int(b)): int(c) for a, b, c in re.findall(r"E\((\d),(\d)\) = (-?\d+)", txt)}
Evhdl = np.array([[vals[(i, j)] for j in range(3)] for i in range(3)], dtype=np.int64)
print("E (GHDL, inteiros Q15.16):\n", Evhdl)
print("emulacao Python == GHDL (9/9 elementos):", bool(np.array_equal(Eemu, Evhdl)), "| elementos iguais:", int((Eemu == Evhdl).sum()))
Eideal = K.T / 65536.0 @ fv @ K / 65536.0
print("E ideal em ponto flutuante (K^T F K):\n", Eideal)
print("E do GHDL convertido para real:\n", Evhdl / 65536.0)
print("elementos |E_ideal| > 32767.99998 (fora da faixa Q15.16):", int((np.abs(Eideal) >= 32768).sum()), "de 9")

print("### OpenCV: pose e triangulacao (mesmo procedimento de visualize_vhdl_results.py) e comparacao com X3D do VHDL")
Kf = np.array([[525, 0, 320], [0, 525, 240], [0, 0, 1]], dtype=np.float64)
E8 = Kf.T @ F8 @ Kf
n, R, t, mk = cv2.recoverPose(E8, tb1.astype(np.float32), tb2.astype(np.float32), Kf)
ang = np.degrees(np.arccos((np.trace(R) - 1) / 2))
print("recoverPose(8 pontos): pontos com cheirality=%d de 8 | angulo de rotacao=%.2f graus | t=%s" % (n, ang, t.ravel()))
W = np.array([[0,-1,0],[1,0,0],[0,0,1]], dtype=float)
Rrel = R @ W.T
print("angulo geodesico entre R_opencv e W (R que o codigo VHDL produziria se os sinais fossem validos): %.2f graus" % np.degrees(np.arccos(np.clip((np.trace(Rrel) - 1) / 2, -1, 1))))
P1 = Kf @ np.hstack((np.eye(3), np.zeros((3, 1)))); P2 = Kf @ np.hstack((R, t))
X = cv2.triangulatePoints(P1, P2, tb1.T, tb2.T); X = X[:3] / X[3]
print("OpenCV Z (camera 1) dos 8 pontos:", np.round(X[2], 3), "| Z>0 em:", int((X[2] > 0).sum()), "de 8")
def reproj(P, Xw, x):
    pr = P @ np.vstack([Xw, np.ones((1, Xw.shape[1]))]); pr = (pr[:2] / pr[2]).T
    return np.linalg.norm(pr - x, axis=1)
print("erro de reprojecao OpenCV (px) img1: %s | img2: %s" % (stats(reproj(P1, X, tb1)), stats(reproj(P2, X, tb2))))
t3 = readlog(os.path.join(d, "log_probe.txt"))
rows = re.findall(r"X3D\((\d+)\) = \[(-?\d+), (-?\d+), (-?\d+), (-?\d+)\]", t3)
V = np.array([[int(a) for a in r[1:]] for r in rows if int(r[0]) < 8], dtype=np.int64)
print("X3D do VHDL (8 primeiros, Q15.16 inteiros):\n", V)
Vf = V[:, :3].T / 65536.0
exp = np.round((np.round(tb1 * 65536) + np.round(tb2 * 65536)) / 2 / 65536, 1)
print("X,Y do VHDL (reais):", np.round(Vf[:2].T, 2).tolist()[:3], "... | Z do VHDL:", np.unique(Vf[2]))
print("X,Y do VHDL == media dos pontos de pixel dos dois pares (tol 0.1 px):", bool(np.allclose(Vf[:2].T, (tb1 + tb2) / 2, atol=0.1)))
print("erro de reprojecao (px) dos X3D do VHDL em img1 com P1=K[I|0]: %s" % stats(reproj(P1, Vf, tb1)))

print("### Quantizacao Q15.16 dos pontos (int(v*65536), como nos scripts)")
allp = np.vstack([q1, q2]).astype(np.float64).ravel()
qq = np.trunc(allp * 65536) / 65536
print("erro max de conversao (px) em %d coordenadas: %.3e (limite teorico 2^-16 = %.3e)" % (len(allp), np.abs(allp - qq).max(), 2 ** -16))
print("maior coordenada |v| = %.1f ; limite Q15.16 = 32767.99998" % np.abs(allp).max())
