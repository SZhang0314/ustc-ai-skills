"""Render the complete bilingual book: front matter + TOC + all chapters + glossary.

Shares esc/inject_terms/render_block with render.py (same directory), so both
single-chapter and whole-book builds handle LaTeX math spans, `equation` blocks,
LaTeX tables and minipage-wrapped figures/tables identically.
"""
import json
import os
import sys

from render import esc, render_block

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')
TEX = os.path.join(ROOT, 'tex')
BUILD = os.path.join(ROOT, 'build')

CHAPTER_TITLES = {
    1: ("Crystal Structure", "晶体结构"),
    2: ("Wave Diffraction and the Reciprocal Lattice", "波衍射与倒易点阵"),
    3: ("Crystal Binding and Elastic Constants", "晶体结合与弹性常量"),
    4: ("Phonons I. Crystal Vibrations", "声子 I. 晶格振动"),
    5: ("Phonons II. Thermal Properties", "声子 II. 热学性质"),
    6: ("Free Electron Fermi Gas", "自由电子费米气体"),
    7: ("Energy Bands", "能带"),
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
    19: ("Noncrystalline Solids", "非晶态固体"),
    20: ("Point Defects", "点缺陷"),
    21: ("Dislocations", "位错"),
    22: ("Alloys", "合金"),
}


def main():
    used = set()
    glossary = {}
    body = []
    for c in range(1, 23):
        p = os.path.join(SRC, f'ch{c:02d}.json')
        data = json.load(open(p, encoding='utf-8'))
        en, zh = CHAPTER_TITLES[c]
        body.append(f'\\chapter{{{esc(zh)}}}')
        body.append(f'\\chaptermark{{{esc(zh)}}}')
        body.append(f'\\noindent{{\\large\\itshape {esc(en)}}}\\par\\bigskip')
        for b in data.get('blocks', []):
            body.append(render_block(b, used, glossary))
        body.append('\\clearpage')

    # glossary sorted by English
    gloss_items = sorted(glossary.items(), key=lambda kv: kv[0][0].lower())
    glines = []
    for (en, zh), note in gloss_items:
        glines.append(f'\\item[\\textbf{{{esc(zh)}}}] \\textit{{{esc(en)}}}——{esc(note)}')

    doc = []
    doc.append('\\documentclass[11pt,openany]{book}')
    doc.append(r'\input{preamble.tex}')
    doc.append('\\begin{document}')
    doc.append('\\frontmatter')
    doc.append('\\pagestyle{empty}')
    doc.append('\\begin{titlepage}')
    doc.append('\\centering\\vspace*{3cm}')
    doc.append('{\\Huge\\bfseries Kittel《固体物理导论》\\par}')
    doc.append('\\vspace{0.6cm}')
    doc.append('{\\LARGE 中英对照注释版\\par}')
    doc.append('\\vspace{0.4cm}')
    doc.append('{\\large Introduction to Solid State Physics\\par}')
    doc.append('{\\large Bilingual Annotated Edition\\par}')
    doc.append('\\vspace{1.2cm}')
    doc.append('{\\large Charles Kittel\\par}')
    doc.append('\\vspace{0.3cm}')
    doc.append('{\\normalsize University of California, Berkeley\\par}')
    doc.append('\\vfill')
    doc.append('{\\small 说明：本版逐段对照呈现英文原文与中文全译，专业术语在首次出现处以脚注给出中英对照与释义，书末附全书术语表。\\par}')
    doc.append('\\end{titlepage}')
    doc.append('\\clearpage')
    doc.append('\\pagestyle{fancy}')
    doc.append('\\tableofcontents')
    doc.append('\\clearpage')
    doc.append('\\mainmatter')
    doc.extend(body)
    doc.append('\\backmatter')
    doc.append('\\chapter*{术语表 / Glossary}')
    doc.append('\\addcontentsline{toc}{chapter}{术语表 / Glossary}')
    doc.append('\\begin{description}[leftmargin=3.2cm,style=nextline]')
    doc.extend(glines)
    doc.append('\\end{description}')
    doc.append('\\end{document}')

    tex = '\n\n'.join(doc)
    path = os.path.join(TEX, 'book.tex')
    open(path, 'w', encoding='utf-8').write(tex)
    import shutil as _sh
    _sh.copyfile(os.path.join(ROOT, 'preamble.tex'),
                 os.path.join(TEX, 'preamble.tex'))
    print('wrote', path)
    print('terms in glossary:', len(gloss_items))
    # compile (twice for TOC)
    for i in range(3):
        r = subprocess_run_book()
        ok = os.path.exists(os.path.join(TEX, 'book.pdf'))
        print(f'pass {i+1}: {"OK" if ok else "FAIL"}')
        if not ok:
            print(r)
            return
    out = os.path.join(BUILD, 'Kittel_固体物理导论_中英对照注释版.pdf')
    import shutil
    shutil.copyfile(os.path.join(TEX, 'book.pdf'), out)
    print('BOOK ->', out)


def subprocess_run_book():
    import subprocess
    r = subprocess.run(['xelatex', '-interaction=nonstopmode', '-halt-on-error',
                        'book.tex'], cwd=TEX, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    tail = '\n'.join((r.stdout or '').splitlines()[-20:])
    return tail


if __name__ == '__main__':
    main()
