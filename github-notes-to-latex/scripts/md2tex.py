#!/usr/bin/env python3
"""Convert an Obsidian/MkDocs Markdown vault into LaTeX chapter files that are
\\input by main.tex and compiled with XeLaTeX (ctexbook).

Design goals:
  * Preserve a deterministic chapter order.
  * Convert Obsidian syntax: YAML frontmatter, [[wikilinks]], ![[images]],
    callouts (> [!note]), ==highlight==, footnotes, tables, fenced code,
    standard [text](url) links.
  * Keep $...$ and $$...$$ math intact (fix a few known bad characters).
  * Emit one .tex per logical unit plus a generated chapters/_manifest.tex.

Chapter order is resolved from, in priority order:
  1. ``--config <file.json>``  — explicit chapter spec (see reference/chapters_schema.md)
  2. a ``chapters.json`` next to the source root
  3. a built-in preset selected with ``--preset <name>`` (currently ``ustc-ai-notes``)
  4. auto-discovery: numbered top-level directories become chapters in order

Usage:
  python md2tex.py <source-root> <output-dir> [--config F | --preset NAME | --auto]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

_ARGS = None  # parsed in main()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("source", nargs="?", default="source-notes",
                   help="root directory of the Markdown notes")
    p.add_argument("output", nargs="?", default=".",
                   help="output directory (chapters/ and images/ are created here)")
    p.add_argument("--config", help="JSON file describing chapter order")
    p.add_argument("--preset", help="built-in chapter preset name (e.g. ustc-ai-notes)")
    p.add_argument("--auto", action="store_true",
                   help="force auto-discovery of chapters from numbered directories")
    return p.parse_args(argv)


REPO = Path("source-notes")
OUT = Path(".")
CHAPTERS = OUT / "chapters"
IMAGES = OUT / "images"
CHAPTERS = OUT / "chapters"
IMAGES = OUT / "images"

# ---------------------------------------------------------------------------
# Chapter ordering. Each logical chapter has:
#   number   : chapter number (None -> use \chapter*)
#   title    : display title
#   index    : chapter index markdown (optional)
#   sections : ordered list of section markdown files
#   cards    : list of (group_title, [card files]) rendered as chapter appendix
# ---------------------------------------------------------------------------
USTC_AI_NOTES_SPECS = [
    {
        "number": None,
        "title": "知识地图",
        "index": "人工智能数学原理与算法A.md",
        "sections": [],
        "cards": [],
    },
    {
        "number": 0,
        "title": "公共基础",
        "index": "00-公共基础/00-公共基础.md",
        "sections": [],
        "cards": [
            ("基本概念", [
                "00-公共基础/基本概念/假设类.md",
                "00-公共基础/基本概念/损失函数.md",
                "00-公共基础/基本概念/优化算法.md",
                "00-公共基础/基本概念/正则化方法.md",
                "00-公共基础/基本概念/激活函数.md",
                "00-公共基础/基本概念/拟合与泛化.md",
            ]),
            ("算法与函数", [
                "00-公共基础/算法/梯度下降.md",
                "00-公共基础/算法/反向传播.md",
                "00-公共基础/算法/Sigmoid函数.md",
                "00-公共基础/算法/Softmax函数.md",
                "00-公共基础/算法/ReLU.md",
                "00-公共基础/算法/L1正则化.md",
                "00-公共基础/算法/L2正则化.md",
                "00-公共基础/算法/残差连接.md",
            ]),
        ],
    },
    {
        "number": 1,
        "title": "数学基础",
        "index": "00-数学基础/00-数学基础.md",
        "sections": [
            "00-数学基础/0.1-线性代数与张量.md",
            "00-数学基础/0.2-微积分与自动微分.md",
            "00-数学基础/0.3-概率统计与信息论.md",
            "00-数学基础/0.4-最优化基础.md",
            "00-数学基础/0.5-符号与维度速查.md",
        ],
        "cards": [],
    },
    {
        "number": 2,
        "title": "人工智能概述",
        "index": "01-人工智能概述/01-人工智能概述.md",
        "sections": [
            "01-人工智能概述/1.1-人工智能简介.md",
            "01-人工智能概述/1.2-人工智能与机器学习简史.md",
            "01-人工智能概述/1.3-人工智能的意义与展望.md",
        ],
        "cards": [
            ("常识", [
                "01-人工智能概述/常识/人工智能主要流派.md",
                "01-人工智能概述/常识/人工智能的浪潮与波谷.md",
            ]),
        ],
    },
    {
        "number": 3,
        "title": "机器学习基础",
        "index": "02-机器学习基础/02-机器学习基础.md",
        "sections": [
            "02-机器学习基础/2.1-机器学习简介.md",
            "02-机器学习基础/2.2-线性回归.md",
            "02-机器学习基础/2.3-逻辑回归.md",
        ],
        "cards": [
            ("基本概念", [
                "02-机器学习基础/基本概念/正态分布.md",
                "02-机器学习基础/基本概念/特征提取器.md",
            ]),
            ("算法", [
                "02-机器学习基础/算法/交叉熵损失.md",
            ]),
        ],
    },
    {
        "number": 4,
        "title": "神经网络基础",
        "index": "03-神经网络基础/03-神经网络基础.md",
        "sections": [
            "03-神经网络基础/3.1-前馈神经网络.md",
            "03-神经网络基础/3.2-神经网络优化.md",
            "03-神经网络基础/3.3-深度神经网络.md",
            "03-神经网络基础/卷积神经网络.md",
        ],
        "cards": [
            ("基本概念", [
                "03-神经网络基础/基本概念/M-P神经元.md",
                "03-神经网络基础/基本概念/感知机.md",
            ]),
            ("算法", [
                "03-神经网络基础/算法/池化层.md",
                "03-神经网络基础/算法/深度神经网络中的初始化.md",
                "03-神经网络基础/算法/深度神经网络中的归一化.md",
            ]),
            ("定理", [
                "03-神经网络基础/定理/万能近似定理.md",
            ]),
        ],
    },
    {
        "number": 5,
        "title": "图神经网络",
        "index": "04-图神经网络/04-图神经网络.md",
        "sections": [
            "04-图神经网络/4.1-图数据与图学习简介.md",
            "04-图神经网络/4.2-图表征学习.md",
            "04-图神经网络/4.3-图神经网络的基本操作.md",
            "04-图神经网络/4.4-图神经网络的经典架构.md",
        ],
        "cards": [
            ("基本概念", [
                "04-图神经网络/基本概念/度矩阵.md",
                "04-图神经网络/基本概念/异构图.md",
                "04-图神经网络/基本概念/拉普拉斯矩阵.md",
                "04-图神经网络/基本概念/消息传递范式.md",
                "04-图神经网络/基本概念/节点嵌入.md",
            ]),
            ("算法", [
                "04-图神经网络/算法/DeepWalk.md",
                "04-图神经网络/算法/Node2vec.md",
                "04-图神经网络/算法/图注意力网络GAT.md",
                "04-图神经网络/算法/随机游走.md",
            ]),
        ],
    },
    {
        "number": 6,
        "title": "Transformer",
        "index": "05-Transformer/05-Transformer.md",
        "sections": [
            "05-Transformer/5.1-Transformer简介与注意力机制.md",
            "05-Transformer/5.2-Transformer 的编码与解码器.md",
            "05-Transformer/5.3-Transformer 的典型应用.md",
        ],
        "cards": [
            ("基本概念", [
                "05-Transformer/基本概念/多头注意力.md",
                "05-Transformer/基本概念/自注意力机制.md",
            ]),
            ("模型", [
                "05-Transformer/模型/LSTM.md",
                "05-Transformer/模型/RNN.md",
            ]),
            ("算法", [
                "05-Transformer/算法/掩码矩阵.md",
                "05-Transformer/算法/残差连接与层归一化.md",
            ]),
        ],
    },
    {
        "number": 7,
        "title": "自监督学习",
        "index": "06-自监督学习/06-自监督学习.md",
        "sections": [
            "06-自监督学习/6.1-自监督学习简介.md",
            "06-自监督学习/6.2-word2vec 与 BERT 模型.md",
            "06-自监督学习/6.3-自回归语言建模.md",
            "06-自监督学习/6.4-大语言模型.md",
        ],
        "cards": [
            ("基本概念", [
                "06-自监督学习/基本概念/词向量.md",
                "06-自监督学习/基本概念/掩码语言建模.md",
                "06-自监督学习/基本概念/困惑度.md",
                "06-自监督学习/基本概念/扩展法则.md",
                "06-自监督学习/基本概念/涌现能力.md",
                "06-自监督学习/基本概念/零样本学习.md",
                "06-自监督学习/基本概念/大模型的幻觉.md",
            ]),
            ("算法", [
                "06-自监督学习/算法/skip-gram.md",
                "06-自监督学习/算法/负采样.md",
                "06-自监督学习/算法/自回归语言模型.md",
            ]),
        ],
    },
    {
        "number": 8,
        "title": "强化学习",
        "index": "07-强化学习/07-强化学习.md",
        "sections": [
            "07-强化学习/7.1-强化学习简介.md",
            "07-强化学习/7.2-马尔可夫决策过程.md",
            "07-强化学习/7.3-动态规划算法.md",
            "07-强化学习/7.4 Q-学习.md",
            "07-强化学习/7.5-深度 Q 学习.md",
            "07-强化学习/7.6-多智能体强化学习.md",
        ],
        "cards": [
            ("基本概念", [
                "07-强化学习/基本概念/马尔可夫决策过程.md",
                "07-强化学习/基本概念/马尔可夫奖励过程.md",
            ]),
            ("定理", [
                "07-强化学习/定理/贝尔曼期望方程.md",
                "07-强化学习/定理/贝尔曼最优方程.md",
            ]),
            ("算法", [
                "07-强化学习/算法/Q-学习.md",
                "07-强化学习/算法/价值迭代.md",
                "07-强化学习/算法/策略迭代.md",
                "07-强化学习/算法/目标网络.md",
                "07-强化学习/算法/经验回放.md",
            ]),
        ],
    },
    {
        "number": None,
        "title": "实验课讲义",
        "index": None,
        "sections": [
            "实验课/实验一-Python入门/实验一讲义.md",
            "实验课/实验二-Python调试与函数/实验二讲义.md",
        ],
        "cards": [],
    },
]


def load_specs_from_json(path: Path) -> list[dict]:
    """Load a chapter spec from a JSON file (list of chapter objects)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "chapters" in data:
        data = data["chapters"]
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON list of chapters")
    return data


