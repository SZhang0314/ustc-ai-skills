# -*- coding: utf-8 -*-
"""Render the merged paper JSONs into a single collection .tex with bilingual TOC."""
import json
import os
import re
import sys
from papers import PAPERS, OUT

try:
    from papers import COLLECTION_TITLE, COLLECTION_TITLE_EN, COLLECTION_SUBTITLE
except ImportError:
    COLLECTION_TITLE = '英文文献中英对照集'
    COLLECTION_TITLE_EN = 'A Bilingual Collection of Key Papers'
    COLLECTION_SUBTITLE = '中英逐段对照 · 术语注释版'

SRC = os.path.join(OUT, 'src')
TEXDIR = os.path.join(OUT, 'tex')


from normalize import normalize, normalize_math
from abstract_detect import detect as detect_abstract

# Sentinels won't collide with normal text.
_PH = '\uE000'
_PHD = '\uE001'  # literal escaped dollar \$


def _grab_math(s, macros):
    """Cut math spans out of `s`, storing them in `macros` for later
    restoration. Each span's inner content is math-mode-normalized.
    Literal escaped dollars (\\$) must be pre-replaced with _PHD first."""
    def _store(open_d, inner, close_d):
        macros.append(open_d + normalize_math(inner) + close_d)
        return _PH + str(len(macros) - 1) + _PH

    s = re.sub(r'\\\[(.*?)\\\]',
               lambda m: _store(r'\[', m.group(1), r'\]'), s, flags=re.S)
    s = re.sub(r'\\\((.*?)\\\)',
               lambda m: _store(r'\(', m.group(1), r'\)'), s, flags=re.S)
    s = re.sub(r'(?<!\\)\$\$(.*?)\$\$',
               lambda m: _store('$$', m.group(1), '$$'), s, flags=re.S)
    s = re.sub(r'(?<!\\)\$([^$]+?)\$',
               lambda m: _store('$', m.group(1), '$'), s, flags=re.S)
    return s


def esc(s):
    # All math spans (agent-written and normalize-introduced) are stored behind
    # placeholders, so the escaping below cannot mangle their backslashes.
    macros = []

    def _hide(m):
        macros.append(m.group(1))
        return _PH + str(len(macros) - 1) + _PH

    s = s.replace('\\$', _PHD)   # literal \$ is text, not a math delimiter
    s = _grab_math(s, macros)    # agent-written math spans out first
    s = normalize(s)             # text-mode mapping (may insert $macro$)
    s = re.sub(r'(\$[^$]*\$)', _hide, s)  # protect normalize-introduced macros
    s = s.replace('\\', r'\textbackslash{}')
    for a, b in [('&', r'\&'), ('%', r'\%'), ('#', r'\#'), ('_', r'\_'),
                 ('{', r'\{'), ('}', r'\}'), ('~', r'\textasciitilde{}'),
                 ('^', r'\textasciicircum{}'), ('$', r'\$')]:
        s = s.replace(a, b)
    s = s.replace(_PHD, r'\$')

    def _show(m):
        return macros[int(m.group(1))]
    s = re.sub(_PH + r'(\d+)' + _PH, _show, s)
    return s


_used = set()


def inject_terms(zh, terms, used):
    out = zh
    for t in terms or []:
        zhterm = t.get('zh', '')
        note = t.get('note', '')
        if not zhterm:
            continue
        cands = [zhterm]
        base = re.split(r'[（(]', zhterm)[0]
        if base and base != zhterm:
            cands.append(base)
        for cand in cands:
            idx = out.find(cand)
            if idx != -1:
                macro = f'\\term{{{cand}}}{{{esc(note)}}}'
                out = out[:idx] + macro + out[idx + len(cand):]
                used.add(zhterm)
                break
    return out


_EQ_ENV_RE = re.compile(
    r'\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|eqnarray\*?|displaymath)\}')


def render_equation(b):
    """Display equation block: real LaTeX math, rendered once (language-neutral)."""
    latex = (b.get('latex') or b.get('en') or '').strip()
    if not latex:
        return ''
    latex = normalize_math(latex)
    num = (b.get('num') or '').strip()
    if not _EQ_ENV_RE.match(latex):
        latex = ('\\begin{equation*}' + latex +
                 ('\\tag{' + esc(num) + '}' if num else '') + '\\end{equation*}')
    out = '\\par\\medskip\n' + latex + '\n\\par\\medskip'
    note = (b.get('zh_note') or b.get('zh') or '').strip()
    if re.search(r'[\u4e00-\u9fff]', note):
        out += '\\noindent{\\small\\color{capColor}\\kai ' + esc(note) + '}\\par'
    out += '\\smallskip\\pairrule'
    return out


def render_figure(b):
    """Figure block: unbreakable minipage (image above caption), never overlaps."""
    img = ''
    if b.get('png'):
        img = ('\\begin{center}\\includegraphics[width=0.9\\linewidth,'
               'height=0.5\\textheight,keepaspectratio]{figures/'
               + b['png'] + '}\\end{center}\n')
    return ('\\par\\smallskip\\noindent\\begin{minipage}{\\linewidth}\n' + img +
            '\\begin{zhpara}\\figcap{【图】' + esc(b.get('zh', '')) + '}{' +
            esc(b.get('en', '')) + '}\\end{zhpara}\n\\end{minipage}\n'
            '\\par\\smallskip\\pairrule')


