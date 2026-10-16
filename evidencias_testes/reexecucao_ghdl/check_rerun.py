import re, os, sys
l = sys.argv[1]
rd = lambda n: open(os.path.join(l, n), encoding="utf-8", errors="replace").read().replace("\r", "")

def vals(txt, name, n):
    out = re.findall(name + r"\(([\d,]+)\) = ([^\n]*)", txt)
    return out

def meta_summary(txt, name):
    items = re.findall(r"\b" + name + r"\((?:\d,\d|\d)\) = (META\[([UX]+)\]|-?\d+)", txt)
    kinds = {}
    for full, m in items:
        k = ("all_" + set(m).pop() if m and len(set(m)) == 1 and len(m) == 32 else ("meta_mixed" if m else "defined"))
        kinds[k] = kinds.get(k, 0) + 1
    return kinds

t = rd("run_tb_probe.txt").replace("\n", "")
t = re.sub(r"\s+", " ", t)
# o terminal quebra linhas ao redirecionar? cmd nao quebra, mas normalizamos mesmo assim
for nm in ("F", "E", "R", "t"):
    print("probe 1:", nm, meta_summary(t, nm))
for tag in ("tb_probe_real", "tb_probe_sim"):
    vhd = open(os.path.join(l, "..", "repo", "tb", tag + ".vhd"), encoding="latin-1").read()
    pts = {(a, int(i), int(c)): int(v) for a, i, c, v in re.findall(r"pts([12])_in\((\d+), (\d)\) <= to_signed\((-?\d+), 32\)", vhd)}
    log = re.sub(r"\s+", " ", rd("run_" + tag + ".txt").replace("\n", ""))
    rows = {int(a): [int(x) for x in (b, c, d, e)] for a, b, c, d, e in re.findall(r"X3D\((\d+)\) = \[(-?\d+), (-?\d+), (-?\d+), (-?\d+)\]", log)}
    td = lambda v: int(v / 2) if v >= 0 else -int(-v / 2)
    ok = sum(rows[i] == [td(pts[("1", i, 0)] + pts[("2", i, 0)]), td(pts[("1", i, 1)] + pts[("2", i, 1)]), 65536, 65536] for i in range(8))
    print(tag, "X3D == ((x1+x2)/2, (y1+y2)/2, 1, 1):", ok, "/ 8 | X3D(8) =", rows[8], "| F meta:", meta_summary(log, "F"), "| E meta:", meta_summary(log, "E"))

# probe2: segunda execucao
t2 = re.sub(r"\s+", " ", rd("run_tb_probe2.txt").replace("\n", ""))
run2 = t2[t2.find("RUN2"):]
for nm in ("F", "E", "R", "t"):
    print("probe 2 (RUN2):", nm, meta_summary(re.sub(r"RUN2 ", "", run2), nm))

# E isolado vs emulacao inteira
K = [[34406400, 0, 20971520], [0, 34406400, 15728640], [0, 0, 65536]]
F = [[32768, 16384, 8192], [4096, 2048, 1024], [512, 256, 128]]
def w32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v >= (1 << 31) else v
def mm(A, B):
    return [[w32(sum(A[i][k] * B[k][j] for k in range(3)) >> 16) for j in range(3)] for i in range(3)]
KT = [[K[j][i] for j in range(3)] for i in range(3)]
Emu = mm(KT, mm(F, K))
te = re.sub(r"\s+", " ", rd("run_tb_ess_probe.txt").replace("\n", ""))
ev = {(int(a), int(b)): int(c) for a, b, c in re.findall(r"E\((\d),(\d)\) = (-?\d+)", te)}
ok = sum(ev[(i, j)] == Emu[i][j] for i in range(3) for j in range(3))
print("E isolado GHDL == emulacao inteira:", ok, "/ 9")
print("E(0,0) GHDL =", ev[(0, 0)], "=", ev[(0, 0)] / 65536, "| ideal =", 525 * 525 * 0.5)
print("elementos |E ideal| >= 32768:", sum(abs(sum(KT[i][a] / 65536 * F[a][b] / 65536 * K[b][j] / 65536 for a in range(3) for b in range(3))) >= 32768 for i in range(3) for j in range(3)))
