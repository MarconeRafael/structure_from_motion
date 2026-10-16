import re, os, sys
d = sys.argv[1]
def readlog(p):
    b = open(p, "rb").read()
    t = b.decode("utf-16") if b[:2] == b"\xff\xfe" else b.decode("utf-8", "replace")
    return t.replace("\r", "").replace("\n", "")
def tdiv2(v):  # divisao inteira truncando para zero (semantica de numeric_std "/")
    return int(v / 2) if v >= 0 else -int(-v / 2)
for tag, datafile in (("real", "run_points_1.txt"), ("sim", "run_tbdata_1.txt")):
    src = open(os.path.join(d, datafile), encoding="latin-1").read()
    pts = {}
    for arr, i, c, v in re.findall(r"pts([12])_in\((\d+), (\d)\) <= to_signed\((-?\d+), 32\)", src):
        pts[(arr, int(i), int(c))] = int(v)
    log = readlog(os.path.join(d, f"log_tb_probe_{tag}.txt"))
    rows = {int(r[0]): [int(x) for x in r[1:]] for r in re.findall(r"X3D\((\d+)\) = \[(-?\d+), (-?\d+), (-?\d+), (-?\d+)\]", log)}
    ok = 0
    for i in range(8):
        exp = [tdiv2(pts[("1", i, 0)] + pts[("2", i, 0)]), tdiv2(pts[("1", i, 1)] + pts[("2", i, 1)]), 65536, 65536]
        ok += rows[i] == exp
    print(f"{tag}: X3D == [(x1+x2)/2, (y1+y2)/2, 1.0, 1.0] (inteiros Q15.16) em {ok}/8 pontos; X3D(8)={rows[8]}")