def discover_specs(root: Path) -> tuple[list[dict], str]:
    """Auto-discover chapters from the notes tree.

    Strategy:
      * Each top-level directory is a chapter. Directories whose name starts
        with a number are ordered by that number; others follow alphabetically
        after them.
      * Within a chapter directory, markdown files whose stem starts with a
        digit or looks like ``x.y-`` are ordered sections; files named
        ``00-*/index`` (or ``NN-<dirname>.md``) are treated as the index.
      * Nested subdirectories named 基本概念/算法/定理/模型 become card groups.
    Returns (specs, preset_name).
    """
    def sort_key(p: Path):
        m = re.match(r"^(\d+)", p.name)
        return (0, int(m.group(1)), p.name) if m else (1, 0, p.name)

    def section_key(p: Path):
        m = re.match(r"^(\d+)\.(\d+)", p.stem)
        if m:
            return (0, int(m.group(1)), int(m.group(2)), p.name)
        m = re.match(r"^(\d+)", p.stem)
        if m:
            return (0, int(m.group(1)), 0, p.name)
        return (1, 0, 0, p.name)

    NAME_MAP = {
        "基本概念": "基本概念", "概念": "基本概念", "常识": "常识",
        "算法": "算法", "函数": "算法", "定理": "定理", "模型": "模型",
    }

    specs: list[dict] = []
    top_dirs = sorted([d for d in root.iterdir() if d.is_dir()
                       and not d.name.startswith(".") and d.name != "assets"], key=sort_key)
    # Loose top-level markdown files (e.g. a knowledge-map) become an intro chapter.
    loose = sorted([f for f in root.glob("*.md")], key=sort_key)

    if loose:
        specs.append({"number": None, "title": "总览",
                      "index": str(loose[0].relative_to(root)).replace("\\", "/"),
                      "sections": [], "cards": []})

    for ci, d in enumerate(top_dirs):
        title = re.sub(r"^\d+[-_.\s]*", "", d.name) or d.name
        md_files = [f for f in d.glob("*.md")]
        md_files.sort(key=section_key)

        index = None
        sections = []
        for f in md_files:
            # Index file: same name as dir (sans number) or a STUB named index.
            dir_stem = re.sub(r"^\d+[-_.\s]*", "", d.name)
            if f.stem in (dir_stem, d.name, "index", "README"):
                index = str(f.relative_to(root)).replace("\\", "/")
            else:
                sections.append(str(f.relative_to(root)).replace("\\", "/"))

        cards = []
        for sub in sorted([x for x in d.iterdir() if x.is_dir()], key=sort_key):
            group = NAME_MAP.get(sub.name, sub.name)
            files = sorted([str(f.relative_to(root)).replace("\\", "/")
                            for f in sub.glob("*.md")], key=lambda s: sort_key(Path(s)))
            if files:
                cards.append((group, files))

        specs.append({"number": ci, "title": title, "index": index,
                      "sections": sections, "cards": cards})
    return specs, "auto"


