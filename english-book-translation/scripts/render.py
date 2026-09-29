r"""
Render a bilingual-chapter JSON into a standalone .tex file.

Blocks:
  {"type":"heading","level":1|2,"en":...,"zh":...}
  {"type":"para","en":...,"zh":...,"terms":[{"en","zh","note"}, ...]}
  {"type":"equation","latex":"...","num":"(2.1)","zh_note":"..."}
  {"type":"figcap","en":...,"zh":...,"png":"..."}
  {"type":"table","en":...,"zh":...,"latex":"\\begin{tabular}...\\end{tabular}"}

Formulas are real LaTeX math:
- inline math ($...$, \(...\), $$...$$, \[...\]) inside en/zh text is cut out
  and stored behind placeholders BEFORE escaping, then restored verbatim;
- display equations use the `equation` block (rendered once, shared by both
  languages, with optional \tag{num} for the original equation number).

Anti-overlap: figure and table blocks are wrapped in an unbreakable
`minipage` — if the remaining page space is too small the whole block moves
to the next page, so figure+caption never split and never overlap body text
or the footer. (Never use `samepage`: it forces no-break and can push
content through the footer.)

If `zh` already contains the Chinese term, its first occurrence is replaced
with \\term{...}{...} (once per chapter, with a numbered footnote).
"""
import json
import os
import re
import sys

from normalize import normalize, normalize_math

# Private-use sentinels that never collide with real text.
_PH = '\uE000'
_PHD = '\uE001'  # literal escaped dollar \$

_used_terms = set()


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
    """Escape LaTeX specials in a text field while preserving math spans."""
    macros = []

    def _hide(m):
        macros.append(m.group(1))
        return _PH + str(len(macros) - 1) + _PH

    s = s.replace('\\$', _PHD)      # literal \$ is text, not a math delimiter
    s = _grab_math(s, macros)       # agent-written math spans out first
    s = normalize(s)                # text-mode mapping (may insert $macro$)
    s = re.sub(r'(\$[^$]*\$)', _hide, s)  # protect normalize-introduced macros
    s = s.replace('\\', r'\textbackslash{}')
    for a, b in [('&', r'\&'), ('%', r'\%'), ('#', r'\#'), ('_', r'\_'),
                 ('{', r'\{'), ('}', r'\}'), ('~', r'\textasciitilde{}'),
                 ('^', r'\textasciicircum{}'), ('$', r'\$')]:
        s = s.replace(a, b)
    s = s.replace(_PHD, r'\$')

    def _show(m):
        return macros[int(m.group(1))]
    return re.sub(_PH + r'(\d+)' + _PH, _show, s)


def inject_terms(zh, terms, used, glossary=None):
    """Replace first occurrence of each term's Chinese form with \\term.
    Injected once per chapter (dedup via `used`); optionally records the
    term into `glossary` for the book-end glossary."""
    out = zh
    for t in terms or []:
        zhterm = t.get('zh', '')
        en = t.get('en', '')
        note = t.get('note', '')
        if not zhterm:
            continue
        key = (en, zhterm)
        if glossary is not None and key not in glossary:
            glossary[key] = note
        if key in used:
            continue
        # handle parenthetical forms like 点阵（lattice）
        candidates = [zhterm]
        base = zhterm.split('（')[0].split('(')[0]
        if base and base != zhterm:
            candidates.append(base)
        for cand in candidates:
            idx = out.find(cand)
            if idx != -1:
                macro = f'\\term{{{cand}}}{{{esc(note)}}}'
                out = out[:idx] + macro + out[idx + len(cand):]
                used.add(key)
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


def render_figure(b, figdir='../figures/'):
    """Figure block: unbreakable minipage (image above caption)."""
    img = ''
    if b.get('png'):
        img = ('\\begin{center}\\includegraphics[width=0.86\\linewidth,'
               'height=0.5\\textheight,keepaspectratio]{' + figdir + b['png'] +
               '}\\end{center}\n')
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


def render_para(b, used, glossary=None):
    en = esc(b.get('en', ''))
    # inject terms operate on the *escaped* Chinese text so macros are safe
    zh = inject_terms(esc(b.get('zh', '')), b.get('terms'), used, glossary)
    return ('\\begin{enpara}\n' + en + '\n\\end{enpara}\n'
            '\\begin{zhpara}\n' + zh + '\n\\end{zhpara}\n\\pairrule')


def render_block(b, used=None, glossary=None, figdir='../figures/'):
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
        return render_figure(b, figdir)
    if t == 'table':
        return render_table(b)
    return render_para(b, used if used is not None else _used_terms, glossary)


def render_chapter(data, outpath):
    _used_terms.clear()
    parts = []
    parts.append('\\documentclass[11pt,openany]{book}')
    parts.append(r'\input{preamble.tex}')
    zh_title = esc(data.get('title_zh', ''))
    en_title = esc(data.get('title_en', ''))
    parts.append('\\begin{document}')
    parts.append(f'\\chapter{{{zh_title}}}')
    parts.append('\\thispagestyle{fancy}')
    parts.append(f'\\noindent{{\\large\\itshape {en_title}}}\\par\\bigskip')
    for b in data.get('blocks', []):
        parts.append(render_block(b))
    parts.append('\\end{document}')
    tex = '\n\n'.join(parts)
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(tex)
    return outpath


if __name__ == '__main__':
    inp = sys.argv[1]
    outp = sys.argv[2]
    with open(inp, encoding='utf-8') as f:
        data = json.load(f)
    render_chapter(data, outp)
    print('rendered', outp)
