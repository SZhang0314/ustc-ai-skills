# -*- coding: utf-8 -*-
"""One-time project setup: copy the skill scripts + AGENT_SPEC into <OUT>.

Usage (from the skill scripts directory, with a papers.py already present in OUT
or set via the SKILL flow):

    python setup_project.py <OUT_DIR>

After this, run the pipeline scripts *from <OUT_DIR>*:
    extract_papers.py -> merge_papers.py -> extract_figures.py ->
    attach_figures.py -> render_collection.py -> prepare_tex.py -> build.bat
"""
import os
import shutil
import sys
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
FILEREF = [
    (os.path.join(HERE, 'extract_papers.py'), 'extract_papers.py'),
    (os.path.join(HERE, 'merge_papers.py'), 'merge_papers.py'),
    (os.path.join(HERE, 'extract_figures.py'), 'extract_figures.py'),
    (os.path.join(HERE, 'attach_figures.py'), 'attach_figures.py'),
    (os.path.join(HERE, 'abstract_detect.py'), 'abstract_detect.py'),
    (os.path.join(HERE, 'normalize.py'), 'normalize.py'),
    (os.path.join(HERE, 'render_collection.py'), 'render_collection.py'),
    (os.path.join(HERE, 'prepare_tex.py'), 'prepare_tex.py'),
    (os.path.join(HERE, 'build.bat'), 'build.bat'),
    (os.path.join(HERE, '..', 'reference', 'AGENT_SPEC.md'), 'AGENT_SPEC.md'),
    (os.path.join(HERE, '..', 'reference', 'preamble.tex'), 'preamble.tex'),
]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for src, name in FILEREF:
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(out, name))
            print('copied', name)
    # papers.py
    pj = os.path.join(out, 'papers.py')
    if not os.path.exists(pj):
        tmpl = os.path.join(HERE, 'papers_meta_template.py')
        shutil.copy2(tmpl, pj)
        print('created papers.py from template (EDIT IT)')


if __name__ == '__main__':
    main()
