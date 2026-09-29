"""Attach extracted figure PNGs to figcap blocks in each chapter JSON (v2).

Matching per chapter:
- Candidates ordered by (page, clip y).
- Each figcap is matched to the first unused CANDIDATE ENTRY whose figure
  number equals the figcap's number; if none matches, the next unused entry
  in order (same png may be shared by several captions when the source shares
  one image between captions like 6a/6b).
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')
FIGS = os.path.join(ROOT, 'figures')

CH_PAGES = {
    1: (98, 140), 2: (141, 164), 3: (165, 210), 4: (211, 229), 5: (230, 254),
    6: (255, 286), 7: (287, 311), 8: (312, 353), 9: (354, 400), 10: (401, 454),
    11: (455, 490), 12: (491, 531), 13: (532, 570), 14: (571, 614),
    15: (615, 652), 16: (653, 688), 17: (689, 737), 18: (738, 789),
    19: (790, 808), 20: (809, 830), 21: (831, 872), 22: (873, 899),
}

NUM_RE = re.compile(r'(?:Figure|FIGURE|Fig\.?)\s*(\d+[A-Za-z]?)', re.I)


def main():
    idx = json.load(open(os.path.join(FIGS, 'figures.json'), encoding='utf-8'))
    for c, (a, b) in CH_PAGES.items():
        cands = sorted([e for e in idx if a <= e['page'] <= b],
                       key=lambda e: (e['page'], float(e['clip'][1])))
        used = set()
        p = os.path.join(SRC, f'ch{c:02d}.json')
        data = json.load(open(p, encoding='utf-8'))
        n_attached = 0
        n_missing = 0
        for blk in data['blocks']:
            if blk.get('type') != 'figcap':
                continue
            en = blk.get('en', '') + ' ' + blk.get('zh', '')
            m = NUM_RE.search(en)
            num = m.group(1) if m else None
            match = None
            if num is not None:
                for j, e in enumerate(cands):
                    if e['num'] == num and j not in used:
                        match = j
                        break
            if match is None:
                for j, e in enumerate(cands):
                    if j not in used:
                        match = j
                        break
            if match is not None:
                used.add(match)
                blk['png'] = cands[match]['png']
                n_attached += 1
            else:
                n_missing += 1
        json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'ch{c:02d}: attached={n_attached} missing={n_missing} cands={len(cands)}')


if __name__ == '__main__':
    main()