def resolve_specs(args) -> list[dict]:
    """Pick the chapter spec source based on CLI arguments and available files."""
    if args.config:
        return load_specs_from_json(Path(args.config))
    local = REPO / "chapters.json"
    if local.is_file():
        print(f"Using chapter spec: {local}")
        return load_specs_from_json(local)
    if args.preset:
        if args.preset in ("ustc-ai-notes", "ustc", "default"):
            return USTC_AI_NOTES_SPECS
        raise SystemExit(f"Unknown preset: {args.preset!r}")
    if args.auto:
        specs, name = discover_specs(REPO)
        print(f"Auto-discovered {len(specs)} chapters.")
        return specs
    # Heuristic: if the known knowledge-map file exists, use the built-in preset.
    if (REPO / "人工智能数学原理与算法A.md").is_file():
        print("Using built-in preset: ustc-ai-notes")
        return USTC_AI_NOTES_SPECS
    specs, name = discover_specs(REPO)
    print(f"Auto-discovered {len(specs)} chapters.")
    return specs

# ---------------------------------------------------------------------------
# Filename → link label index (stems + aliases) so [[...]] becomes plain text.
# ---------------------------------------------------------------------------


def read_frontmatter(path: Path):
    text = path.read_text(encoding="utf-8")
    # Strip a UTF-8 BOM if present (Windows editors / Set-Content add one).
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    fm: dict[str, str] = {}
    aliases: list[str] = []
    in_aliases = False
    for line in lines[1:end]:
        if re.match(r"^aliases:\s*$", line):
            in_aliases = True
            continue
        if re.match(r"^[A-Za-z_]+:\s*", line):
            key = line.split(":", 1)[0]
            fm[key] = line.split(":", 1)[1].strip()
            in_aliases = False
            continue
        if in_aliases:
            m = re.match(r"\s+-\s+(.+?)\s*$", line)
            if m:
                aliases.append(m.group(1).strip("\"'"))
    if aliases:
        fm["_aliases"] = aliases
    body = "\n".join(lines[end + 1:])
    return fm, body


