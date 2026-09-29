# 翻译任务规范（中英对照注释版）

## 目标
把章节英文原文翻译成**中英逐段对照**的 JSON 文件，供 LaTeX 渲染成 PDF。

## 输出格式
生成一个 JSON 文件，结构如下：

```json
{
 "chapter": 2,
 "title_en": "Wave Diffraction and the Reciprocal Lattice",
 "title_zh": "波衍射与倒易点阵",
 "blocks": [
   {"type":"heading","level":1,"en":"DIFFRACTION OF WAVES BY CRYSTALS","zh":"晶体对波的衍射"},
   {"type":"heading","level":2,"en":"Bragg Law","zh":"布拉格定律"},
   {"type":"para","en":"<英文段落原文>","zh":"<中文译文>",
    "terms":[{"en":"reciprocal lattice","zh":"倒易点阵","note":"<术语解释，1-2句>"}]},
   {"type":"equation","latex":"n\\lambda=2d\\sin\\theta","num":"(2)",
    "zh_note":"布拉格定律：衍射极大的条件"},
   {"type":"figcap","en":"Figure 1 ...","zh":"图 1 ..."},
   {"type":"table","en":"TABLE 1 ...","zh":"表 1 ...",
    "latex":"\\begin{tabular}{lcc}\\toprule ... \\bottomrule\\end{tabular}"}
 ]
}
```

## 规则
1. **逐段对照**：每个 `para` 必须是一段完整英文原文 + 对应的中文全译。不要把多段合并。
2. **全文翻译**：正文、图题、表题、小结、习题都要翻译，不遗漏。
3. **标题**：章节内一级小标题（原文全大写）用 `level:1`；二级小标题（如 "Bragg Law"）用 `level:2`。
4. **图/表题**：`figcap` / `table` 类型。英文原文照录，中文给出完整翻译。
   **务必保留图号/表号**（供插图绑定与核对）。
5. **专业术语**：每章第一次出现的重要专业术语放入该段的 `terms` 数组，`note` 用 1-2 句中文解释。
   - `zh` 字段必须包含该术语的中文译名（渲染时会自动加脚注）。
   - 每章术语 15-40 个为宜，优先核心概念。
6. **公式（全部用 LaTeX，禁止 Unicode 近似）**：
   - 行内公式写在 `en`/`zh` 文本里，用 `$...$` 包裹：如 `$E=\hbar\omega$`、`$a_1$`、
     `$\sqrt{3}/2$`、`$\lambda=2d\sin\theta$`。中文段里的行内公式同样用 `$...$`。
   - **禁止用 Unicode 上下标/希腊字母散落正文**（a₁、½、θ、ω 这类写法一律改为 `$...$`）。
   - 原书**单独成行的编号公式**单独用 `equation` block：
     `latex` 字段只写**数学模式本体**（不要写 `\begin{equation}` 包裹，渲染器会自动加），
     原书公式编号放 `num`（如 `"(2)"`，渲染为 `\tag`）；可选 `zh_note` 用一句中文说明。
     公式是语言中性的，`equation` block 只渲染一次，中英共用。
   - **JSON 转义**：反斜杠写成 `\\`（解析后为单个 `\`），如 `"\\frac{1}{2}"`；
     不要过度转义（`"\\\\hbar"` 解析后是 `\\hbar`，会被当成换行）。
   - 正文中如确需美元符号（价格等），写成 `\$`（JSON 里 `"\\$"`）；
     **不要出现孤立的裸 `$`**（会打乱公式配对）。
   - 多步推导拆成多个 `equation` block；**避免单行公式过宽**——用
     `\begin{aligned}...\end{aligned}` 内部换行，公式行宽控制在约 60 字符以内。
7. **表格（用 LaTeX 排版，不要只给表题）**：`table` block 除中英表题外，给出 `latex` 字段：
   完整的 `\begin{tabular}{...}...\end{tabular}`（booktabs 风格：`\toprule`/`\midrule`/`\bottomrule`）。
   - 单元格内的数学用 `$...$`；单元格文本不要用 `<`、`>`、`&`、`%`、`#`、`_` 等需转义字符
     （`&` 只能作列分隔符）。
   - 渲染器会自动把过宽表格缩放到版心内（`adjustbox`），超长（跨页）表格用 `longtable`。
   - 原书表格如果只是文字描述没有表体，`latex` 可省略（只渲染表题）。
8. **英文原文**：忠实照录，修正明显的断行/连字符（如 "peri-\nodic" → "periodic"）。
9. **中文译文**：准确、通顺、术语规范（参照《物理学名词》与固体物理教材习惯）。保留原文中的
   图号、公式号引用，如 "(Fig. 2)" → "（图 2）"，"(2)" → "式 (2)"。
10. JSON 必须合法（UTF-8，无注释，无尾逗号）。

## 输入
章节英文原文在 raw/chNN.txt（`===PAGE n===` 为页分隔符，含页眉页脚噪声，翻译时忽略页码/页眉）。

## 输出
写到 src/chNN.json。

## 执行要求
- **先把文件写出来，再校验**（WRITE THE FILE FIRST, then validate），用
  `json.dump(..., ensure_ascii=False)` 写 UTF-8 JSON。
- 完成后回报：文件路径、`blocks` 数量、英文总字符数。
