# 批量 OCR 一组 PNG，输出带页标记的 UTF-8 文本。
# 用法: python ocr_batch.py <png_dir> <out.txt> <start_page> <end_page>
#   页码按 render_pages.py 的命名 p%03d.png（0 基）
# 依赖: pip install rapidocr-onnxruntime pillow
# 注意：tesseract 未装时用 RapidOCR（对中文教材扫描件效果好，无需额外语言包）
import io, os, sys
from rapidocr_onnxruntime import RapidOCR

engine = RapidOCR()
indir, outfile = sys.argv[1], sys.argv[2]
start, end = int(sys.argv[3]), int(sys.argv[4])

out = io.open(outfile, "w", encoding="utf-8")
for p in range(start, end + 1):
    fn = os.path.join(indir, "p%03d.png" % p)
    if not os.path.exists(fn):
        out.write("\n===== PAGE %d (missing) =====\n" % p)
        continue
    res, _ = engine(fn)
    out.write("\n===== PAGE %d =====\n" % p)
    if res:
        for line in res:
            out.write(line[1] + "\n")
    out.flush()
    print("ocr page", p, "lines", len(res) if res else 0)
out.close()
print("DONE ->", outfile)
