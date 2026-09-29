# -*- coding: utf-8 -*-
"""Merge src/pNN_partK.json -> src/pNN.json, preserving block order.
Title comes from the part that has a non-empty title_zh."""
import json
import os
import glob
import re
from papers import PAPERS, OUT

SRC = os.path.join(OUT, 'src')


def main():
    summary = []
    for prefix, num, year, title_en in PAPERS:
        parts = sorted(glob.glob(os.path.join(SRC, f'p{num:02d}_part*.json')),
                       key=lambda p: int(re.search(r'part(\d+)', p).group(1)))
        blocks = []
        title_zh = ''
        for p in parts:
            d = json.load(open(p, encoding='utf-8'))
            blocks.extend(d.get('blocks', []))
            if not title_zh and d.get('title_zh'):
                title_zh = d['title_zh']
        out = {
            'num': num, 'year': year,
            'title_en': title_en, 'title_zh': title_zh,
            'blocks': blocks,
        }
        with open(os.path.join(SRC, f'p{num:02d}.json'), 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        summary.append((num, year, len(parts), len(blocks), title_zh))
    for num, year, np_, nb, tz in summary:
        print(f'p{num:02d} {year} parts={np_} blocks={nb}  zh_len={len(tz)}')


if __name__ == '__main__':
    main()
