---
name: english-papers-translation
description: 把一批（多篇）英文文献/论文 PDF（文件名杂乱、来源不一）整理后逐篇中英逐段对照翻译，提取原文献插图并绑定到图题，自动识别并标注摘要，最终合成一份带中英双语目录（标题中英+年份+页码）的 LaTeX/PDF 合集。Use when 用户要求翻译"多篇文献"、"一批论文"、"英文文献合集"、"文献翻译成中文"、"中英对照论文集"、"把文件夹里的论文翻译并合并成 PDF"，或提到"整理文献翻译"、"多篇 paper 翻译"。Only for 多篇文献批量翻译任务；单篇论文或整本书翻译请用 english-book-translation。
---

# 多篇英文文献中英对照翻译合集

把一文件夹里**命名杂乱**的英文论文 PDF（Zotero 导出、期刊下载等），整理、逐篇
**中英逐段对照**翻译、提取并绑定**原文献插图**、标注**摘要**，最终合成一份带
**中英双语目录**（标题中英 + 年份 + 页码）的 PDF。本 skill 由 38 篇
"爱因斯坦-德哈斯效应"文献翻译项目沉淀而成，脚本在 `scripts/` 下可直接复用。

## 依赖

- Python 3 + `PyMuPDF`（`pip install pymupdf`）；可选 `Pillow`（插图空白检测）
- TeX Live（需 `xelatex`）
- 中文字体：`SimSun`（宋体）、`SimHei`（黑体）、`FandolKai`（TeX Live 自带）
- 大批量翻译用**并行 subagent** 分发（每片一个 agent）

## 工作流总览（七阶段）

```
杂乱 PDF 文件夹
  │ ①盘点   列文件、算 MD5 去重、核对年份        → papers.py（元数据）
  │ ②提取   extract_papers.py                    → raw/pNN.txt + raw/pNN_partK.txt
  │ ③翻译   并行 subagent（每片一个）             → src/pNN_partK.json
  │        merge_papers.py 合并                  → src/pNN.json
  │ ④插图   extract_figures.py + attach_figures.py → figures/*.png + 写入 block['png']
  │ ⑤摘要   abstract_detect.py（渲染时调用）
  │ ⑥排版   render_collection.py + preamble.tex   → tex/collection.tex
  │ ⑦编译   build.bat（xelatex ×3）                → build/<合集名>.pdf
```

## 快速开始（项目初始化）

```bash
# 1) 在目标输出目录初始化：拷入脚本、规范、导言模板、papers.py 模板
python <skill>/scripts/setup_project.py "<项目目录>/translation"
# 2) 编辑 <项目目录>/translation/papers.py（改 BASE/OUT/PAPERS/合集标题）
# 3) 依次运行（cwd = <项目目录>/translation）：
python extract_papers.py
#   → 并行 subagent 翻译每一片（见 ③），产出 src/pNN_partK.json
python merge_papers.py
python extract_figures.py
python attach_figures.py
python render_collection.py
python prepare_tex.py
cd tex && build.bat
```

> 之所以把脚本拷到 `<OUT>`：脚本之间用 `from papers import ...` /
> `from normalize import ...` 相互引用，**同目录**运行最省事。

## ① 盘点与元数据（去重是第一步）

文件夹常有两类命名：`NN_年份_标题.pdf` 与 `XXX_年份_标题.pdf`，且**同一篇文献
可能重复**。先做：

1. 列全部文件（含大小）；**用 MD5 找内容重复**（`Get-FileHash -Algorithm MD5`
   或 Python `hashlib`）。文件名年份冲突时，以**真实发表年**为准（查 Crossref：
   `https://api.crossref.org/works?query.bibliographic=<title>&rows=1`）。
2. 与用户确认重复项如何取舍（推荐每组只留一份、以真实年份为准）。
3. 生成 `papers.py`（见 `scripts/papers_meta_template.py`）：

```python
BASE = r'...'          # PDF 所在文件夹
OUT  = os.path.join(BASE, 'translation')   # 全部中间产物输出目录
PAPERS = [
    ("01_2007_", 1, 2007, "Influence of photon angular momentum on ..."),  # (文件名前缀, 序号, 年份, 英文标题)
    ...
]
def find_pdf(prefix):  # 按前缀在 BASE 中找唯一 PDF
    ...
```

**关键经验**：

- 有些 PDF 会**损坏**：文件头全为 0 字节，或缺 xref/trailer（PyMuPDF 报
  `invalid key in dict` / `no objects found`）。`os.path.getsize` 正常也不代表可读。
  **先 `fitz.open` 逐个试开**，损坏的立即反馈用户重新下载，不要跳过。
