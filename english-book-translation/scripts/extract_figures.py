"""
Extract figure regions from the source PDF (v2).

Fixes vs v1:
- Continuation captions (e.g. "Figure 6b" right below "Figure 6a" sharing one
  image) previously produced zero-height regions and were dropped, shifting all
  later matches. Now: if the region between the nearest text block above and
  the caption contains no image/drawing content, the caption reuses the
  previous caption's clip on that page.
- Region top is bounded by the lowest IMAGE/DRAWING bottom above the caption
  when the intervening text is a caption (labels inside figures are drawings).
"""
import fitz
import json
import os
import re

SRC = r'E:\USTC-AI\solidphy\Introduction to Solid State Physics (Charles Kittel) (z-library.sk, 1lib.sk, z-lib.sk).pdf'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'figures')
os.makedirs(OUT, exist_ok=True)

CAP_RE = re.compile(r'^\s*(Figure|FIGURE|Fig\.)\s*(\d+[A-Za-z]?)', re.I)


def content_bboxes(page):
    """All image and drawing bboxes on the page."""
    rects = []
    for im in page.get_image_info():
        r = fitz.Rect(im['bbox'])
        if r.width > 5 and r.height > 5:
            rects.append(r)
    for d in page.get_drawings():
        r = d['rect']
        if r.width > 5 and r.height > 5:
            rects.append(r)
    return rects


def extract():
    doc = fitz.open(SRC)
    index = []
    for pi in range(doc.page_count):
        page = doc[pi]
        blocks = [(fitz.Rect(b[:4]), b[4], b[6]) for b in page.get_text('blocks')]
        captions = [(r, t.strip()) for r, t, typ in blocks
                    if typ == 0 and CAP_RE.match(t or '')]
        if not captions:
            continue
        contents = content_bboxes(page)
        prev_clip = None
        for cap_rect, cap_text in captions:
            num = CAP_RE.match(cap_text).group(2)
            # nearest text-block bottom strictly above this caption
            text_above = [r for r, t, typ in blocks
                          if typ == 0 and r.y1 <= cap_rect.y0 + 2]
            region_top = max((r.y1 for r in text_above), default=70) + 3
            y0, y1 = region_top, cap_rect.y0 - 2
            # clip region for content detection
            zone = fitz.Rect(0, y0, page.rect.width, y1)
            inside = [r for r in contents if r.y0 >= y0 - 6 and r.y1 <= y1 + 6]
            if inside:
                u = inside[0]
                for r in inside[1:]:
                    u |= r
                x0, x1 = u.x0 - 6, u.x1 + 6
                y0, y1 = u.y0 - 6, u.y1 + 6
            else:
                if prev_clip is not None and (y1 - y0) < 60:
                    # continuation caption: shares previous figure
                    index.append({'page': pi, 'num': num, 'caption': cap_text[:120],
                                  'png': prev_clip['png'], 'clip': prev_clip['clip']})
                    continue
                # fall back to text column width
                xs = [r.x0 for r in text_above] + [r.x1 for r in text_above]
                x0, x1 = (min(xs), max(xs)) if xs else (72, 540)
            clip = fitz.Rect(x0, max(y0, 60), x1, min(y1, cap_rect.y0 - 2))
            if clip.width < 20 or clip.height < 20:
                continue
            outname = f'fig_p{pi:04d}_{num}.png'
            pix = page.get_pixmap(clip=clip, dpi=200)
            pix.save(os.path.join(OUT, outname))
            entry = {'page': pi, 'num': num, 'caption': cap_text[:120],
                     'png': outname, 'clip': list(clip)}
            index.append(entry)
            prev_clip = entry
    json.dump(index, open(os.path.join(OUT, 'figures.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('extracted', len(index), 'figure regions')


if __name__ == '__main__':
    extract()
