import cv2, numpy as np, hashlib, os, sys
from PIL import Image, ExifTags

root = sys.argv[1]
paths = [os.path.join(root, "images", n) for n in ("img1.jpeg", "img2.jpeg")]
grays = []
for p in paths:
    print("==", os.path.basename(p))
    print("  tamanho_bytes:", os.path.getsize(p))
    print("  sha256:", hashlib.sha256(open(p, "rb").read()).hexdigest())
    im = Image.open(p)
    print("  PIL formato:", im.format, "modo:", im.mode, "size(WxH):", im.size, "info_keys:", sorted(k for k in im.info.keys()))
    print("  dpi:", im.info.get("dpi"), "jfif:", im.info.get("jfif"), "progressive:", im.info.get("progressive"))
    ex = im.getexif()
    print("  EXIF tags:", {ExifTags.TAGS.get(k, k): v for k, v in ex.items()} if ex else "nenhum")
    q = getattr(im, "quantization", None)
    print("  tabelas_quantizacao:", None if q is None else len(q))
    c = cv2.imread(p)
    g = cv2.imread(p, 0)
    print("  cv2 BGR shape:", c.shape, "dtype:", c.dtype, "| gray shape:", g.shape)
    print("  gray min/max/mean/std: %d %d %.2f %.2f" % (g.min(), g.max(), g.mean(), g.std()))
    print("  var_Laplaciano (nitidez): %.2f" % cv2.Laplacian(g, cv2.CV_64F).var())
    b, gg, r = [c[:, :, i].astype(int) for i in range(3)]
    print("  max|B-G|, max|G-R| (0 => cinza puro): %d %d" % (np.abs(b - gg).max(), np.abs(gg - r).max()))
    grays.append(g)
a, b = grays
print("== comparacao")
print("  mesmas dimensoes:", a.shape == b.shape)
print("  MAE pixel a pixel (gray): %.2f" % np.abs(a.astype(float) - b.astype(float)).mean())
ha = cv2.calcHist([a], [0], None, [256], [0, 256]); hb = cv2.calcHist([b], [0], None, [256], [0, 256])
print("  correlacao de histogramas: %.4f" % cv2.compareHist(ha, hb, cv2.HISTCMP_CORREL))
print("  opencv", cv2.__version__)