# ---------------------------------------------------------------------------
# Inline conversion
# ---------------------------------------------------------------------------

WIKILINK = re.compile(r"(!?)\[\[([^\]]+)\]\]")
MD_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
INLINE_MATH = re.compile(r"(?<!\$)\$([^$\n]+?)\$(?!\$)")
INLINE_CODE = re.compile(r"`([^`]+)`")
HIGHLIGHT = re.compile(r"==(.+?)==")
FOOTNOTE_REF = re.compile(r"\[\^([^\]]+)\]")
UNDERLINE = re.compile(r"\\underline\{")

LATEX_UNSAFE = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

# Circled numbers and a few pictographs that fall outside the CJK/Latin fonts.
UNICODE_REPLACE = {
    "\u2460": "(1)", "\u2461": "(2)", "\u2462": "(3)", "\u2463": "(4)",
    "\u2464": "(5)", "\u2465": "(6)", "\u2466": "(7)", "\u2467": "(8)",
    "\u2468": "(9)", "\u2469": "(10)", "\u246a": "(11)", "\u246b": "(12)",
    "\u246c": "(13)", "\u246d": "(14)", "\u246e": "(15)", "\u246f": "(16)",
    "\u2470": "(17)", "\u2471": "(18)", "\u2472": "(19)", "\u2473": "(20)",
    "\u2705": "[OK]", "\u274c": "[X]", "\u26a0\ufe0f": "!", "\u26a0": "!",
    "\u2705\ufe0f": "[OK]",
}

# Symbols that appear in body text but need math mode in LaTeX.
TEXT_MATH_SYMBOLS = {
    "\u2283": r"$\supset$",
    "\u2282": r"$\subset$",
    "\u2208": r"$\in$",
    "\u2209": r"$\notin$",
    "\u2200": r"$\forall$",
    "\u2203": r"$\exists$",
    "\u2192": r"$\rightarrow$",
    "\u21d2": r"$\Rightarrow$",
    "\u21d4": r"$\Leftrightarrow$",
    "\u2264": r"$\le$",
    "\u2265": r"$\ge$",
    "\u2260": r"$\ne$",
    "\u2248": r"$\approx$",
    "\u2211": r"$\sum$",
    "\u220f": r"$\prod$",
    "\u222b": r"$\int$",
    "\u221e": r"$\infty$",
    "\u00d7": r"$\times$",
    "\u00b7": r"$\cdot$",
}


def normalize_unicode(s: str) -> str:
    for k, v in UNICODE_REPLACE.items():
        s = s.replace(k, v)
    return s


def fix_math(s: str) -> str:
    # Known bad characters inside math that break XeLaTeX.
    s = normalize_unicode(s)
    s = s.replace("\u2019", "'")
    s = s.replace("\u2028", "\n")
    s = s.replace("\u2029", "\n")
    s = s.replace("\u00a0", " ")
    # ctex provides these via text mode; ensure Chinese in \text works.
    s = s.replace(r"\text{若", r"\text{若}")
    return s


DISPLAY_ENVS = ("align", "align*", "gather", "gather*", "multline", "multline*",
                "equation", "equation*", "flalign", "flalign*", "alignat", "alignat*",
                "eqnarray", "eqnarray*")


def emit_math(content: str) -> str:
    """Emit display math, avoiding nested display environments and blank lines
    (blank lines inside math mode break align/matrix structures)."""
    content = fix_math(content).strip()
    content = "\n".join(ln for ln in content.split("\n") if ln.strip())
    m = re.match(r"^\\begin\{([^}]+)\}", content)
    if m and m.group(1) in DISPLAY_ENVS:
        return "\n" + content + "\n"
    return "\n\\begin{equation*}\n" + content + "\n\\end{equation*}\n"


