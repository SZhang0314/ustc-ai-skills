# 论文翻译任务规范（中英逐段对照）

## 目标
把一篇物理论文的英文原文翻译成**中英逐段对照**的 JSON 文件，供 LaTeX 渲染成 PDF。

## 输入
- 你的分片原文文件：`raw/pNN_partK.txt`（`===PAGE n===` 为页分隔符，含页眉页脚/页码/参考文献噪声）。
- 论文元数据见 `papers.py` 或任务提示中给出的标题。

## 输出
生成一个 JSON 文件，写到指定的 `src/pNN_partK.json`，结构如下：

```json
{
 "num": 7,
 "year": 2012,
 "title_en": "Influence of photon angular momentum on ultrafast demagnetization in nickel",
 "title_zh": "光子角动量对镍中超快退磁的影响",
 "part": 1,
 "blocks": [
   {"type":"para","en":"<英文段落原文>","zh":"<中文译文>",
    "terms":[{"en":"demagnetization","zh":"退磁","note":"一两句中文术语解释"}]},
   {"type":"heading","level":1,"en":"EXPERIMENTAL SETUP","zh":"实验装置"},
   {"type":"equation","latex":"M(t)=M_0+\\Delta M\\,e^{-t/\\tau}","num":"(1)",
    "zh_note":"退磁的指数衰减模型"},
   {"type":"figcap","en":"FIG. 1. ...","zh":"图 1. ..."},
   {"type":"table","en":"TABLE I. ...","zh":"表 I. ...",
    "latex":"\\begin{tabular}{lcc}\\toprule ... \\bottomrule\\end{tabular}"}
 ]
}
```

## 规则
1. **逐段对照**：每个 `para` = 一段完整英文原文 + 对应中文全译。不要把多段合并，也不要漏段。
2. **全文翻译**：正文、各级标题、图题、表题、致谢、附录都要翻译。
   **参考文献列表（Bibliography/References 逐条条目）不翻译**，遇到整段参考文献直接跳过。
   作者单位、DOI、PACS 号可跳过或原样保留；**公式不跳过**（见规则 7）。
3. **段落切分**：以原文自然段为单位。PDF 抽取常把一段拆成多行短行，请合并成完整段落
   （去掉断行连字符，如 "demagnetiza-\ntion" → "demagnetization"）；跨页续段也要合并。
4. **标题**：章节内一级小标题（常全大写，如 "EXPERIMENTAL SETUP"）用 `level:1`；
   二级小标题（如 "Bragg Law"）用 `level:2`。
5. **图/表题**：`figcap`（英文以 FIG./Fig./Figure 开头）/ `table`。英文原文照录，
   中文给出完整翻译。**务必保留图号/表号**（供插图绑定）。
6. **专业术语**：每篇第一次出现的重要专业术语放入该段的 `terms` 数组，`note` 用
   1-2 句中文解释。`zh` 字段是术语的中文译名（渲染时自动加脚注并标红）。
   每篇 15-40 个术语为宜，优先核心概念。
7. **公式（全部用 LaTeX，禁止 Unicode 近似）**：
   - 行内公式写在 `en`/`zh` 文本里，用 `$...$` 包裹：如 `$E=\hbar\omega$`、`$a_1$`、
     `$\sqrt{3}/2$`。中文段里的行内公式同样用 `$...$`。
   - **禁止用 Unicode 上下标/希腊字母散落正文**（a₁、½、θ、ω 这类写法一律改为 `$...$`）。
   - 原文**单独成行的编号公式**单独用 `equation` block：`latex` 字段只写**数学模式本体**
     （不要写 `\begin{equation}` 包裹，渲染器会自动加），原书/原文编号放 `num`
     （如 `"(1)"`，渲染为 `\tag`）；可选 `zh_note` 用一句中文说明。
     公式是语言中性的，`equation` block 只渲染一次，中英共用。
   - **JSON 转义**：反斜杠写成 `\\`（解析后为单个 `\`），如 `"\\frac{1}{2}"`；
     不要过度转义（`"\\\\hbar"` 解析后是 `\\hbar`，会被当成换行）。
   - 正文中如确需美元符号（价格等），写成 `\$`（JSON 里 `"\\$"`）；
     **不要出现孤立的裸 `$`**（会打乱公式配对）。
   - 多步推导拆成多个 `equation` block；**避免单行公式过宽**——用
     `\begin{aligned}...\end{aligned}` 内部换行，公式行宽控制在约 60 字符以内。
8. **表格（用 LaTeX 排版，不要只给表题）**：`table` block 除中英表题外，给出 `latex` 字段：
   完整的 `\begin{tabular}{...}...\end{tabular}`（booktabs 风格：`\toprule`/`\midrule`/`\bottomrule`）。
   - 单元格内的数学用 `$...$`；单元格文本不要用 `<`、`>`、`&`、`%`、`#`、`_` 等需转义字符
     （`&` 只能作列分隔符）。
   - 渲染器会自动把过宽表格缩放到版心内（`adjustbox`），超长（跨页）表格用 `longtable`。
   - 原文表格如果只是文字描述没有表体，`latex` 可省略（只渲染表题）。
9. **英文原文**：忠实照录，修正明显断行/连字符。去掉页眉、页脚、页码、"Downloaded from..."
   之类噪声。
10. **中文译文**：准确、通顺、术语规范（参照《物理学名词》与学科习惯）。保留图号公式号
    引用，如 "(Fig. 2)" → "（图 2）"，"(3)" → "式 (3)"。
11. **摘要**：论文摘要就是正文的首个实质段落，正常翻译为 `para` 即可
    （渲染阶段会自动在其前加"摘要 / Abstract"标注）。
12. JSON 必须合法（UTF-8，无注释，无尾逗号）。

## 重要执行要求
- **先把文件写出来，再校验**（WRITE THE FILE FIRST, then validate）。不要只把内容输出到对话里。
- 用 Python 写 JSON（`json.dump(..., ensure_ascii=False)`）以避免转义问题。
- 完成后回报：文件路径、`blocks` 数量、英文总字符数。

## 输入文件说明
分片文件只包含该论文的一部分页面。只翻译你这一片包含的内容，不要臆造后续内容。
若整片都是参考文献/纯噪声，写出 `blocks: []` 的空 JSON 也是正确的。