- 有中文字符的输出目录/文件名在 **GBK 控制台**下打印会乱码或抛
  `UnicodeEncodeError`。**验证结果一律写文件再读**，或打印
  `encode('ascii','replace')` / `encode('unicode_escape')`，不要直接 print CJK。

## ② 正文提取与分片

`extract_papers.py`（把 `BASE/OUT/MAXBYTES` 改成本项目）：

- PyMuPDF 逐页抽文本，加 `===PAGE n===` 标记；清理 `\u2003`、`\u00a0`、连字
  `ﬁﬂ` 等。
- 每篇输出 `raw/pNN.txt`（全文，带页标记）与 `raw/pNN_part1..K.txt`（**按页边界**
  切成 **≤33KB/片**）。同时写 `manifest.json`。

> 分片是硬性要求：subagent 读完整篇（>40KB）后常**耗尽输出预算而不写文件**。

## ③ 并行翻译（核心）

**格式规范**见 `reference/AGENT_SPEC.md`。每片产出一个 `src/pNN_partK.json`：

```json
{
 "num": 7, "year": 2012,
 "title_en": "...", "title_zh": "中文标题", "part": 1,
 "blocks": [
   {"type":"heading","level":1,"en":"SECTION TITLE","zh":"小节标题"},
   {"type":"para","en":"<英文原段>","zh":"<中文全译>",
    "terms":[{"en":"demagnetization","zh":"退磁","note":"一两句术语释义"}]},
   {"type":"equation","latex":"M(t)=M_0+\\Delta M\\,e^{-t/\\tau}","num":"(1)",
    "zh_note":"退磁的指数衰减模型"},
   {"type":"figcap","en":"FIG. 1. ...","zh":"图 1. ..."},
   {"type":"table","en":"TABLE I ...","zh":"表 I ...",
    "latex":"\\begin{tabular}{lcc}\\toprule ... \\bottomrule\\end{tabular}"}
 ]
}
```

规则要点：

- **逐段对照**：一个 `para` = 一段完整英文原文 + 对应中文全译，不合并、不漏段。
- **全文翻译**：正文、各级标题、图题、表题、致谢、附录都译；**参考文献列表整条跳过**。
- **段落拼接**：PDF 抽取常把一段拆成多行短行，需合并并修断行连字符
  （`demagnetiza-\ntion` → `demagnetization`）；跨页续段也要合并。
- **术语**：每篇 15–40 个核心术语，`zh` 字段含中文译名（渲染时自动加脚注标红）。
- **公式全部用 LaTeX**（详见 `reference/AGENT_SPEC.md` 规则 7）：
  - 行内公式写在 `en`/`zh` 文本里，用 `$...$` 包裹（`$E=\hbar\omega$`、`$a_1$`、`$\sqrt{3}/2$`）。
  - 原文单独成行的编号公式用 `equation` block（`latex` 字段只写数学模式本体，`num` 放原文编号）。
  - **禁止 Unicode 公式散落正文**（a₁、½、θ、ω 这类一律改为 `$...$`）。
  - 渲染端会**先占位保护** `$...$`/`\[...\]`/`$$...$$`/`\(...\)` 再转义其余文本，公式不会被破坏。
- **表格用 LaTeX 排版**：`table` block 除中英表题外给 `latex` 字段（完整
  `tabular`，booktabs 风格）；渲染器自动把宽表缩放到版心内；跨页表用 `longtable`。
- **摘要**：作为正文第一段/首段翻译即可（渲染阶段会自动加"摘要 / Abstract"标注）。

派发提示词模板（每个片一个 subagent）：

```
You are translating a physics paper from English to Chinese for a bilingual PDF.
Work in directory: <OUT>
READ: 1) <OUT>/AGENT_SPEC.md  2) <OUT>/raw/pNN_partK.txt
Metadata: num=..., year=..., title_en="...", part=K
TASK: translate the ENTIRE source text paragraph-by-paragraph into JSON (block
types: para/heading/equation/figcap/table; ALL formulas in LaTeX $...$ or
separate equation blocks; tables with full tabular `latex`), WRITE to
<OUT>/src/pNN_partK.json
CRITICAL: follow AGENT_SPEC.md; WRITE THE FILE FIRST (json.dump ensure_ascii=False)
then validate with json.load; title_zh = Chinese title.
Reply with ONLY: file path, number of blocks, total english chars.
```