def escape_text(s: str) -> str:
    s = normalize_unicode(s)
    out = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "\\":
            # Preserve intended LaTeX escapes like \|, \ldots when present.
            nxt = s[i + 1] if i + 1 < len(s) else ""
            if nxt and nxt in "|,;:!%&#_{}":
                out.append("\\" + nxt)
                i += 2
                continue
            out.append(r"\textbackslash{}")
            i += 1
            continue
        out.append(LATEX_UNSAFE.get(ch, ch))
        i += 1
    return "".join(out)


def wikilink_label(body: str) -> str:
    body = body.replace(r"\|", "|")
    parts = body.split("|")
    target = parts[0].split("#")[0].strip()
    if len(parts) > 1:
        return parts[1].strip()
    return target


def inline_to_tex(text: str) -> str:
    """Convert inline markdown to LaTeX, protecting math and code spans.

    Implementation: use a single shared placeholder registry so that nested
    emphasis (bold inside a table cell, highlight inside bold, ...) resolves
    correctly without index collisions across recursive calls.
    """
    placeholders: list[str] = []

    def stash(value: str) -> str:
        placeholders.append(value)
        return f"\x00{len(placeholders) - 1}\x00"

    def convert(seg: str) -> str:
        # Order matters: protect verbatim spans first.
        seg = INLINE_MATH.sub(lambda m: stash("$" + fix_math(m.group(1)) + "$"), seg)
        seg = INLINE_CODE.sub(lambda m: stash(r"\texttt{" + escape_text(m.group(1)) + "}"), seg)
        # Standard Markdown links/images.
        seg = MD_IMAGE.sub(
            lambda m: stash(r"\emph{" + escape_text(m.group(1) or m.group(2)) + "}"),
            seg,
        )

        def link_repl(m: re.Match) -> str:
            label, url = m.group(1), m.group(2).strip()
            url_esc = url.replace("%", r"\%").replace("#", r"\#")
            return stash(r"\href{" + url_esc + "}{" + escape_text(label) + "}")

        seg = MD_LINK.sub(link_repl, seg)
        seg = WIKILINK.sub(
            lambda m: stash(
                (r"\emph{" + escape_text(wikilink_label(m.group(2))) + "}")
                if m.group(1)
                else escape_text(wikilink_label(m.group(2)))
            ),
            seg,
        )
        # Emphasis (bold then italic) -> recursively convert inner, then stash.
        seg = re.sub(r"\*\*(.+?)\*\*", lambda m: stash(r"\textbf{" + convert(m.group(1)) + "}"), seg)
        seg = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", lambda m: stash(r"\emph{" + convert(m.group(1)) + "}"), seg)
        seg = HIGHLIGHT.sub(lambda m: stash(r"\hl{" + convert(m.group(1)) + "}"), seg)
        # Math symbols that appear in body text: substitute via stash so their
        # inserted `$...$` is not escaped afterwards.
        for k, v in TEXT_MATH_SYMBOLS.items():
            if k in seg:
                seg = seg.replace(k, stash(v))
        # Escape whatever raw text remains.
        return escape_text(seg)

    text = convert(text)

    def restore(match: re.Match) -> str:
        idx = int(match.group(1))
        return placeholders[idx] if idx < len(placeholders) else ""

    for _ in range(12):
        new = re.sub(r"\x00(\d+)\x00", restore, text)
        if new == text:
            break
        text = new
    return text


# ---------------------------------------------------------------------------
# Block conversion
# ---------------------------------------------------------------------------

FENCE = re.compile(r"^\s*(```|~~~)\s*([^\s`]*)\s*$")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
UL = re.compile(r"^(\s*)[-*+]\s+(.*)$")
OL = re.compile(r"^(\s*)(\d+)\.\s+(.*)$")
BLOCKQUOTE = re.compile(r"^>\s?(.*)$")
FOOTNOTE_DEF = re.compile(r"^\[\^([^\]]+)\]:\s*(.*)$")

LANG_MAP = {
    "python": "Python",
    "py": "Python",
    "bash": "bash",
    "sh": "bash",
    "bat": "Batch",
    "cmd": "Batch",
    "text": "",
    "yaml": "YAML",
    "json": "JSON",
    "yml": "YAML",
}


