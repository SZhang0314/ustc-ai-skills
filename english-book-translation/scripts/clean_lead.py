"""Final cleanup: drop leading TOC remnants that precede the first heading."""
import json
import os
import re

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')


def is_remnant(b):
    if b.get('type') != 'para':
        return False
    en = (b.get('en') or '').strip()
    zh = (b.get('zh') or '').strip()
    if len(en) > 120:
        return False
    # single capital letter + text  (e.g. "H  Cooper Pairs")
    if re.match(r'^[A-J]\s{1,3}\S', en) and en.count(' ') < 6:
        return True
    # numbered problem title
    if re.match(r'^\d+[\.、]\s', en) and en.count('.') <= 2:
        return True
    if en in ('PROBLEMS', 'SUMMARY'):
        return True
    # Chinese mirror
    if re.match(r'^[A-J]\s{1,3}\S', zh) and len(zh) < 30:
        return True
    return False


def clean(chapter):
    p = os.path.join(SRC, f'ch{chapter:02d}.json')
    data = json.load(open(p, encoding='utf-8'))
    blocks = data['blocks']
    # only strip if the leading run is remnants and there is a heading later
    i = 0
    while i < len(blocks) and is_remnant(blocks[i]):
        i += 1
    if i >= 3 and i < len(blocks):
        data['blocks'] = blocks[i:]
        json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'ch{chapter:02d}: stripped {i} leading remnants')
    else:
        print(f'ch{chapter:02d}: ok')


if __name__ == '__main__':
    for c in range(1, 23):
        clean(c)
