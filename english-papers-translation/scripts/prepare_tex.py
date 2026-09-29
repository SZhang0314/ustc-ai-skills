# -*- coding: utf-8 -*-
"""Copy preamble.tex and figure PNGs into <OUT>/tex before compiling.

Run this once after render_collection.py, then run build.bat inside tex/.
"""
import os
import shutil
import glob
from papers import OUT

TEXDIR = os.path.join(OUT, 'tex')
FIGDIR = os.path.join(OUT, 'figures')
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    os.makedirs(os.path.join(TEXDIR, 'figures'), exist_ok=True)
    # preamble (prefer a project-local copy in OUT, else the skill's reference copy)
    local = os.path.join(OUT, 'preamble.tex')
    if os.path.exists(local):
        shutil.copy2(local, os.path.join(TEXDIR, 'preamble.tex'))
        print('preamble from', local)
    else:
        src = os.path.join(HERE, '..', 'reference', 'preamble.tex')
        shutil.copy2(src, os.path.join(TEXDIR, 'preamble.tex'))
        print('preamble from skill reference')
    # figures
    n = 0
    for png in glob.glob(os.path.join(FIGDIR, '*.png')):
        shutil.copy2(png, os.path.join(TEXDIR, 'figures', os.path.basename(png)))
        n += 1
    print('copied', n, 'figures into tex/figures')


if __name__ == '__main__':
    main()
