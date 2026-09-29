#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build a scientific-paper-format lab report in .docx / .tex / .pdf from one JSON.

Usage:
    python build_report.py --input report.json --outdir output \
        --formats docx,pdf,tex --title "实验题目"

The single input JSON (see reference/report_schema.md) is the only content
source, so all three outputs stay identical in content and layout.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

# ---------------------------------------------------------------------------
# JSON -> intermediate "blocks" so all three writers share content parsing.
# ---------------------------------------------------------------------------

MATH_RE = re.compile(r"(\$\$.*?\$\$|\$.*?\$)", re.S)


def split_math(text):
    """Split a paragraph into [('text', s) | ('math', latex_body), ...]."""
    parts = []
    for tok in MATH_RE.split(text):
        if not tok:
            continue
        if tok.startswith("$$") and tok.endswith("$$"):
            parts.append(("display", tok[2:-2].strip()))
        elif tok.startswith("$") and tok.endswith("$"):
            parts.append(("inline", tok[1:-1].strip()))
        else:
            parts.append(("text", tok))
    return parts


def load(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    meta = data.setdefault("meta", {})
    data.setdefault("keywords", [])
    data.setdefault("introduction", [])
    data.setdefault("purpose", [])
    data.setdefault("principle", [])
    data.setdefault("content", {})
    data["content"].setdefault("apparatus", [])
    data["content"].setdefault("design", {})
    data["content"]["design"].setdefault("overview", [])
    data["content"]["design"].setdefault("uncertainty", {})
    data["content"].setdefault("procedure", [])
    data.setdefault("data_processing", {})
    data["data_processing"].setdefault("intro", [])
    data["data_processing"].setdefault("tables", [])
    data["data_processing"].setdefault("steps", [])
    data["data_processing"].setdefault("figures", [])
    data.setdefault("conclusion", {})
    data["conclusion"].setdefault("summary", [])
    data["conclusion"].setdefault("discussion", [])
    data["conclusion"].setdefault("questions", [])
    data.setdefault("references", [])
    return data


# ---------------------------------------------------------------------------
# LaTeX writer
# ---------------------------------------------------------------------------

LATEX_HEADER = r"""\documentclass[12pt,a4paper]{ctexart}
\usepackage{amsmath,amssymb,bm}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{geometry}
\usepackage{setspace}
\usepackage{caption}
\usepackage{float}
\usepackage[hidelinks]{hyperref}
\usepackage{enumitem}
\usepackage{titlesec}

\geometry{top=2.54cm,bottom=2.54cm,left=3.17cm,right=3.17cm}
\onehalfspacing
\setlength{\parindent}{2em}
\setlength{\parskip}{3pt}

\titleformat{\section}{\heiti\zihao{4}}{\thesection}{1em}{}
\titleformat{\subsection}{\heiti\zihao{-4}}{\thesubsection}{1em}{}
\captionsetup[table]{position=top,labelsep=quad}
\captionsetup[figure]{position=bottom,labelsep=quad}

\newcommand{\uA}{u_{\mathrm{A}}}
\newcommand{\uB}{u_{\mathrm{B}}}
\newcommand{\uC}{u_{\mathrm{C}}}

\begin{document}
"""


def tex_escape_text(s):
    """Escape characters that are special in LaTeX but keep $...$ math."""
    out = []
    for kind, val in split_math(s):
        if kind == "text":
            val = val.replace("\\", r"\textbackslash{}")
            for a, b in [("&", r"\&"), ("%", r"\%"), ("#", r"\#"),
                         ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
                         ("~", r"\textasciitilde{}"),
                         ("^", r"\textasciicircum{}")]:
                val = val.replace(a, b)
            out.append(val)
        elif kind == "inline":
            out.append("$" + val + "$")
        else:
            out.append(r"\[" + val + r"\]")
    return "".join(out)


def tex_paragraphs(body):
    chunks = []
    for p in body:
        if isinstance(p, str):
            chunks.append(tex_escape_text(p) + "\n")
    return "\n".join(chunks)


def build_tex(data, title, outdir):
    m = data["meta"]
    L = [LATEX_HEADER]
    doc_title = m.get("title") or title or "实验报告"

    # Title block
    L.append(r"\begin{center}")
    L.append(r"{\heiti\zihao{2} " + tex_escape_text(doc_title) + r"}\\[1em]")
    L.append(r"{\songti\zihao{5} " + tex_escape_text(
        "  ".join(x for x in [m.get("author", ""), m.get("student_id", ""),
                              m.get("department", "")] if x)) + r"}\\[0.3em]")
    L.append(r"{\songti\zihao{5} " + tex_escape_text(
        "  ".join(x for x in [m.get("institution", ""),
                              m.get("instructor", ""), m.get("date", "")]
                  if x)) + r"}\end{center}")
    L.append(r"\vspace{0.5em}")

    # Abstract
    L.append(r"\begin{center}{\heiti\zihao{5} 摘\quad 要}\end{center}")
    L.append(r"{\zihao{5}" + tex_escape_text(data.get("abstract", "")) + r"}")
    kw = "；".join(data.get("keywords", []))
    if kw:
        L.append(r"\noindent{\heiti\zihao{5} 关键词：}{\zihao{5}"
                 + tex_escape_text(kw) + r"}")
    L.append(r"\vspace{0.6em}")

    def section(name, paragraphs=None, raw=None):
        L.append(r"\section*{" + name + r"}")
        L.append(r"\addcontentsline{toc}{section}{" + name + r"}")
        if paragraphs:
            L.append(tex_paragraphs(paragraphs))
        if raw:
            L.append(raw)

    # 1 引言
    section(r"1\ 引言", data["introduction"])
    # 2 实验目的
    section(r"2\ 实验目的", data["purpose"])
    # 3 实验原理
    L.append(r"\section*{3\ 实验原理}")
    L.append(r"\addcontentsline{toc}{section}{3\ 实验原理}")
    for blk in data["principle"]:
        L.append(r"\subsection*{" + tex_escape_text(blk.get("heading", "")) + "}")
        L.append(tex_paragraphs(blk.get("body", [])))

    # 4 实验内容
    L.append(r"\section*{4\ 实验内容}")
    L.append(r"\addcontentsline{toc}{section}{4\ 实验内容}")
    app = data["content"]["apparatus"]
    if app:
        L.append(r"\subsection*{4.1\ 实验仪器}")
        L.append(r"\begin{table}[H]\centering")
        L.append(r"\caption{实验仪器与规格}")
        L.append(r"\begin{tabular}{p{3cm}p{3cm}p{1.2cm}p{5cm}}")
        L.append(r"\toprule")
        L.append(r"名称 & 规格型号 & 数量 & 用途 \\ \midrule")
        for a in app:
            L.append(" & ".join(tex_escape_text(str(a.get(k, "")))
                                for k in ("name", "model", "qty", "usage"))
                     + r" \\")
        L.append(r"\bottomrule\end{tabular}\end{table}")

    design = data["content"]["design"]
    L.append(r"\subsection*{4.2\ 实验设计}")
    L.append(tex_paragraphs(design.get("overview", [])))
    unc = design.get("uncertainty", {})
    if unc:
        L.append(r"\subsection*{4.3\ 不确定度分析}")
        L.append(tex_paragraphs(unc.get("intro", [])))
        for key, label in [("type_a", "A 类不确定度"),
                           ("type_b", "B 类不确定度"),
                           ("combined", "合成不确定度与扩展不确定度")]:
            node = unc.get(key)
            if not node:
                continue
            L.append(r"\paragraph{" + label + "}")
            L.append(tex_paragraphs(node.get("body", [])))

    L.append(r"\subsection*{4.4\ 实验具体内容}")
    for blk in data["content"]["procedure"]:
        L.append(r"\paragraph{" + tex_escape_text(blk.get("heading", "")) + "}")
        L.append(tex_paragraphs(blk.get("body", [])))

    # 5 数据处理
    L.append(r"\section*{5\ 实验数据处理}")
    L.append(r"\addcontentsline{toc}{section}{5\ 实验数据处理}")
    L.append(tex_paragraphs(data["data_processing"].get("intro", [])))
    for t in data["data_processing"]["tables"]:
        cols = t.get("columns", [])
        L.append(r"\begin{table}[H]\centering")
        L.append(r"\caption{" + tex_escape_text(t.get("caption", "")) + "}")
        L.append(r"\begin{tabular}{" + "c" * max(1, len(cols)) + "}")
        L.append(r"\toprule")
        L.append(" & ".join(tex_escape_text(c) for c in cols) + r" \\ \midrule")
        for row in t.get("rows", []):
            L.append(" & ".join(tex_escape_text(str(c)) for c in row) + r" \\")
        L.append(r"\bottomrule\end{tabular}")
        if t.get("note"):
            L.append(r"\\[2pt]{\zihao{6}" + tex_escape_text(t["note"]) + r"}")
        L.append(r"\end{table}")
    for s in data["data_processing"].get("steps", []):
        L.append(tex_escape_text(s) + "\n")
    for fig in data["data_processing"].get("figures", []):
        if os.path.exists(os.path.join(outdir, fig["path"])) or \
           os.path.exists(fig["path"]):
            path = fig["path"] if os.path.exists(fig["path"]) else \
                os.path.join(outdir, fig["path"])
            L.append(r"\begin{figure}[H]\centering")
            L.append(r"\includegraphics[width=%scm]{%s}" % (
                fig.get("width_cm", 12), path.replace("\\", "/")))
            L.append(r"\caption{" + tex_escape_text(fig.get("caption", "")) + r"}")
            L.append(r"\end{figure}")

    # 6 结论与思考题
    concl = data["conclusion"]
    L.append(r"\section*{6\ 实验结论与思考题}")
    L.append(r"\addcontentsline{toc}{section}{6\ 实验结论与思考题}")
    if concl.get("summary"):
        L.append(r"\subsection*{6.1\ 实验结论}")
        L.append(tex_paragraphs(concl["summary"]))
    if concl.get("discussion"):
        L.append(r"\subsection*{6.2\ 讨论与误差分析}")
        L.append(tex_paragraphs(concl["discussion"]))
    if concl.get("questions"):
        L.append(r"\subsection*{6.3\ 思考题解答}")
        for i, qa in enumerate(concl["questions"], 1):
            L.append(r"\paragraph{" + tex_escape_text(qa.get("q", "")) + "}")
            L.append(tex_paragraphs(qa.get("a", [])))

    # 7 参考文献
    if data.get("references"):
        L.append(r"\section*{参考文献}")
        L.append(r"\addcontentsline{toc}{section}{参考文献}")
        L.append(r"\begin{list}{}{\setlength{\leftmargin}{2em}"
                 r"\setlength{\itemindent}{-2em}\setlength{\itemsep}{2pt}}")
        for r in data["references"]:
            L.append(r"\item[] " + tex_escape_text(r))
        L.append(r"\end{list}")

    L.append(r"\end{document}")
    content = "\n".join(L)
    tex_path = os.path.join(outdir, _safe(title) + ".tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(content)
    return tex_path


# ---------------------------------------------------------------------------
# DOCX writer
# ---------------------------------------------------------------------------

def build_docx(data, title, outdir):
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
    from docx.oxml.ns import qn

    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(2.54)
    sec.bottom_margin = Cm(2.54)
    sec.left_margin = Cm(3.17)
    sec.right_margin = Cm(3.17)

    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

    def set_cn(run, font="宋体"):
        run.font.name = "Times New Roman"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), font)

    def add_para(text, size=12, bold=False, cn="宋体", align=None,
                 indent=True, line=1.5):
        p = doc.add_paragraph()
        if align is not None:
            p.alignment = align
        pf = p.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        pf.line_spacing = line
        if indent:
            pf.first_line_indent = Pt(24)
        for kind, val in split_math(text) if text else []:
            if kind == "text":
                r = p.add_run(val)
                r.font.size = Pt(size)
                r.bold = bold
                set_cn(r, cn)
            else:
                r = p.add_run((" " if kind == "inline" else "") +
                              "$" + val + "$" +
                              (" " if kind == "inline" else ""))
                r.font.size = Pt(size)
                r.font.name = "Cambria Math"
        return p

    def add_heading(text, size=14, cn="黑体", align=None):
        return add_para(text, size=size, bold=False, cn=cn,
                        align=align, indent=False, line=1.5)

    m = data["meta"]
    doc_title = m.get("title") or title or "实验报告"
    add_para(doc_title, size=18, cn="黑体",
             align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    info = "  ".join(x for x in [m.get("author", ""), m.get("student_id", ""),
                                 m.get("department", "")] if x)
    if info:
        add_para(info, size=10.5, cn="宋体",
                 align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    info2 = "  ".join(x for x in [m.get("institution", ""),
                                  m.get("instructor", ""), m.get("date", "")]
                      if x)
    if info2:
        add_para(info2, size=10.5, cn="宋体",
                 align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)

    add_para("摘  要", size=10.5, cn="黑体",
             align=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_para(data.get("abstract", ""), size=10.5)
    if data.get("keywords"):
        add_para("关键词：" + "；".join(data["keywords"]), size=10.5,
                 cn="黑体", indent=False)

    def section(num, name, paras):
        add_heading(f"{num}  {name}", size=14)
        for p in paras:
            add_para(p)

    section(1, "引言", data["introduction"])
    section(2, "实验目的", data["purpose"])

    add_heading("3  实验原理", size=14)
    for blk in data["principle"]:
        add_heading(blk.get("heading", ""), size=12)
        for p in blk.get("body", []):
            add_para(p)

    add_heading("4  实验内容", size=14)
    app = data["content"]["apparatus"]
    if app:
        add_heading("4.1  实验仪器", size=12)
        cols = ["名称", "规格型号", "数量", "用途"]
        table = doc.add_table(rows=1, cols=4)
        table.style = "Table Grid"
        for i, c in enumerate(cols):
            cell = table.rows[0].cells[i]
            cell.text = ""
            r = cell.paragraphs[0].add_run(c)
            r.font.size = Pt(10.5)
            r.bold = True
            set_cn(r, "黑体")
        for a in app:
            cells = table.add_row().cells
            for i, k in enumerate(("name", "model", "qty", "usage")):
                cells[i].text = ""
                r = cells[i].paragraphs[0].add_run(str(a.get(k, "")))
                r.font.size = Pt(10.5)
                set_cn(r)

    design = data["content"]["design"]
    add_heading("4.2  实验设计", size=12)
    for p in design.get("overview", []):
        add_para(p)
    unc = design.get("uncertainty", {})
    if unc:
        add_heading("4.3  不确定度分析", size=12)
        for p in unc.get("intro", []):
            add_para(p)
        for key, label in [("type_a", "A 类不确定度"),
                           ("type_b", "B 类不确定度"),
                           ("combined", "合成不确定度与扩展不确定度")]:
            node = unc.get(key)
            if not node:
                continue
            add_heading(label, size=11, cn="黑体")
            for p in node.get("body", []):
                add_para(p)

    add_heading("4.4  实验具体内容", size=12)
    for blk in data["content"]["procedure"]:
        add_heading(blk.get("heading", ""), size=11, cn="黑体")
        for p in blk.get("body", []):
            add_para(p)

    add_heading("5  实验数据处理", size=14)
    for p in data["data_processing"].get("intro", []):
        add_para(p)
    for t in data["data_processing"]["tables"]:
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cap.add_run(t.get("caption", ""))
        r.font.size = Pt(10.5)
        set_cn(r, "宋体")
        cols = t.get("columns", [])
        table = doc.add_table(rows=1, cols=max(1, len(cols)))
        table.style = "Table Grid"
        for i, c in enumerate(cols):
            cell = table.rows[0].cells[i]
            cell.text = ""
            r = cell.paragraphs[0].add_run(str(c))
            r.font.size = Pt(10.5)
            r.bold = True
            set_cn(r, "宋体")
        for row in t.get("rows", []):
            cells = table.add_row().cells
            for i, c in enumerate(row):
                if i < len(cells):
                    cells[i].text = ""
                    r = cells[i].paragraphs[0].add_run(str(c))
                    r.font.size = Pt(10.5)
                    set_cn(r)
        if t.get("note"):
            add_para(t["note"], size=9, indent=False)
    for s in data["data_processing"].get("steps", []):
        add_para(s)
    for fig in data["data_processing"].get("figures", []):
        path = fig["path"]
        if not os.path.exists(path):
            cand = os.path.join(outdir, path)
            if os.path.exists(cand):
                path = cand
        if os.path.exists(path) and path.lower().endswith(
                (".png", ".jpg", ".jpeg", ".bmp", ".gif")):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(path, width=Cm(fig.get("width_cm", 12)))
            cap = doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = cap.add_run(fig.get("caption", ""))
            r.font.size = Pt(9)
            set_cn(r)

    concl = data["conclusion"]
    add_heading("6  实验结论与思考题", size=14)
    if concl.get("summary"):
        add_heading("6.1  实验结论", size=12)
        for p in concl["summary"]:
            add_para(p)
    if concl.get("discussion"):
        add_heading("6.2  讨论与误差分析", size=12)
        for p in concl["discussion"]:
            add_para(p)
    if concl.get("questions"):
        add_heading("6.3  思考题解答", size=12)
        for qa in concl["questions"]:
            add_heading(qa.get("q", ""), size=11, cn="黑体")
            for p in qa.get("a", []):
                add_para(p)

    if data.get("references"):
        add_heading("参考文献", size=14)
        for r in data["references"]:
            add_para(r, size=10.5, indent=False)

    docx_path = os.path.join(outdir, _safe(title) + ".docx")
    doc.save(docx_path)
    return docx_path


def _safe(name):
    name = re.sub(r'[\\/:*?"<>|]', "", name or "report").strip()
    return name or "report"


# ---------------------------------------------------------------------------
# PDF via xelatex
# ---------------------------------------------------------------------------

def build_pdf(tex_path, outdir):
    xelatex = shutil.which("xelatex")
    if not xelatex:
        return None
    for _ in range(2):
        proc = subprocess.run(
            [xelatex, "-interaction=nonstopmode", "-halt-on-error",
             os.path.basename(tex_path)],
            cwd=outdir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if proc.returncode != 0:
            log = proc.stdout.decode("utf-8", "ignore")
            sys.stderr.write(log[-4000:])
            return None
    return os.path.join(outdir, os.path.splitext(
        os.path.basename(tex_path))[0] + ".pdf")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--outdir", default="output")
    ap.add_argument("--formats", default="docx,pdf,tex")
    ap.add_argument("--title", default="实验报告")
    args = ap.parse_args()

    data = load(args.input)
    os.makedirs(args.outdir, exist_ok=True)
    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    made = {}

    if "tex" in formats or "pdf" in formats:
        tex_path = build_tex(data, args.title, args.outdir)
        made["tex"] = tex_path
    if "pdf" in formats:
        pdf = build_pdf(tex_path, args.outdir)
        if pdf:
            made["pdf"] = pdf
        else:
            sys.stderr.write(
                "[warn] xelatex not found or failed; PDF skipped.\n")
    if "docx" in formats:
        made["docx"] = build_docx(data, args.title, args.outdir)

    for k, v in made.items():
        sys.stdout.write(f"{k}: {os.path.abspath(v)}\n")


if __name__ == "__main__":
    main()
