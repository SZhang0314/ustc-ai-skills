---
name: 讲义总结
description: 把课程 PPT（.pptx）与教材/习题解答 PDF 总结制作成一份 LaTeX 排版的中文讲义 PDF（包含内容精讲、例题及解答、习题及解答），电路图/逻辑图按原比例整页截图插入。Use when 用户要求"总结 PPT 成讲义"、"PPT+教材做讲义"、"制作讲义 PDF"、"讲义总结"、"课件总结成 LaTeX"，且需要内容精讲+例题+习题三部分、xelatex 编译、幻灯片截图插图。不适用于实验报告（用 make_report）、整本书翻译（用 english-book-translation）。
---

# Skill: 讲义总结

把课程 **PPT（.pptx）** 与 **教材 PDF（含配套习题解答 PDF）** 总结加工成一份
**LaTeX 排版的中文讲义 PDF**，包含三大块：**内容精讲、例题及解答、习题及解答**。
电路图、逻辑图、真值表、卡诺图等**直接按原比例整页截图**插入讲义。

本项目沉淀自《组合逻辑电路》（4 份 PPT + 康华光《电子技术基础·数字部分》第 7 版第 4 章
+ 配套《学习辅导与习题解答》）讲义制作。

## 依赖

- Python 3 + `pymupdf`、`python-pptx`、`pillow`、`numpy`、`pywin32`、`rapidocr-onnxruntime`
- TeX Live（需 `xelatex`）；中文字体由 ctex 自动调用（SimSun 等）
- **WPS Office**（Windows 下无 PowerPoint/LibreOffice 时的 PPTX 渲染方案）

## 工作流总览（七阶段）

```
PPT + 教材PDF + 习题解答PDF
  │ ①识别源材料    改名复制到工作目录（避免长中文文件名出错）
  │ ②提取PPT文字   pptx_text.py        → pptN.txt（文本/表格/备注）
  │ ③渲染PPT为图   wps_ppt2pdf.py + PyMuPDF → slides/pptN_KK.png（每页 2.5x）
  │ ④提取教材文字  pdf_probe.py 判定扫描件 → render_pages.py + ocr_batch.py → OCR 文本
  │ ⑤截图插图     make_figs.py（整页截图+抹页码+裁白边）→ figs/*.png
  │ ⑥LaTeX 排版   preamble.tex + 主tex + modules/examples/exercises.tex
  │ ⑦编译校验     xelatex ×2~3 遍 → 页数/图数/U+FFFD/引用校验
```

## ① 识别源材料

1. 用 `Get-ChildItem -LiteralPath` 找到含 PPT/PDF 的文件夹（控制台显示中文会乱码，属 GBK 显示问题，路径本身正常）。
2. **把文件改名复制到工作目录**（如 `ppt1.pptx`…`book5.pdf`），避免长中文文件名在 Python/COM 调用中出错。
3. 先读 PPT 提取的文本确定知识范围，再决定教材要 OCR 哪些章节。

## ② 提取 PPT 文字（`scripts/pptx_text.py`）

- 输出每页 `[TEXT]`（文本）、`[TABLE]`（表格）、`[PICTURE]`（图片占位）、`[NOTES]`（演讲者备注）。
- **备注常含最完整的讲解**（PPT 正文常只有提纲式短句），必须通读。
- `python-pptx` 读不到的图形（AutoShapes/Lines/Group 组合的矢量图）不会出现在文本里，
  只能靠渲染成图后截图。

## ③ 渲染 PPT 为图（`scripts/wps_ppt2pdf.py`）

- 系统常**没有 PowerPoint 和 LibreOffice**，但可能装了 WPS（注册表
  `App Paths\powerpnt.exe` 指向 `wps.exe`）。用 WPS COM 自动化转 PDF：
  ```python
  app = win32.Dispatch("Kwpp.Application")
  try: app.Visible = False        # WPS 下会抛 com_error，必须 try/except 跳过
  except Exception: pass
  pres = app.Presentations.Open(src)   # 不要传 ReadOnly/WithWindow 参数
  pres.SaveAs(dst, 32)                 # 32 = ppSaveAsPDF
  ```
- 转出的 PDF 用 PyMuPDF 按 **2.5x** 渲染成每页 PNG（文本在 PDF 中仍清晰）。
- WPS 渲染保留全部矢量图形（逻辑门、连线、框图），这是截图插图的来源。

## ④ 提取教材文字（扫描件 → OCR）

1. **先用 `pdf_probe.py` 判定**：`textlen=0` 即扫描件，无文字层，必须 OCR。
2. **确定页码偏移**：教材 PDF 的物理页 ≠ 印刷页码。OCR 几页开头对比页眉页码
   （如印刷 p140 在物理 p170，则偏移 = +30），再按目录换算章节页码范围。
3. 扫描件无书签（`TOC entries: 0`）时，用 `render_pages.py` 渲染目录页 → OCR 目录
   得到章节起始页；或按关键词逐段 OCR 定位。
4. `ocr_batch.py` 批量 OCR 整章，输出带 `===== PAGE n =====` 标记的 UTF-8 文本。

## ⑤ 截取幻灯片插图（`scripts/make_figs.py`）⚠️ 最重要的坑

用户要求"电路、逻辑图直接按照原比例截图"。**三种裁法只有一种可靠**：