def render_table(b):
    """Table block: LaTeX tabular (booktabs), auto-shrunk to the text width."""
    latex = (b.get('latex') or '').strip()
    cap = ('\\begin{zhpara}\\figcap{【表】' + esc(b.get('zh', '')) + '}{' +
           esc(b.get('en', '')) + '}\\end{zhpara}')
    if not latex:
        return cap + '\n\\pairrule'
    is_long = 'longtable' in latex
    if (not is_long and '\\begin{tabular' in latex
            and 'resizebox' not in latex):
        body = '\\adjustbox{max width=\\linewidth}{' + latex + '}'
    else:
        body = latex
    if is_long:
        # longtable breaks across pages itself; never put it inside a box
        return ('\\par\\medskip\n' + cap + '\n\\par\\smallskip\n' + body +
                '\n\\par\\medskip\\pairrule')
    return ('\\par\\smallskip\\noindent\\begin{minipage}{\\linewidth}\n' + cap +
            '\n\\begin{center}\\small\n' + body +
            '\\end{center}\n\\end{minipage}\n\\par\\smallskip\\pairrule')


def render_block(b):
    t = b.get('type', 'para')
    if t == 'heading':
        lvl = b.get('level', 1)
        zh = esc(b.get('zh', ''))
        en = esc(b.get('en', ''))
        if lvl == 1:
            return (f'\\section{{{zh}}}\n'
                    f'\\noindent{{\\small\\itshape（{en}）}}\\par')
        return f'\\subsection{{{zh}}}\n'
    if t == 'equation':
        return render_equation(b)
    if t == 'figcap':
        return render_figure(b)
    if t == 'table':
        return render_table(b)
    en = esc(b.get('en', ''))
    zh = inject_terms(esc(b.get('zh', '')), b.get('terms'), _used)
    return ('\\begin{enpara}\n' + en + '\n\\end{enpara}\n'
            '\\begin{zhpara}\n' + zh + '\n\\end{zhpara}\n\\pairrule')


def main():
    os.makedirs(TEXDIR, exist_ok=True)
    years = [p[2] for p in PAPERS]
    ylo, yhi = min(years), max(years)
    n_papers = len(PAPERS)
    body = []
    body.append('\\documentclass[11pt,openany]{book}')
    body.append(r'\input{preamble.tex}')
    body.append(r'\begin{document}')
    body.append(r'\frontmatter')
    body.append(r'\pagestyle{empty}')
    body.append(r'\begin{titlepage}\centering')
    body.append('{\\Huge\\bfseries\\sffamily ' + esc(COLLECTION_TITLE) + '\\par}')
    body.append(r'\vspace{18pt}')
    body.append('{\\Large\\itshape ' + esc(COLLECTION_TITLE_EN) + '\\par}')
    body.append(r'\vspace{30pt}')
    body.append('{\\large 共 %d 篇文献 · 按发表年份排序（%d--%d）\\par}' % (n_papers, ylo, yhi))
    body.append(r'\vspace{40pt}')
    body.append('{\\large ' + esc(COLLECTION_SUBTITLE) + '\\par}')
    body.append(r'\vfill')
    body.append(r'{\normalsize\today\par}')
    body.append(r'\end{titlepage}')
    # TOC
    body.append(r'\cleardoublepage')
    body.append(r'\pagestyle{fancy}')
    body.append(r'\renewcommand{\contentsname}{目\ 录}')
    body.append(r'\tableofcontents')
    body.append(r'\cleardoublepage')
    body.append(r'\mainmatter')
    # papers
    for prefix, num, year, title_en in PAPERS:
        d = json.load(open(os.path.join(SRC, f'p{num:02d}.json'), encoding='utf-8'))
        _used.clear()
        zh = esc(d.get('title_zh', ''))
        en = esc(title_en)
        # TOC entry: Chinese title, then italic English title, then year.
        rich = (zh + r'\protect\\ {\normalfont\itshape\footnotesize ' + en +
                r'}\quad(\textbf{' + str(year) + r'})')
        plain = f'{d.get("title_zh","")} ({en}) ({year})'
        toc = r'\texorpdfstring{' + rich + '}{' + plain + '}'
        body.append(f'\\chapter[{toc}]{{{zh}}}')
        # Header uses \leftmark; truncate long titles so the header never
        # overflows the text width and overlaps other content.
        mark = d.get('title_zh', '') or title_en
        if len(mark) > 40:
            mark = mark[:40] + '…'
        body.append('\\markboth{' + esc(mark) + '}{}')
        body.append(f'\\noindent{{\\large\\itshape {en}}}\\par')
        body.append(f'\\noindent{{\\small\\textcolor{{capColor}}{{发表年份：{year}\\quad 文献编号：{num:02d}}}}}\\par\\bigskip')
        abs_idx, how = detect_abstract(d)
        for bi, b in enumerate(d.get('blocks', [])):
            if bi == abs_idx:
                body.append(r'\abstracthead')
            if bi == abs_idx and how == 'inline':
                b = dict(b)
                b['en'] = re.sub(r'^\s*[Aa]bstract\s*:?\s*', '', b.get('en', ''))
                b['zh'] = re.sub(r'^\s*摘\s*要\s*[:：]?\s*', '', b.get('zh', ''))
            body.append(render_block(b))
    body.append(r'\end{document}')
    tex = '\n\n'.join(body)
    out = os.path.join(TEXDIR, 'collection.tex')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(tex)
    print('WROTE', out, 'chars=', len(tex))


if __name__ == '__main__':
    main()
