import fitz
import os
import json
import re

SRC = r'E:\USTC-AI\solidphy\Introduction to Solid State Physics (Charles Kittel) (z-library.sk, 1lib.sk, z-lib.sk).pdf'
OUT = r'E:\USTC-AI\solidphy\translation\extracted'

CHAPTER_STARTS = {
    1: 98, 2: 141, 3: 165, 4: 211, 5: 230, 6: 255, 7: 287, 8: 312,
    9: 354, 10: 401, 11: 455, 12: 491, 13: 532, 14: 571, 15: 615,
    16: 653, 17: 689, 18: 738, 19: 790, 20: 809, 21: 831, 22: 873,
}
BOOK_END = 900


def get_pages(doc, a, b):
    return [doc[i].get_text() for i in range(a, b)]


def clean_line(ln):
    ln = ln.replace('\u2003', ' ').replace('\u00a0', ' ')
    ln = re.sub(r'[ \t]+', ' ', ln)
    return ln.rstrip()


def raw_paragraphs(pages):
    """Join page texts, drop headers/footers and page numbers, split on blank lines."""
    lines = []
    for txt in pages:
        for ln in txt.split('\n'):
            lines.append(clean_line(ln))
    paras = []
    cur = []
    for ln in lines:
        if ln.strip() == '':
            if cur:
                paras.append(' '.join(cur).strip())
                cur = []
        else:
            cur.append(ln.strip())
    if cur:
        paras.append(' '.join(cur).strip())
    # Drop trivial page-number / running-head fragments
    cleaned = []
    for p in paras:
        if re.match(r'^\d{1,3}$', p):
            continue
        cleaned.append(p)
    return cleaned


def main():
    doc = fitz.open(SRC)
    os.makedirs(OUT, exist_ok=True)
    starts = sorted(CHAPTER_STARTS.items())
    manifest = []
    for idx, (chnum, start) in enumerate(starts):
        end = starts[idx + 1][1] if idx + 1 < len(starts) else BOOK_END
        pages = get_pages(doc, start, end)
        paras = raw_paragraphs(pages)
        data = {
            'chapter': chnum,
            'page_start': start,
            'page_end': end - 1,
            'n_paras': len(paras),
            'paras': paras,
        }
        with open(os.path.join(OUT, f'ch{chnum:02d}.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        manifest.append({'chapter': chnum, 'page_start': start, 'page_end': end - 1,
                         'n_paras': len(paras)})
        print(f'ch{chnum:02d}: pages {start}-{end-1}  paras={len(paras)}')
    with open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