| 裁法 | 结果 |
|------|------|
| 按固定比例（top_frac/bottom_frac）裁竖条 | ❌ 可能把文字/图截成一半 |
| 按 python-pptx 形状 bbox 并集裁 | ❌ **占位符形状 left/top 返回 None**，主图漏裁，trim 后只剩小碎片 |
| **整页截图 + 抹掉页码 + 裁四周白边** | ✅ 任何内容都不截断 |

可靠做法（`make_figs.py` 已实现）：
1. **整页幻灯片截图**（含标题、全部图形与文字）；
2. 从 PPTX 读**页码/页脚形状的实际 EMU 坐标**（右下角 `left>11e6, top>6.2e6`），按
   `像素 = EMU × (图宽/幻灯片EMU宽)` 换算后**精确涂白**页码，不误伤图形；
3. `trim_white`（阈值 248，pad 10px）只裁四周白边，**不触碰墨迹**。

选图依据：通读 PPT 文本后，为每张要引用的图登记 `(幻灯片png文件名, ppt序号, 页码)`，
并给讲义里起的图名（如 `fig_mux41`）。**用 OCR 抽查每张截图**确认内容完整（能读到图内标注文字），
墨迹密度 <1% 说明裁空了。

## ⑥ LaTeX 排版

目录结构（模板见 `templates/preamble.tex`）：

```
讲义目录/
├── preamble.tex      ← 导言（ctex + tcolorbox + 例题/习题环境）
├── main.tex          ← 封面、目录、前言、第1~3章
├── modules.tex       ← 常用模块章（编码器/译码器/选择器/比较器/加法器…）
├── examples.tex      ← 例题及解答
├── exercises.tex     ← 习题及解答
└── figs/*.png        ← 幻灯片截图
```

- **主文件写法**：`\documentclass[11pt,a4paper]{article}` + `\input{preamble.tex}`；
  preamble 只含 packages（含 `\tcbuselibrary{breakable,skins}`）与格式定义。
- **分文件**：每章/每部分一个 tex，用 `\input` 串联，便于分段编写与修改。
- **环境**：`keybox`（知识点框）、`exbox`（方法框）、`example`+`solution`（例题）、
  `exercise`+`exsolution`（习题），均为 tcolorbox 或简单加粗标题环境。
- **插图**：`\includegraphics[width=0.9\linewidth,height=0.42\textheight,keepaspectratio]`
  保持原比例；双图并排用 `minipage` 0.49\textwidth + `\captionof{figure}`。
- **公式**：直接用 LaTeX 数学语法（$\ov{A}$、$\XOR$）；表格用 `tabular`。
- **目录/页眉**：`\markboth` 设页眉右标；`\tableofcontents` 需编译 2~3 遍。

### ⚠️ 排版踩坑（务必遵守）

- **xelatex 必须在讲义目录内运行**（用 workdir），**不要用 `-output-directory`**——
  它会破坏 `figs/` 相对路径，报 "Unable to load picture"。
- `tcolorbox` 的 `breakable` 必须 `\tcbuselibrary{breakable}` 显式加载。
- **避免 `enumerate*`**（需 enumitem `[inline]` 且易错），行内编号直接写
  `（1）…（2）…` 纯文本。
- **自定义环境的 `\begin{}/\end{}` 必须配对**。编译报
  `\begin{exercise} ... ended by \end{exsolution}` 时，用正则计数定位：
  ```powershell
  $raw=[IO.File]::ReadAllText($p)
  "be="+([regex]::Matches($raw,'\\begin\{exercise\}')).Count+" ee="+([regex]::Matches($raw,'\\end\{exercise\}')).Count
  ```
  数目不等即找错行修正（常见：复制上一题时忘改 `\end{}`）。
- **控制台是 GBK**，无法打印 CJK：验证结果一律写文件再读，或用 `-Encoding UTF8` 读回。
- 写 Python 脚本用 write 工具，**不要用 PowerShell here-string 内嵌中文**（引号/编码易炸）。

## ⑦ 编译与校验

```powershell
xelatex -interaction=nonstopmode main.tex    # 在讲义目录内，跑 2~3 遍出目录
```

校验脚本（PyMuPDF）：
```python
d = fitz.open("main.pdf")
tot = sum(len(d[i].get_images()) for i in range(d.page_count))   # 嵌入图数
bad = sum(1 for i in range(d.page_count) if "\ufffd" in d[i].get_text())  # 缺字
```

1. 编译零错误；`Select-String -Pattern "^!|Error|Undefined control"` 无输出。
2. PDF 页数符合预期、嵌入图数 = 截图数、无 U+FFFD。
3. 无未定义引用（log 中无 `undefined`）。
4. 抽查插图页：图完整（OCR 能读到图内标注）、页码已抹白。
5. 复制成品为 `<讲义名>.pdf` 交付。

## 讲义内容组织（三大部分）

1. **内容精讲**：按知识点逐条讲解定义、结构特点、分析/设计步骤、各模块功能与扩展，
   配 `keybox` 知识点框 + 幻灯片截图。**以 PPT 提纲为主线、教材正文补充深度**（PPT 备注里的
   讲解往往是教材原文的浓缩）。
2. **例题及解答**：从教材正文例题 + 辅导书"典型例题解析"中选代表性题目，按
   分析类/设计类/模块应用类/判别类分组，给完整解题过程。
3. **习题及解答**：从辅导书"习题全解"中选代表题，同样分组编排；
   结尾加一个"习题总结"框归纳解题方法论（分析题四步、设计题要点、判别准则、模块扩展方法）。
4. **前言**：说明材料来源（教材版次、页码范围、PPT 讲次）、三大部分结构与符号约定。