- **先写文件再校验**；对没写文件的 agent **重开新会话**比 resume 可靠。
- 每批约 8–10 个 subagent 并行；每批结束后 `json.load` 校验全部产物。
- 某些片可能整片都是参考文献 → `blocks` 为空是**正常**的。

合并：`merge_papers.py` 把 `src/pNN_part*.json` 按 part 号合并成 `src/pNN.json`，
标题取第一个非空 `title_zh`。合并后统计各篇 blocks 数（空篇需警惕是否漏译）。

## ④ 插图提取与绑定

**期刊版式差异大**，`extract_figures.py` 用"题注定位 + 图形簇聚类"策略：

- 收集页面所有 **drawing + image** 的 bbox（忽略极小的），按空间邻近**聚类**成图形簇。
- 每个 `FIG./Fig./Figure/Table N` 题注匹配**最近的图形簇**；
- **排除文内引用**（如 `Figure 1a depicts ...`）——用 `BODY_REF` 正则过滤。
- 邻近簇**按接触合并**（多面板图）；**大版面期刊（Nature/Science）**用整行合并；
- **同页相邻但各有题注的图不可合并**（用"该簇下方是否有自己的题注"判断）。

`attach_figures.py`：按题注里的**图号**把 PNG 绑定到对应 `figcap` 块的
`block['png']`；无图号的续图题复用上一张；写入 JSON。

**校验**：用 Pillow 算非白像素比例，**丢弃空白裁剪**；统计"含图页中图文同页"的比例。

**踩过的坑**：

- 有些论文的图题在翻译时被当成普通段落**漏译**（如 p37 的 4 条 `FIG.`）——
  合并后统计 `figcap` 数 vs 提取图数，缺的**手工补译图题**再绑定。
- 矢量图形（PRB 的 plots）`get_drawings()` 可能返回上千个 rect，聚类前先按尺寸过滤。

## ⑤ 摘要标注

`abstract_detect.py` 的 `detect(data)` 返回摘要所在 block 下标，兼容三种排布：

- **显式小标题** `Abstract` / `Abstract:` → 取其后首个实质段落；
- **行内前缀** `Abstract: ...` → 就是该段（渲染时去掉前缀）；
- **无标注** → 跳过开头的标题/作者/单位/日期/DOI/关键词行，取首个实质 `para`。

`render_collection.py` 在摘要段前插入 `\abstracthead`（中英标注"摘要 / Abstract"）。

## ⑥ LaTeX 排版

`render_collection.py`（JSON → 合集 .tex）+ `reference/preamble.tex` + `build.bat`。

- `xeCJK` + SimSun/SimHei/FandolKai；每篇文献一个 `\chapter`。
- **目录**：`\titlecontents{chapter}` + `\chapter[\texorpdfstring{...}{...}]{...}`，
  条目 = 中文标题 + 斜体英文标题 + （年份）；`\setcounter{tocdepth}{0}` 只列到章。
- `enpara`（英文，深灰）→ `zhpara`（中文，深蓝）→ `\pairrule` 分隔线。
- **公式**：`equation` block → `equation*` + `\tag{num}`（原文编号）；文本里的
  `$...$`/`\(...\)`/`$$...$$`/`\[...\]` 用占位符保护后原样还原。
- **图**：图+题注整体包在 `\begin{minipage}{\linewidth}` 里（图在图题上方）。
- **表**：表题在上 + `\adjustbox{max width=\linewidth}{tabular}` 自动缩放；
  `longtable` 检测到时不套 minipage（longtable 自己跨页）。
- `\abstracthead`：摘要的中英标注标题。
- **页眉**：`\fancyhead[L]{}` 留空，右页眉放当前文献标题（`\leftmark`）——
  不要放固定合集名；渲染时 `\markboth` 标题截断到 ~40 字符防溢出版心。

### ⚠️ 排版踩坑（务必遵守）

- **防重叠总则**：图/表块整体包在 `\begin{minipage}{\linewidth}` 里——minipage 不可拆分，
  剩余空间放不下就整块移到下页，**绝不会与正文/页脚/页眉重叠**；**禁止用 `samepage` 环境**
  （强行不换页会 Overfull \vbox，把内容挤出页底与页脚重叠）。
- **图片高度上限**：`height=0.5\textheight` + `keepaspectratio`，保证 图+题注 < 一页高度。
- **宽表格**：渲染器自动套 `\adjustbox{max width=\linewidth}` 缩到版心内；
  跨页表用 `longtable`（不可放进 minipage/box，否则断页错乱）。
