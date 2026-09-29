"""Remove leading chapter-table-of-contents noise blocks.

Some raw chapters begin with a chapter TOC page (list of headings + problem
titles). These duplicate headings that appear later in the body. We drop a
leading run of heading/para blocks when it repeats a heading that occurs later.
"""
import json
import os
import re

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')


def is_toc_like(blocks):
    """Return index of first real body block, or 0 if no leading TOC noise.

    A leading run of >=4 blocks that are headings or short numbered
    problem titles, where at least 3 headings also occur later in the
    chapter, is treated as a leftover chapter table of contents.
    """
    n = len(blocks)
    headings = [b for b in blocks if b.get('type') == 'heading']
    if len(headings) < 3:
        return 0
    i = 0
    leading = []
    while i < n:
        b = blocks[i]
        is_head = b.get('type') == 'heading'
        is_prob = (b.get('type') == 'para'
                   and re.match(r'^\s*\d+[\.、]', b.get('en', ''))
                   and len(b.get('en', '')) < 80)
        if is_head or is_prob:
            leading.append(i)
            i += 1
        else:
            break
    if len(leading) < 4:
        return 0
    later = {h.get('zh', '') for h in headings}
    dup = sum(1 for j in leading
              if blocks[j].get('type') == 'heading'
              and blocks[j].get('zh', '') in later)
    if dup >= 3:
        return i
    return 0


def clean(chapter):
    p = os.path.join(SRC, f'ch{chapter:02d}.json')
    data = json.load(open(p, encoding='utf-8'))
    blocks = data['blocks']
    cut = is_toc_like(blocks)
    if cut > 0:
        data['blocks'] = blocks[cut:]
        json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'ch{chapter:02d}: removed {cut} leading TOC blocks')
    else:
        print(f'ch{chapter:02d}: no leading TOC')


if __name__ == '__main__':
    import sys
    args = [int(a) for a in sys.argv[1:]]
    for c in (args or range(1, 23)):
        clean(c)
