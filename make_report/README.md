# make_report

从实验课讲义等资料生成**科研论文格式的实验报告**，一次输出内容与排版一致的
`.docx`、`.pdf`、`.tex` 三份文件。

## 快速开始

```powershell
# 1. 编辑唯一内容源（可复制示例后修改）
copy ".opencode\skills\make_report\reference\example_report.json" report.json

# 2.（可选）生成合理示例数据与不确定度
python ".opencode\skills\make_report\scripts\generate_data.py" `
    --config ".opencode\skills\make_report\reference\example_data_config.json" `
    --out data.json

# 3. 生成三份文件
python ".opencode\skills\make_report\scripts\build_report.py" `
    --input report.json --outdir .\output --formats docx,pdf,tex `
    --title "实验题目"
```

输出：`output\实验题目.docx`、`output\实验题目.pdf`、`output\实验题目.tex`。

## 报告结构

摘要 → 关键词 → 引言 → 实验目的（按原材料）→ 实验原理（公式推导+物理图像）
→ 实验内容（仪器 / 实验设计含 A·B 类不确定度 / 具体内容）→ 实验数据处理（含不确定度）
→ 实验结论与思考题（含丰富解答）→ 参考文献。

## 依赖

- Python 包：`python-docx`（生成 docx）、`matplotlib`（可选，作图）
- LaTeX：`xelatex`（TeX Live / MiKTeX），用于生成 PDF
- 缺少 `xelatex` 时会跳过 PDF 并给出提示，`.docx`/`.tex` 仍正常生成

## 文件

| 路径 | 说明 |
| --- | --- |
| `SKILL.md` | 技能主说明与工作流 |
| `reference/report_schema.md` | `report.json` 完整字段说明 |
| `reference/example_report.json` | 完整可运行示例（RLC 电路） |
| `reference/example_data_config.json` | 数据生成配置示例 |
| `scripts/build_report.py` | 主生成器（tex → pdf → docx） |
| `scripts/generate_data.py` | 示例数据与不确定度生成 |
| `templates/report_template.tex` | LaTeX 排版模板参考 |

## 验证

在 Windows + TeX Live 2026 + python-docx 环境下已实测：
示例报告可成功生成 7 页 PDF、含 2 张表格的 docx 与可独立编译的 tex，
且 LaTeX 日志无错误。
