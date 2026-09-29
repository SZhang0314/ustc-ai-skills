# -*- coding: utf-8 -*-
"""Attach extracted figure PNGs to figcap blocks in each paper JSON.

Matching rules per paper:
  * Extract the figure label + number from the figcap's English text.
  * Extracted figure entries are ordered by (page, clip.y).
  * Match by figure number when possible ("FIG. 2" -> entry whose label has 2);
    otherwise fall back to the next unused entry in order.
  * A figcap without a number (continuation caption) reuses the previous match.
"""
import json
import os
import re
import glob
from papers import OUT

SRC = os.path.join(OUT, 'src')
FIGS = os.path.join(OUT, 'figures')
NUM_RE = re.compile(r'(?:FIG\.?|Figure|FIGURE)\s*([IVXLC]+|\d+)', re.I)


def roman(s):
    vals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
    s = s.upper()
    tot = prev = 0
    for ch in reversed(s):
        v = vals.get(ch, 0)
        tot += v if v >= prev else -v
        prev = max(prev, v)
    return tot


def label_num(text):
    m = NUM_RE.search(text or '')
    if not m:
        return None
    tok = m.group(1)
    return int(tok) if tok.isdigit() else roman(tok)


def main():
    figures = json.load(open(os.path.join(FIGS, 'figures.json'), encoding='utf-8'))
    for path in sorted(glob.glob(os.path.join(SRC, 'p??.json'))):
        data = json.load(open(path, encoding='utf-8'))
        key = f'p{data["num"]:02d}'
        entries = sorted(figures.get(key, []),
                         key=lambda e: (e['page'], e['clip'][1]))
        for e in entries:
            e['num'] = label_num(e.get('label', '')) or label_num(e.get('caption', ''))

        used = set()
        last_png = None
        n_att = 0
        n_miss = 0
        for blk in data['blocks']:
            if blk.get('type') != 'figcap':
                continue
            num = label_num(blk.get('en', ''))
            idx = None
            if num is not None:
                for j, e in enumerate(entries):
                    if e['num'] == num and j not in used:
                        idx = j
                        break
            if idx is None:
                for j in range(len(entries)):
                    if j not in used:
                        idx = j
                        break
            if idx is not None:
                e = entries[idx]
                blk['png'] = e['png']
                used.add(idx)
                last_png = e['png']
                n_att += 1
            elif last_png is not None:
                blk['png'] = last_png   # continuation caption shares image
                n_att += 1
            else:
                n_miss += 1
        json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'{key}: captions_attached={n_att} missing={n_miss} figures_avail={len(entries)}')


if __name__ == '__main__':
    main()
