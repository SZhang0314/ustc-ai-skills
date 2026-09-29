---
name: english-book-translation
description: 把英文书籍/教材 PDF 翻译成中英逐段对照、带术语脚注和原书插图的注释版 PDF（LaTeX 排版）。Use when 用户要求翻译英文书籍、英文教材、英文专著成中文，或提到"英文书籍翻译"、"中英对照"、"双语对照"、"翻译 PDF 书籍"、"术语注释版"。Only for 整本书籍级翻译任务，不适用于单段/单页短文翻译。
---

# 英文书籍翻译（中英对照注释版 PDF）

把一本英文书（PDF）加工成**逐段中英对照 + 术语脚注 + 原书插图 + 术语表**的 LaTeX 排版 PDF。
本 skill 由 Kittel《固体物理导论》（997 页、22 章、约 17 万词）全书翻译项目沉淀而来，
所有脚本在 `scripts/` 下，可直接复用。

## 依赖

- Python 3 + `PyMuPDF`（`pip install pymupdf`）
- TeX Live（需 `xelatex`，`adjustbox`/`booktabs`/`longtable` 等 CTAN 包）
- 中文字体：`SimSun`（宋体）、`SimHei`（黑体）、`FandolKai`（楷体，TeX Live 自带）
- 大批量翻译用并行 subagent 分发

## 工作流总览（六阶段）

```
原书 PDF
  │ ①提取    extract.py          → extracted/chNN.json（章节段落）
  │ ②拆分    split_chapters.py   → raw/chNN_partK.txt（≤33KB/片）
  │ ③翻译    并行 subagent       → src/chNN_partK.json → merge_parts.py 合并
  │ ④清理    clean_toc.py / clean_lead.py（去章首目录噪声）
  │ ⑤插图    extract_figures.py → attach_figures.py（原书图裁剪并绑定图题）
  │ ⑥排版    render.py → build.py（分章 PDF）→ build_book.py（整书 PDF）
  │          （normalize.py 提供文本/数学两套 Unicode→LaTeX 映射，被 render 共用）
```

## ① 内容拆解与提取

`extract.py`：用 PyMuPDF 逐页抽文本，按章切分（先定位每章起始页），去页眉页脚与页码，
按空行分段，输出 `extracted/chNN.json`。

- 章节起始页需要先用正则扫描正文 `^CHAPTER \d+` 定位（目录页的 "Chapter N" 不算）。
- 单独再生成一份 `raw/chNN.txt`（带 `===PAGE n===` 标记）供翻译 agent 阅读。

## ② 翻译（关键：分片并行）

**格式规范**见 `reference/AGENT_SPEC.md`，核心是每章一个 JSON：

```json
{
 "chapter": 1, "title_en": "Crystal Structure", "title_zh": "晶体结构",
 "blocks": [
   {"type":"heading","level":1,"en":"SECTION TITLE","zh":"小节标题"},
   {"type":"para","en":"<英文原段>","zh":"<中文全译>",
    "terms":[{"en":"lattice","zh":"点阵","note":"一两句术语释义"}]},
   {"type":"equation","latex":"n\\lambda=2d\\sin\\theta","num":"(2)",
    "zh_note":"布拉格定律"},
   {"type":"figcap","en":"Figure 1 ...","zh":"图 1 ..."},
   {"type":"table","en":"TABLE 1 ...","zh":"表 1 ...",
    "latex":"\\begin{tabular}{lcc}\\toprule ... \\bottomrule\\end{tabular}"}
 ]
}
```

规则要点：

- **逐段对照**：一个 `para` = 一段完整英文原文 + 对应中文全译，不合并段落。
- **全文翻译**：正文、图题、表题、小结、习题都要译，不遗漏。
- **术语**：每章 15–40 个核心术语，`zh` 字段必须含中文译名（渲染时自动加脚注）。
- **公式全部用 LaTeX**（详见 `reference/AGENT_SPEC.md` 规则 6）：
  - 行内公式写在 `en`/`zh` 文本里，用 `$...$` 包裹（`$E=\hbar\omega$`、`$a_1$`、`$\sqrt{3}/2$`）。
  - 原书单独成行的编号公式用 `equation` block（`latex` 字段只写数学模式本体，`num` 放原书编号）。
  - **禁止 Unicode 公式散落正文**（a₁、½、θ、ω 这类一律改为 `$...$`）。
  - 渲染端会**先占位保护** `$...$`/`\[...\]`/`$$...$$`/`\(...\)` 再转义其余文本，公式不会被破坏。
