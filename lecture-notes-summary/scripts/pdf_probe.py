# 探测 PDF：页数、有无文字层（扫描件 textlen=0）、每页图片数、书签目录。
# 用法: python pdf_probe.py <src.pdf> <out.txt>
# 依赖: pip install pymupdf
import fitz, sys, io

doc = fitz.open(sys.argv[1])
out = io.open(sys.argv[2], "w", encoding="utf-8")
out.write("PDF: %s  pages=%d\n" % (sys.argv[1], doc.page_count))
toc = doc.get_toc()
out.write("TOC entries: %d\n" % len(toc))
for t in toc:
    out.write("%s %s  p%s\n" % ("  " * (t[0] - 1), t[1], t[2]))
out.write("\n--- probe sample pages ---\n")
for pno in [0, 1, 2, 10, 50, 100]:
    if pno < doc.page_count:
        t = doc[pno].get_text()
        imgs = doc[pno].get_images()
        out.write("page %d: textlen=%d images=%d %s\n"
                  % (pno, len(t), len(imgs), "(SCANNED, no text layer)" if len(t) == 0 else ""))
out.close()
print("done ->", sys.argv[2])
