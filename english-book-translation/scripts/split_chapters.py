"""Split raw/chNN.txt into raw/chNN_partK.txt with target max size."""
import io
import os
import re

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raw')
PAGES = {
    9: (354, 400), 10: (401, 454), 11: (455, 490), 12: (491, 531),
    13: (532, 570), 14: (571, 614), 15: (615, 652), 16: (653, 688),
    17: (689, 737), 18: (738, 789), 19: (790, 808), 20: (809, 830),
    21: (831, 872), 22: (873, 899),
}
TARGET = 33000


def split(chapter):
    a, b = PAGES[chapter]
    txt = io.open(os.path.join(RAW, f'ch{chapter:02d}.txt'), encoding='utf-8').read()
    pages = re.findall(r'===PAGE (\d+)===\n(.*?)(?====PAGE|\Z)', txt, re.S)
    pages = [(int(n), body) for n, body in pages if a <= int(n) <= b]
    parts = []
    cur, size = [], 0
    for n, body in pages:
        chunk = f'===PAGE {n}===\n{body}'
        if cur and size + len(chunk) > TARGET:
            parts.append(cur)
            cur, size = [], 0
        cur.append(chunk)
        size += len(chunk)
    if cur:
        parts.append(cur)
    for k, pt in enumerate(parts, 1):
        out = os.path.join(RAW, f'ch{chapter:02d}_part{k}.txt')
        io.open(out, 'w', encoding='utf-8').write(''.join(pt))
    print(f'ch{chapter:02d}: {len(parts)} parts sizes={[len("".join(pt)) for pt in parts]}')


if __name__ == '__main__':
    for c in range(9, 23):
        split(c)
