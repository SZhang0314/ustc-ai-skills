# 把 PDF 指定页渲染为 PNG（供 OCR 或直接插讲义）。
# 用法: python render_pages.py <src.pdf> <outdir> <page_list>
#   page_list 形如 "0,1,2,10-20"（0 基页码，支持区间）
# 依赖: pip install pymupdf pillow
import fitz, os, sys

src, outdir, pages = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(outdir, exist_ok=True)
plist = []
for part in pages.split(","):
    if "-" in part:
        a, b = part.split("-")
        plist.extend(range(int(a), int(b) + 1))
    else:
        plist.append(int(part))

doc = fitz.open(src)
for p in sorted(set(plist)):
    if p < doc.page_count:
        pix = doc[p].get_pixmap(matrix=fitz.Matrix(2, 2))   # 2x ≈ 144DPI，OCR 够用
        pix.save(os.path.join(outdir, "p%03d.png" % p))
print("rendered", len(set(plist)), "pages ->", outdir)
