---
name: make_report
description: Use when the user asks to generate a lab/experiment report ("实验报告", "科研论文格式的实验报告", "实验课讲义", "写实验报告") from lecture notes or lab handouts, and needs matching .docx, .pdf, and .tex outputs with abstract, keywords, introduction, purpose, principle with formulas, content with uncertainty analysis, data processing, conclusions, and references. Also use when the user mentions producing the same report in three formats or replicating the same layout across docx/pdf/tex.
---

# make_report — 科研论文格式实验报告生成

从实验课讲义等资料生成**科研论文格式**的实验报告，输出三份内容与排版一致的
文件：`.docx`、`.pdf`、`.tex`。数据可用计算机方法生成合理示例数据。

## 工作流（必须按顺序）

### 第 1 步：读取原材料
1. 用户会给出讲义/资料路径（PDF/DOCX/MD/TXT/图片）或直接粘贴内容。
2. 读取全部材料，提取：实验标题、目的、原理、仪器、步骤、思考题。
3. 若材料缺失某部分（如思考题），依据主题合理补全，并在该节开头用
   一段普通文字说明"本节思考题为根据实验主题补充"。

### 第 2 步：构建结构化内容 `report.json`
这是**唯一内容源**。三个生成器都只读取它，从而保证三份输出内容/排版一致。
参照 `reference/report_schema.md` 的完整 schema。要点：

- 所有数学公式使用 **LaTeX 数学语法**（`$...$` 行内，`$$...$$` 独立），
  docx 生成器会转成 OMML，LaTeX 生成器直接用，PDF 经 LaTeX 排版。
- 章节顺序固定：
  `摘要 → 关键词 → 引言 → 实验目的 → 实验原理 → 实验内容 → 实验数据处理
  → 实验结论与思考题 → 参考文献`
- **实验目的**：严格按原材料写，不要擅自扩充。
- **实验原理**：在材料基础上丰富，逐条概括，含公式推导与物理图像解释。
- **实验内容**：必须包含
  - 实验仪器（表格：名称/规格型号/数量/用途）
  - 实验设计，其中**必须有不确定度分析**：给出不确定度公式，
    并明确区分 **A 类不确定度**（统计，$u_A=s/\sqrt{n}$）与
    **B 类不确定度**（仪器/分辨率，$u_B=\Delta/\sqrt{3}$ 等），
    最后合成 $u_C=\sqrt{u_A^2+u_B^2}$ 与扩展不确定度 $U=k\,u_C$。
  - 实验具体内容（分小节，含操作步骤）。
- **实验数据处理**：含完整不确定度计算，含数据表格与必要的拟合/图像。
- **实验结论与思考题**：结论总结充分；每个思考题给出较丰富的解答
  （推导 + 文字解释）。
- **参考文献**：GB/T 7714 风格，与正文引用编号对应。

原始数据可用 `scripts/generate_data.py` 生成合理示例数据（见下）。

### 第 3 步：生成数据（如需要）
```powershell
python ".opencode/skills/make_report/scripts/generate_data.py" --config data_config.json --out data.json
```
`generate_data.py` 支持在配置里声明物理模型 + 噪声，输出示例数据与
不确定度。若不使用脚本，也可手写数据。生成的数值直接写入 `report.json`
的 `data_processing.tables` 与正文。

### 第 4 步：生成三份文件
```powershell
python ".opencode/skills/make_report/scripts/build_report.py" --input report.json --outdir .\output --formats docx,pdf,tex --title "实验题目"
```
- `build_report.py` 会：校验 JSON → 生成 `.tex` → 用 `xelatex` 编译
  `.pdf` → 用 `python-docx` 生成 `.docx`。
- 若缺少 `xelatex`，跳过 PDF 并在结尾提示用户安装 TeX Live / MiKTeX。
- 三份文件必须同名（除扩展名外）。

### 第 5 步：自检
- 确认三个文件都已生成且非空。
- 打开 `.tex` 确认无编译错误日志（输出目录下 `*.log`）。
- 报告完成情况，列出文件绝对路径。

## 排版规范（三份一致）
- 标题：黑体/`\heiti`，居中，小二。
- 一级标题：黑体，四号。
- 正文：宋体/`\songti`，小四，1.5 倍行距，首行缩进 2 字符。
- 公式居中编号；表格三线表；图注在图下，表注在表上。
- 页边距：上下 2.54cm，左右 3.17cm（Word 默认）。
- 参考文献：五号，悬挂缩进。

## 关键约束
- **不要**三份分别手写；一切从 `report.json` 生成，避免内容漂移。
- 公式语法在 JSON 里一律写成字符串，LaTeX 不转义反斜杠以外的内容；
  JSON 中反斜杠需写 `\\`（例如 `$\\bar{x}$`）。
- 不确定度必须**显式**给出 A 类/B 类公式与合成公式，不可只给结果。
- 文件名避免中文以外的特殊字符；含中文时 LaTeX 用 `ctex` 处理。

## 文件说明
- `reference/report_schema.md` — `report.json` 完整字段说明与样例。
- `scripts/build_report.py` — 主生成器（tex/pdf/docx）。
- `scripts/generate_data.py` — 示例数据与不确定度生成。
- `templates/report_template.tex.j2` — LaTeX 模板（供参考，生成器内置）。
- `reference/example_report.json` — 完整可运行示例。

## 常见问题
- **中文字体报错**：确认系统有 `SimSun`/`SimHei`/`SimKai`；模板用
  `ctex` + `fontset=windows`。
- **docx 公式**：生成器用 `latex2mathml` 或自带的 OMML 转换；若该库缺失，
  公式以 LaTeX 源码形式嵌入并提示用户，仍需保证 .tex/.pdf 正确。
- **编译超时**：`xelatex` 需跑两遍以生成目录/交叉引用，生成器已处理。