- **表格用 LaTeX 排版**：`table` block 除中英表题外给 `latex` 字段（完整
  `tabular`，booktabs 风格）；渲染器自动把宽表缩放到版心内；跨页表用 `longtable`。

### ⚠️ 最重要的经验：必须分片

subagent 读完整章（>40KB 原文）后常常**耗尽输出预算而不写文件**（任务显示 completed 但文件不存在）。
可靠做法：

1. `split_chapters.py` 把每章原文切成 **≤33KB/片**（按页边界切）；
2. 每个片派一个 subagent 翻成 `src/chNN_partK.json`（只含 `blocks`）；
3. `merge_parts.py` 按序合并成 `src/chNN.json`；
4. 每次合并后校验 `json.load`，缺片的章节立即重派。

提示词要点：让 agent **先写文件再校验**（"WRITE THE FILE FIRST, then validate"），
并要求回报 blocks 数量。对没写文件的 agent，重开新会话比 resume 更可靠。

## ③ 清理章首目录噪声

原书每章常有一页章内目录（标题列表 + 习题题名），抽取后会被误当正文/标题，
在渲染的目录里造成重复条目。两层清理：

- `clean_toc.py`：删除章首 ≥4 个"标题/短题名"的连续块，且其中 ≥3 个标题在后文重复出现。
- `clean_lead.py`：删除首个实质段落之前的目录残片（如 "PROBLEMS"、"1. xxx"、"H  Cooper Pairs"）。

**清理后必须抽查各章首块**是否为真实正文（`en` 长度 > 200 的段落），
防止把真正的开篇段误删。

## ④ 原书插图提取与绑定

`extract_figures.py`：

- 每页找图题块（`Figure \d+`），图区域 = 图题上方、到上一个文本块底部之间的内容
  （图像 + 矢量图形 + 图内标注一起），200 DPI 裁剪为 PNG。
- **连续图题**（如 6a/6b 共用一幅图）：若图题上方无图像内容且间隔 <60pt，
  则复用上一条图题的裁剪图 —— 否则会被零高度跳过，导致后续所有图号错位。

`attach_figures.py`：按"章内页范围 + 图号 + 顺序"把 PNG 绑定到各章 JSON 的 `figcap` 块
（写入 `block['png']`）。同一 PNG 允许多条图题共用（对应原书共图）。

## ⑤ LaTeX 排版

`render.py`（JSON → .tex）+ `preamble.tex`（公共导言）+ `build.py`（编译）：

- `xeCJK` + SimSun/SimHei/FandolKai；`graphicx` 插图；`adjustbox` 缩放宽表。
- 两个段落环境：`enpara`（英文，深灰）→ `zhpara`（中文，深蓝，行距 1.35）→ `\pairrule` 分隔线。
- `\term{术语}{释义}`：术语红色加粗并自动生成编号脚注（每章只注首次出现）。
- **公式**：`equation` block → `equation*` + `\tag{num}`（原书编号）；文本里的
  `$...$`/`\(...\)`/`$$...$$`/`\[...\]` 用占位符保护后原样还原。
- **图**：图+题注整体包在 `\begin{minipage}{\linewidth}` 里，图在图题上方
  （`width=0.86\linewidth, height=0.5\textheight, keepaspectratio`）。
- **表**：表题在上 + `\adjustbox{max width=\linewidth}{tabular}` 自动缩放；
  `longtable` 检测到时不套 minipage（longtable 自己跨页）。
- 章节：`\chapter`/`\section`/`\subsection`；中文章名下附斜体英文原名。

