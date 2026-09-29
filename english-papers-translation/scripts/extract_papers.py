# -*- coding: utf-8 -*-
"""Extract each paper's text into raw/pNN.txt (with ===PAGE n=== markers),
then split into <=33KB chunks raw/pNN_partK.txt for parallel translation."""
import fitz
import os
import re
import sys
from papers import PAPERS, OUT, find_pdf

RAW = os.path.join(OUT, 'raw')
MAXBYTES = 33 * 1024


def clean_line(ln):
    ln = ln.replace('\u2003', ' ').replace('\u00a0', ' ')
    ln = ln.replace('\ufb00', 'ff').replace('\ufb01', 'fi').replace('\ufb02', 'fl')
    ln = ln.replace('\ufb03', 'ffi').replace('\ufb04', 'ffl')
    ln = re.sub(r'[ \t]+', ' ', ln)
    return ln.rstrip()


def page_text(page):
    return '\n'.join(clean_line(x) for x in page.get_text().split('\n'))


def split_chunks(text, maxbytes=MAXBYTES):
    """Split raw text into chunks on ===PAGE n=== boundaries, each <= maxbytes."""
    parts = re.split(r'(?m)^(===PAGE \d+===\s*)$', text)
    # parts: [pre, marker, body, marker, body, ...]
    units = []
    if parts and parts[0].strip():
        units.append(parts[0])
    i = 1
    while i < len(parts) - 1:
        units.append(parts[i] + parts[i + 1])
        i += 2
    chunks = []
    cur = ''
    for u in units:
        if cur and len((cur + u).encode('utf-8')) > maxbytes:
            chunks.append(cur)
            cur = u
        else:
            cur += u
    if cur:
        chunks.append(cur)
    return chunks


def main():
    os.makedirs(RAW, exist_ok=True)
    manifest = []
    for prefix, num, year, title in PAPERS:
        pdf = find_pdf(prefix)
        doc = fitz.open(pdf)
        n = doc.page_count
        buf = []
        for i in range(n):
            buf.append(f'===PAGE {i+1}===\n')
            buf.append(page_text(doc[i]))
            buf.append('\n')
        text = ''.join(buf)
        raw_path = os.path.join(RAW, f'p{num:02d}.txt')
        with open(raw_path, 'w', encoding='utf-8') as f:
            f.write(text)
        chunks = split_chunks(text)
        for k, c in enumerate(chunks, 1):
            with open(os.path.join(RAW, f'p{num:02d}_part{k}.txt'), 'w', encoding='utf-8') as f:
                f.write(c)
        manifest.append({'num': num, 'year': year, 'title_en': title,
                         'pages': n, 'raw_bytes': len(text.encode('utf-8')),
                         'n_chunks': len(chunks)})
        print(f'p{num:02d}: {n}p  {manifest[-1]["raw_bytes"]}B  chunks={len(chunks)}  {title[:50]}')
        doc.close()
    import json
    with open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
