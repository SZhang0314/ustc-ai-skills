"""Compile a chapter JSON: render -> xelatex -> move PDF to build/."""
import json
import os
import subprocess
import sys
import glob
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')
TEX = os.path.join(ROOT, 'tex')
BUILD = os.path.join(ROOT, 'build')


def build(chapter):
    name = f'ch{chapter:02d}'
    src = os.path.join(SRC, name + '.json')
    tex = os.path.join(TEX, name + '.tex')
    subprocess.run([sys.executable, os.path.join(ROOT, 'render.py'), src, tex],
                   check=True)
    # ensure preamble is present in tex dir
    shutil.copyfile(os.path.join(ROOT, 'preamble.tex'),
                    os.path.join(TEX, 'preamble.tex'))
    r = subprocess.run(['xelatex', '-interaction=nonstopmode', '-halt-on-error',
                        name + '.tex'], cwd=TEX, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    pdf = os.path.join(TEX, name + '.pdf')
    ok = os.path.exists(pdf)
    if ok:
        shutil.copyfile(pdf, os.path.join(BUILD, name + '.pdf'))
    tail = '\n'.join((r.stdout or '').splitlines()[-6:])
    return ok, tail, pdf


if __name__ == '__main__':
    chapters = [int(a) for a in sys.argv[1:]] or [1]
    for c in chapters:
        ok, tail, pdf = build(c)
        print(f'ch{c:02d}: {"OK" if ok else "FAIL"}\n{tail}\n')