`build.py`：编译单章（render → xelatex → 拷贝到 build/）。
`build_book.py`：整书（封面 + 中文目录 + 全部章 + 书末术语表），编译 3 遍生成目录。
`normalize.py`：文本模式（缺字符号→`$宏$`）与数学模式（Unicode→纯宏，无 `$`）两套映射，
被 render/build_book 共用。

### ⚠️ 排版踩坑（务必遵守）

- **防重叠总则**：图/表块整体包在 `\begin{minipage}{\linewidth}` 里——minipage 不可拆分，
  剩余空间放不下就整块移到下页，**绝不会与正文/页脚/页眉重叠**；**禁止用 `samepage` 环境**
  （强行不换页会 Overfull \vbox，把内容挤出页底与页脚重叠）。
- **图片高度上限**：`height=0.5\textheight` + `keepaspectratio`，保证 图+题注 < 一页高度。
- **宽表格**：渲染器自动套 `\adjustbox{max width=\linewidth}` 缩到版心内；
  跨页表用 `longtable`（不可放进 minipage/box，否则断页错乱）。
- **章标题 `\titlespacing` 顶距不得为负**（负值会把章名顶进页眉造成重叠）。
- **页眉标题过长会溢出版心**：整书/合集渲染时把 `\markboth` 标题截断到 ~40 字符。
- **导言必须保留** `\emergencystretch=3em`、`\tolerance=2000`、孤寡行 penalty：
  避免长公式/长词行溢出伸进页边。
- **直接用 `xelatex` 编译**，不要用 `latexmk -outdir`（Windows 下 `-outdir` 带反斜杠会失败）。
- **编译前把 `preamble.tex` 拷到 tex 目录**，否则用到的是旧导言（曾导致目录名、页眉改动不生效）。
- **字体缺字**：Times New Roman 没有 ⟨⟩⪡ⱼ𝛌⩽≪≫。`normalize.py` 文本模式已映射；
  先编译探针确认字体支持，再补映射（⟨→<，⪡→<<，ⱼ→j，𝛌→λ，⩽→≤）。
- **控制台是 GBK**，无法打印 CJK/特殊字符：验证结果一律**写文件再读**，
  或打印 `encode('unicode_escape')`，不要依赖控制台直接输出。
- 正文转义只做最小集（`\ & % # _ { } ~ ^ $`），且**数学 span 先用占位符保护、
  转义完再还原**——顺序反了会把 `$\hbar$` 的 `\`、`{`、`}` 转义掉报 "Missing $ inserted"。

## ⑥ 最终校验清单

1. 所有章 JSON 合法（`json.load` 通过）、无缺章。
2. 各章首块是真实正文（不是目录残片）。
3. 编译零错误；PDF 页数、嵌入图数（`page.get_images()`）符合预期。
4. 书内无 U+FFFD 等缺字字符。
5. 抽查若干图题页：图在图题正上方；多图共题的章（如含 6a/6b 的章）映射无错位。
6. **编译日志扫描**：`Overfull \vbox` 为 0，`Overfull \hbox (>5pt)` 为 0
   （正则 `Overfull \\hbox \(([\d.]+)pt`）——非 0 说明行/块溢出，会与页边或页脚重叠，必须修。
7. **公式抽查**：display 公式是真实 LaTeX 且编号（`\tag`）与原书一致；
   正文无散落 Unicode 公式（a₁、½、√ 残留 = agent 未按规范，重翻该段）；表格是真实 `tabular` 且未溢出版心。
8. **目视抽查**：抽若干页用 PyMuPDF 渲成 PNG，确认文字/图/表/页眉页脚互不重叠。

## 交付物形态

```
build/
  ├── <书名>_中英对照注释版.pdf   ← 整书：封面+目录+正文+术语表
  └── chNN.pdf                    ← 分章 PDF
```

## 脚本路径调整

`scripts/` 内脚本的 `SRC`（原书 PDF 路径）、输出目录和 `CHAPTER_STARTS`/`CH_PAGES`
（章节起始页）是按上次项目硬编码的，用于新书时先改这三处。
