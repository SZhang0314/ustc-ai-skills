"""Merge chNN_partM.json files into src/chNN.json."""
import json
import os
import sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')

TITLES = {
    3: ("Crystal Binding and Elastic Constants", "晶体结合与弹性常量"),
    8: ("Semiconductor Crystals", "半导体晶体"),
    9: ("Fermi Surfaces and Metals", "费米面与金属"),
    10: ("Superconductivity", "超导电性"),
    11: ("Diamagnetism and Paramagnetism", "抗磁性与顺磁性"),
    12: ("Ferromagnetism and Antiferromagnetism", "铁磁性与反铁磁性"),
    13: ("Magnetic Resonance", "磁共振"),
    14: ("Dielectrics and Ferroelectrics", "介电体与铁电体"),
    15: ("Plasmons, Polaritons, and Polarons", "等离激元、极化激元与极化子"),
    16: ("Optical Processes and Excitons", "光学过程与激子"),
    17: ("Surface and Interface Physics", "表面与界面物理"),
    18: ("Nanostructures", "纳米结构"),
    21: ("Dislocations", "位错"),
}


def merge(chapter):
    parts = []
    i = 1
    while True:
        p = os.path.join(SRC, f'ch{chapter:02d}_part{i}.json')
        if not os.path.exists(p):
            break
        parts.append(json.load(open(p, encoding='utf-8')))
        i += 1
    if not parts:
        raise SystemExit(f'no parts for ch{chapter}')
    blocks = []
    for pt in parts:
        blocks.extend(pt.get('blocks', []))
    en, zh = TITLES.get(chapter, ('', ''))
    data = {'chapter': chapter, 'title_en': en, 'title_zh': zh, 'blocks': blocks}
    out = os.path.join(SRC, f'ch{chapter:02d}.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f'ch{chapter:02d}: merged {i-1} parts, {len(blocks)} blocks -> {out}')


if __name__ == '__main__':
    for c in [int(a) for a in sys.argv[1:]]:
        merge(c)
