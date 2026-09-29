# -*- coding: utf-8 -*-
"""Extract figure regions from each paper PDF (nearest-cluster method).

For each caption block we take the graphic clusters (drawings/images) on the
page and match the caption to the nearest cluster, then grow the region by
union-ing clusters in spatial contact (multi-panel figures).  Captions that are
actually in-text references (no graphics nearby) are rejected.
"""
import fitz
import os
import re
import json
from papers import PAPERS, OUT, find_pdf

FIG_DIR = os.path.join(OUT, 'figures')
os.makedirs(FIG_DIR, exist_ok=True)

CAP_RE = re.compile(r'^\s*(FIG\.?|Figure|FIGURE|TABLE|Table)\s*([IVXLC]+|\d+)[A-Za-z]?', re.I)
# in-text references such as "Figure 1a depicts ..." that are body sentences
BODY_REF = re.compile(r'^\s*(Fig(?:ure|\.)?)\s*\d+[A-Za-z]?\s+'
                      r'(depicts|shows|is|are|was|were|illustrates|presents|reports|gives|'
                      r'displays|summarizes|indicates|reveals)', re.I)


def close(a, b, gap=24):
    return not (a.x1 + gap < b.x0 or b.x1 + gap < a.x0 or
                a.y1 + gap < b.y0 or b.y1 + gap < a.y0)


def cluster(rects):
    rects = list(rects)
    parent = list(range(len(rects)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            if close(rects[i], rects[j]):
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[rj] = ri
    groups = {}
    for i in range(len(rects)):
        groups.setdefault(find(i), []).append(rects[i])
    out = []
    for g in groups.values():
        u = g[0]
        for r in g[1:]:
            u |= r
        out.append(u)
    return out


def page_clusters(page):
    rects = []
    for im in page.get_image_info():
        r = fitz.Rect(im['bbox'])
        if r.width > 6 and r.height > 6:
            rects.append(r)
    for d in page.get_drawings():
        r = d['rect']
        if r.width > 3 and r.height > 3:
            rects.append(r)
    cl = [r for r in cluster(rects) if r.width > 30 and r.height > 24]
    return cl


def page_is_wide(page):
    """True for large-format single-column journals (Nature/Science style)."""
    tb = [fitz.Rect(b[:4]) for b in page.get_text('blocks') if (b[4] or '').strip()]
    if not tb:
        return False
    wide = [r for r in tb if r.width > 0.55 * page.rect.width]
    return len(wide) >= max(2, 0.3 * len(tb))


def dist(a, b):
    dx = max(a.x0 - b.x1, b.x0 - a.x1, 0)
    dy = max(a.y0 - b.y1, b.y0 - a.y1, 0)
    return (dx * dx + dy * dy) ** 0.5


def main():
    manifest = {}
    total = 0
    for prefix, num, year, title in PAPERS:
        doc = fitz.open(find_pdf(prefix))
        entries = []
        for pi in range(doc.page_count):
            page = doc[pi]
            caps = [(fitz.Rect(b[:4]), (b[4] or '').strip())
                    for b in page.get_text('blocks')
                    if (b[4] or '').strip()
                    and CAP_RE.match(b[4])
                    and not BODY_REF.match(b[4])]
            if not caps:
                continue
            cl = page_clusters(page)
            if not cl:
                continue
            wide_page = page_is_wide(page)
            used = set()
            for cap_rect, cap_text in caps:
                best, bestd = None, 1e9
                for k, r in enumerate(cl):
                    if k in used:
                        continue
                    d = dist(r, cap_rect)
                    if d < bestd:
                        bestd, best = d, k
                if best is None:
                    for k, r in enumerate(cl):
                        d = dist(r, cap_rect)
                        if d < bestd:
                            bestd, best = d, k
                if best is None or bestd > 320:
                    continue
                # grow by contact
                group = [best]
                u = fitz.Rect(cl[best])
                changed = True
                while changed:
                    changed = False
                    for k, r in enumerate(cl):
                        if k in group:
                            continue
                        if close(r, u, gap=22):
                            group.append(k)
                            u |= r
                            changed = True
                for k in group:
                    used.add(k)
                clip = fitz.Rect(u.x0 - 4, u.y0 - 4, u.x1 + 4, u.y1 + 4)
                # Same-row multi-panel gather: panels of one full-width figure
                # row sit side by side above the caption. Absorb every cluster
                # whose vertical span overlaps the current region and that lies
                # above the caption -- unless that cluster has its OWN caption
                # just below it (i.e. it belongs to a different figure).
                def owns_caption(r):
                    for c, _ in caps:
                        if abs(c.y0 - cap_rect.y0) < 2 and abs(c.x0 - cap_rect.x0) < 2:
                            continue
                        cx = (c.x0 + c.x1) / 2
                        if r.x0 - 6 <= cx <= r.x1 + 6 and 0 <= c.y0 - r.y1 < 70:
                            return True
                    return False

                vb0, vb1 = u.y0 - 20, u.y1 + 20
                for k, r in enumerate(cl):
                    if k in group:
                        continue
                    if r.y1 > cap_rect.y0 + 6:
                        continue
                    if owns_caption(r):
                        continue
                    ov = min(r.y1, vb1) - max(r.y0, vb0)
                    if ov > 0.5 * min(r.height, vb1 - vb0):
                        group.append(k)
                        u |= r
                clip = fitz.Rect(u.x0 - 4, u.y0 - 4, u.x1 + 4, u.y1 + 4)
                # Wide single-column journals: a figure is a full-width band
                # above its caption; gather all clusters that share the band.
                cap_wide = cap_rect.width > 0.5 * page.rect.width
                if (wide_page or cap_wide) and u.width < 0.7 * page.rect.width:
                    band0, band1 = u.y0 - 25, u.y1 + 25
                    xlo, xhi = u.x0, u.x1
                    for k, r in enumerate(cl):
                        if r.y1 < band0 or r.y0 > band1:
                            continue
                        ov = min(r.y1, band1) - max(r.y0, band0)
                        if ov > 0.4 * min(r.height, band1 - band0):
                            xlo = min(xlo, r.x0)
                            xhi = max(xhi, r.x1)
                    clip = fitz.Rect(xlo - 4, u.y0 - 4, xhi + 4, u.y1 + 4)
                clip &= page.rect
                if clip.width < 24 or clip.height < 18:
                    continue
                outname = f'p{num:02d}_pg{pi:02d}_{len(entries):02d}.png'
                page.get_pixmap(clip=clip, dpi=200).save(os.path.join(FIG_DIR, outname))
                entries.append({'page': pi, 'label': CAP_RE.match(cap_text).group(0).strip(),
                                'caption': cap_text[:80], 'png': outname,
                                'clip': [clip.x0, clip.y0, clip.x1, clip.y1]})
        manifest[f'p{num:02d}'] = entries
        total += len(entries)
        print(f'p{num:02d}: {len(entries)}')
        doc.close()
    json.dump(manifest, open(os.path.join(FIG_DIR, 'figures.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('TOTAL', total)


if __name__ == '__main__':
    main()