- **章标题 `\titlespacing` 顶距不得为负**（负值会把章名顶进页眉造成重叠）。
- **页眉标题过长会溢出版心**：渲染时把 `\markboth` 的标题截断到 ~40 字符。
- **导言必须保留** `\emergencystretch=3em`、`\tolerance=2000`、孤寡行 penalty：
  避免长公式/长词行溢出伸进页边。
- **直接用 `xelatex` 编译 3 遍**（生成目录/书签），不要用 `latexmk -outdir`。
- **编译前把 `preamble.tex` 拷到 tex 目录**，否则用到旧导言。
- **字体缺字**：Times New Roman 没有 ⟨⟩∇∼⊗∝∂ 及数学斜体/花体字母（U+1D400 区）。
  `normalize.py` 两套映射兜底：文本模式（`normalize`，Unicode→`$宏$`）用于普通文本残留；
  数学模式（`normalize_math`，Unicode→纯宏、无 `$`）用于公式内部残留。
  **公式本体应由 agent 直接写 LaTeX**，normalize 只是安全网。
- **控制台 GBK**：编译日志里的 `Missing character` 用正则提取码位写文件再读；
  目标是**零缺字**、无 U+FFFD 替换字符。
- 正文转义最小集（`\ & % # _ { } ~ ^ $`），且**数学 span 先用占位符保护、转义完再还原**，
  **再注入 `\term`**——顺序反了会把 `$\hbar$` 的 `\`、`{`、`}` 转义掉报 "Missing $ inserted"。

## ⑦ 最终校验清单

1. 所有 `src/pNN.json` 合法、无缺篇；每篇 `title_zh` 非空。
2. PDF 页数合理；`page.get_images()` 计数 ≈ 插图数；**无 U+FFFD、无 Missing character**。
3. 目录 38/ N 条，含中英标题、年份、页码，按年份排序。
4. "摘要 / Abstract"标注 = 篇数。
5. 抽查若干页：图在图题上方、图文尽量同页；页眉无固定合集名。
6. **编译日志扫描**：`Overfull \vbox` 为 0，`Overfull \hbox (>5pt)` 为 0
   （正则 `Overfull \\hbox \(([\d.]+)pt`）——非 0 说明行/块溢出，会与页边或页脚重叠，必须修。
7. **公式抽查**：display 公式是真实 LaTeX 且编号（`\tag`）与原文一致；
   正文无散落 Unicode 公式（a₁、½、√ 残留 = agent 未按规范，重翻该段）；表格是真实 `tabular` 且未溢出版心。
8. **目视抽查**：抽若干页用 PyMuPDF 渲成 PNG，确认文字/图/表/页眉页脚互不重叠。

## 交付物形态

```
<项目>/translation/
  ├── papers.py              # 元数据（文件名前缀→序号/年份/标题）
  ├── raw/pNN.txt, pNN_partK.txt
  ├── src/pNN_partK.json → pNN.json
  ├── figures/*.png + figures.json
  ├── tex/collection.tex + preamble.tex + build.bat
  └── build/<合集名>.pdf     ← 最终交付
```

## 脚本清单与路径调整

`scripts/` 下：

| 脚本 | 作用 |
|------|------|
| `setup_project.py` | 一键把脚本/规范/导言拷进项目 `<OUT>`，并生成 `papers.py` 模板 |
| `papers_meta_template.py` | `papers.py` 模板（`BASE/OUT/PAPERS/合集标题`） |
| `extract_papers.py` | 抽正文 + 分片 `raw/`，写 `manifest.json` |
| `merge_papers.py` | 合并 `src/pNN_part*.json` → `src/pNN.json` |
| `extract_figures.py` | 插图提取 → `figures/*.png` + `figures.json` |
| `attach_figures.py` | 按图号绑定插图到 `figcap` 块 |
| `abstract_detect.py` | 摘要定位（供渲染调用） |
| `normalize.py` | 缺字符号 → LaTeX 宏映射（文本模式 `normalize` / 数学模式 `normalize_math`） |
| `render_collection.py` | JSON → `tex/collection.tex`（含封面/目录/摘要标注） |
| `prepare_tex.py` | 拷 `preamble.tex` + 插图到 `tex/` |
| `build.bat` | `xelatex` 编译 3 遍 |

各脚本顶部的 `BASE`/`OUT`/`PAPERS`/`MAXBYTES` 按上次项目硬编码；新项目先跑
`setup_project.py`，再改 `<OUT>/papers.py` 即可，**其余脚本无需改路径**。