class Converter:
    def __init__(self, base_heading_level: int = 2):
        self.base = base_heading_level
        self.card_mode = False
        self.footnotes: list[tuple[str, str]] = []
        self.image_counter = 0

    def convert_body(self, body: str, strip_title: bool = True) -> str:
        lines = body.split("\n")
        out: list[str] = []
        i = 0
        first_h1_seen = not strip_title
        while i < len(lines):
            line = lines[i]

            # Standalone image embed: ![[image.png]]
            mi = re.match(r"^\s*!\[\[([^\]]+\.(?:png|jpg|jpeg|pdf|svg|gif))\]\]\s*$", line, re.I)
            if mi:
                out.append(self._image(mi.group(1).strip()))
                i += 1
                continue

            # Block math: line that starts with $$ (delimiters may close on a
            # later line, or on the same line).
            if line.lstrip().startswith("$$"):
                math_lines = []
                first = line.lstrip()[2:]
                if first.rstrip().endswith("$$") and first.rstrip() != "":
                    math_lines.append(first.rstrip()[:-2])
                    i += 1
                else:
                    if first.strip():
                        math_lines.append(first)
                    i += 1
                    while i < len(lines):
                        if "$$" in lines[i]:
                            head = lines[i].split("$$", 1)[0]
                            if head.strip():
                                math_lines.append(head)
                            i += 1
                            break
                        math_lines.append(lines[i])
                        i += 1
                out.append(emit_math("\n".join(math_lines)))
                continue

            # Fenced code
            m = FENCE.match(line)
            if m:
                lang = m.group(2).strip().lower()
                i += 1
                buf = []
                while i < len(lines) and not FENCE.match(lines[i]):
                    buf.append(lines[i])
                    i += 1
                i += 1  # skip closing fence
                out.append(self._verbatim("\n".join(buf), LANG_MAP.get(lang, "")))
                continue

            # Footnote definition
            m = FOOTNOTE_DEF.match(line)
            if m:
                self.footnotes.append((m.group(1), m.group(2)))
                i += 1
                continue

            # Blockquote (callouts / block math inside quote)
            if BLOCKQUOTE.match(line):
                block = []
                while i < len(lines) and BLOCKQUOTE.match(lines[i]):
                    block.append(BLOCKQUOTE.match(lines[i]).group(1))
                    i += 1
                out.append(self._blockquote(block))
                continue

            # Heading
            m = HEADING.match(line)
            if m:
                level = len(m.group(1))
                title = inline_to_tex(m.group(2).strip())
                if level == 1 and self.card_mode:
                    out.append(f"\\cardtitle{{{title}}}\n")
                    i += 1
                    continue
                if level == 1 and not first_h1_seen:
                    first_h1_seen = True
                    i += 1
                    continue
                # In a book chapter, the file's `#` title is stripped; `##`
                # maps to \section, `###` to \subsection, and so on.
                if level == 1:
                    lvl = self.base
                else:
                    lvl = max(1, min(5, self.base + (level - 2)))
                out.append(self._heading(lvl, title))
                i += 1
                continue

            # Table
            if "|" in line and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|", lines[i + 1]) and "|" in lines[i + 1]:
                tbl, i = self._table(lines, i)
                out.append(tbl)
                continue

            # Lists
            if UL.match(line) or OL.match(line):
                block, i = self._list(lines, i)
                out.append(block)
                continue

            # Horizontal rule
            if re.match(r"^\s*([-*_])\s*(\1\s*){2,}$", line):
                out.append(r"\medskip\hrule\medskip")
                i += 1
                continue

            # Blank
            if not line.strip():
                out.append("")
                i += 1
                continue

            # Paragraph (gather consecutive lines)
            para = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not self._is_block_start(lines, i):
                para.append(lines[i])
                i += 1
            out.append(self._paragraph(para))
            continue
        return "\n".join(out)

    def _is_block_start(self, lines, i):
        line = lines[i]
        if FENCE.match(line) or HEADING.match(line) or BLOCKQUOTE.match(line) or FOOTNOTE_DEF.match(line):
            return True
        if UL.match(line) or OL.match(line):
            return True
        if re.match(r"^\s*([-*_])\s*(\1\s*){2,}$", line):
            return True
        if line.strip().startswith("$$"):
            return True
        return False

    def _image(self, name: str) -> str:
        return (
            "\\begin{figure}[H]\n\\centering\n"
            f"\\includegraphics[width=0.85\\textwidth,keepaspectratio]{{{name}}}\n"
            f"\\caption*{{\\small {escape_text(Path(name).stem)}}}\n"
            "\\end{figure}\n"
        )

    def _heading(self, level: int, title: str) -> str:
        cmd = {1: "section", 2: "subsection", 3: "subsubsection", 4: "paragraph", 5: "subparagraph"}[level]
        if cmd in ("paragraph", "subparagraph"):
            return f"\\{cmd}{{{title}}}\n"
        return f"\\{cmd}{{{title}}}\n\\label{{sec:{abs(hash(title)) % 10**8}}}\n"

    def _paragraph(self, lines: list[str]) -> str:
        joined = "\n".join(lines)
        # Block math $$ ... $$ possibly spanning lines
        if "$$" in joined:
            return self._paragraph_with_math(joined)
        return inline_to_tex(joined) + "\n"

    def _paragraph_with_math(self, text: str) -> str:
        parts = re.split(r"\$\$(.+?)\$\$", text, flags=re.S)
        out = []
        for idx, part in enumerate(parts):
            if idx % 2 == 1:
                out.append(emit_math(part.strip()))
            else:
                if part.strip():
                    out.append(inline_to_tex(part.strip()))
        return "".join(out)

    def _blockquote(self, block: list[str]) -> str:
        # Callout?
        joined = "\n".join(block)
        m = re.match(r"^\[!(\w+)\]\s*(.*)$", block[0].strip()) if block else None
        if m:
            kind = m.group(1).lower()
            inline_title = m.group(2).strip()
            rest = block[1:]
            inner = self.convert_body("\n".join(rest), strip_title=False)
            title_map = {"note": "提示", "tip": "提示", "warning": "注意", "important": "重点", "info": "说明"}
            title = inline_title if inline_title else title_map.get(kind, kind.capitalize())
            return (
                "\\begin{notebox}{" + inline_to_tex(title) + "}\n"
                + inner
                + "\n\\end{notebox}\n"
            )
        # Plain quote, may contain block math.
        inner = self._quote_inner(block)
        return "\\begin{quote}\n" + inner + "\n\\end{quote}\n"

    def _quote_inner(self, block: list[str]) -> str:
        text = "\n".join(block)
        if "$$" in text:
            parts = re.split(r"\$\$(.+?)\$\$", text, flags=re.S)
            out = []
            for idx, part in enumerate(parts):
                if idx % 2 == 1:
                    out.append(emit_math(part.strip()))
                else:
                    if part.strip():
                        out.append(inline_to_tex(part.strip()))
            return "\n".join(out)
        return inline_to_tex(text)

    def _table(self, lines: list[str], i: int) -> tuple[str, int]:
        header = self._split_row(lines[i])
        i += 2  # skip header + separator
        rows = []
        while i < len(lines) and "|" in lines[i] and lines[i].strip():
            rows.append(self._split_row(lines[i]))
            i += 1
        ncol = max(len(header), max((len(r) for r in rows), default=0))
        colspec = self._colspec(ncol)
        out = ["\\begin{center}", "\\begin{tabular}{" + colspec + "}", "\\toprule"]
        out.append(" & ".join(inline_to_tex(c) for c in self._pad(header, ncol)) + r" \\")
        out.append("\\midrule")
        for r in rows:
            out.append(" & ".join(inline_to_tex(c) for c in self._pad(r, ncol)) + r" \\")
        out.append("\\bottomrule")
        out.append("\\end{tabular}")
        out.append("\\end{center}")
        return "\n".join(out) + "\n", i

    @staticmethod
    def _split_row(line: str) -> list[str]:
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|") and not line.endswith(r"\|"):
            line = line[:-1]
        # Split on unescaped pipes only; Obsidian escapes in-cell pipes as \|.
        cells = re.split(r"(?<!\\)\|", line)
        return [c.strip().replace(r"\|", "|") for c in cells]

    @staticmethod
    def _pad(row: list[str], n: int) -> list[str]:
        return row + [""] * (n - len(row))

    @staticmethod
    def _colspec(n: int) -> str:
        if n <= 0:
            return "l"
        # Use wrapping columns so long cell text breaks instead of overflowing.
        if n == 1:
            return "p{0.9\\textwidth}"
        if n == 2:
            return "p{0.33\\textwidth} p{0.6\\textwidth}"
        if n == 3:
            return " ".join(["p{0.3\\textwidth}"] * n)
        if n == 4:
            return " ".join(["p{0.22\\textwidth}"] * n)
        return " ".join(["p{0.17\\textwidth}"] * n)

    def _list(self, lines: list[str], i: int) -> tuple[str, int]:
        items = []  # (depth, ordered, text, raw_block)
        base_indent = len(re.match(r"^(\s*)", lines[i]).group(1))
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                # allow blank inside list only if next is list
                if i + 1 < len(lines) and (UL.match(lines[i + 1]) or OL.match(lines[i + 1])):
                    i += 1
                    continue
                break
            mu, mo = UL.match(line), OL.match(line)
            if not (mu or mo):
                break
            indent = len(re.match(r"^(\s*)", line).group(1))
            depth = max(0, (indent - base_indent) // 2)
            if mo:
                items.append((depth, True, mo.group(3)))
            else:
                items.append((depth, False, mu.group(2)))
            i += 1
        return self._render_list(items) + "\n", i

    def _render_list(self, items) -> str:
        # Normalize depths so each item is at most one level deeper than the
        # previous item (Markdown indentation can jump by 2+ spaces).
        norm = []
        prev = 0
        for depth, ordered, text in items:
            if depth > prev + 1:
                depth = prev + 1
            norm.append((depth, ordered, text))
            prev = depth

        out = []
        stack: list[bool] = []

        def open_env(ordered: bool):
            stack.append(ordered)
            out.append("\\begin{enumerate}" if ordered else "\\begin{itemize}")
            out.append("\\setlength{\\itemsep}{2pt}")

        def close_env():
            ordered = stack.pop()
            out.append("\\end{enumerate}" if ordered else "\\end{itemize}")

        for depth, ordered, text in norm:
            while len(stack) > depth + 1:
                close_env()
            if len(stack) == depth + 1 and stack and stack[-1] != ordered:
                close_env()
            while len(stack) < depth + 1:
                open_env(ordered)
            out.append("\\item " + inline_to_tex(text))
        while stack:
            close_env()
        return "\n".join(out)

    @staticmethod
    def _verbatim(code: str, lang: str) -> str:
        code = normalize_unicode(code)
        if lang:
            return (
                f"\\begin{{lstlisting}}[language={lang}]\n{code}\n\\end{{lstlisting}}\n"
            )
        return f"\\begin{{lstlisting}}[language={{}}]\n{code}\n\\end{{lstlisting}}\n"


def render_footnotes(footnotes: list[tuple[str, str]]) -> str:
    if not footnotes:
        return ""
    out = ["\\begin{footnotesize}", "\\begin{itemize}\\setlength{\\itemsep}{1pt}"]
    for label, text in footnotes:
        out.append("\\item[\\textsuperscript{" + escape_text(label) + "}] " + inline_to_tex(text))
    out.append("\\end{itemize}")
    out.append("\\end{footnotesize}")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def safe_name(path: str) -> str:
    stem = Path(path).stem
    stem = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", stem)
    return stem.strip("_")


def convert_file(rel_path: str, chapter_label: str, part: str, base_heading: int,
                 strip_first_title: bool = True, card_mode: bool = False) -> str | None:
    src = REPO / rel_path
    if not src.exists():
        print(f"  ! missing: {rel_path}")
        return None
    fm, body = read_frontmatter(src)
    conv = Converter(base_heading_level=base_heading)
    conv.card_mode = card_mode
    tex = conv.convert_body(body, strip_title=strip_first_title)
    tex += render_footnotes(conv.footnotes)
    fname = f"{chapter_label}-{part}-{safe_name(rel_path)}.tex"
    (CHAPTERS / fname).write_text(tex, encoding="utf-8")
    return fname


def main(argv: list[str] | None = None) -> None:
    global REPO, OUT, CHAPTERS, IMAGES, _ARGS
    args = _parse_args(argv)
    _ARGS = args
    REPO = Path(args.source)
    OUT = Path(args.output)
    CHAPTERS = OUT / "chapters"
    IMAGES = OUT / "images"

    if not REPO.is_dir():
        raise SystemExit(f"Source directory not found: {REPO}")

    specs = resolve_specs(args)
    CHAPTERS.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)
    manifest = []
    for ci, spec in enumerate(specs):
        spec.setdefault("number", ci)
        spec.setdefault("title", f"Chapter {ci}")
        spec.setdefault("index", None)
        spec.setdefault("sections", [])
        spec.setdefault("cards", [])
        manifest.append(f"% ---- {spec['title']} ----")
        if spec["number"] is None:
            manifest.append(f"\\chapter*{{{spec['title']}}}")
            manifest.append(f"\\addcontentsline{{toc}}{{chapter}}{{{spec['title']}}}")
            manifest.append(f"\\markboth{{{spec['title']}}}{{{spec['title']}}}")
            # Unnumbered chapters: keep their sections unnumbered too.
            manifest.append("\\setcounter{secnumdepth}{0}")
        else:
            manifest.append(f"\\chapter{{{spec['title']}}}")
            manifest.append("\\setcounter{secnumdepth}{3}")

        if spec["index"]:
            fn = convert_file(spec["index"], f"ch{ci:02d}", "idx", base_heading=1)
            if fn:
                manifest.append(f"\\input{{chapters/{fn}}}")

        for si, sec in enumerate(spec["sections"]):
            fn = convert_file(sec, f"ch{ci:02d}", f"s{si:02d}", base_heading=1)
            if fn:
                manifest.append(f"\\input{{chapters/{fn}}}")

        if spec["cards"]:
            manifest.append("\\begin{appendixcards}")
            for group_title, cards in spec["cards"]:
                manifest.append(f"\\section{{{group_title}}}")
                for card in cards:
                    fn = convert_file(card, f"ch{ci:02d}", "card", base_heading=3,
                                      strip_first_title=False, card_mode=True)
                    if fn:
                        manifest.append(f"\\input{{chapters/{fn}}}")
            manifest.append("\\end{appendixcards}")
        manifest.append("")

    (CHAPTERS / "_manifest.tex").write_text("\n".join(manifest), encoding="utf-8")
    print(f"Generated {len(list(CHAPTERS.glob('*.tex')))} files.")

    # Copy images referenced by ![[name]].
    copy_images()


def copy_images() -> None:
    idx: dict[str, Path] = {}
    for p in REPO.rglob("*"):
        if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".pdf", ".svg", ".gif"):
            idx.setdefault(p.name, p)
    count = 0
    for name, src in idx.items():
        dst = IMAGES / name
        if not dst.exists():
            shutil.copy2(src, dst)
            count += 1
    print(f"Copied {count} images.")


if __name__ == "__main__":
    main()
