---
name: github-notes-to-latex
description: Use when the user gives a GitHub URL (repo, README, or page) and wants its notes downloaded into a new project folder, aggregated and compiled into a LaTeX PDF lecture handout, and/or given a double-click .bat that refreshes both the downloaded content and the PDF ("给个 GitHub 网址，把笔记下载整理成 latex 讲义", "要一个双击就能刷新重建的 bat", "随时刷新重新拉取再重编"). Trigger directly when the user inputs a GitHub URL together with "请生成讲义" (e.g. "https://github.com/owner/repo 请生成讲义"). Handles flaky GitHub access, README/Markdown conversion, chapter ordering, XeLaTeX + ctexbook, Windows GBK filename pitfalls.
---

# github-notes-to-latex — GitHub 网址 → 讲义 PDF + 双击刷新 bat

用户给一个 **GitHub 网址**，本 skill 完成四件事：

1. **新建一个项目文件夹**（默认 `<repo>-notes/`），把网页/仓库中的笔记内容
   下载到该文件夹；
2. **汇总编排**这些 Markdown 笔记，按章节顺序转换并用 **XeLaTeX + ctexbook**
   编译成一本讲义 PDF（`main.pdf`）；
3. 在项目文件夹里生成 **`refresh.bat`**：双击即「重新下载 + 重新编译」，
   内容和讲义同时刷新；
4. 全流程可重复：任何时刻双击 bat 或重跑一条命令即可得到最新版。

## 何时使用
- **直接触发**：用户输入一个 GitHub 网址并说「请生成讲义」
  （如 `https://github.com/owner/repo 请生成讲义`）。
- 用户给出 GitHub 仓库 URL / 某页面链接，要求「整理成 PDF 讲义」「编译成
  latex pdf」「做个能随时刷新的 bat」。
- 笔记更新后要一键重建同一本 PDF。

不适用：整本英文书籍翻译（用 `english-book-translation`）、实验报告三件套
（用 `make_report`）。

## 标准流程（一条命令）

```bash
python <skill>/scripts/make_project.py https://github.com/<owner>/<repo> \
    --parent <父目录> --name <项目名> \
    --title "讲义标题" --subtitle "课程笔记" --author "原作者"
```

`make_project.py` 自动完成：

| 步骤 | 动作 | 产物 |
|---|---|---|
| 1 | 解析 URL（repo / blob 页 / raw 文件都支持），新建 `--parent/<name>/` | 项目文件夹 |
| 2 | 下载仓库（抗抖动：ZIP→API→git→mirror） | `source-notes/` |
| 3 | 记录构建参数（repo/branch/标题等） | `chapters.json` |
| 4 | 把运行脚本拷进项目（自包含、可整体搬走） | `_scripts/`、`assets/` |
| 5 | 生成双击刷新脚本（ASCII-only） | `refresh.bat` |
| 6 | 转换 + XeLaTeX 3 遍 | `chapters/`、`images/`、`main.tex`、`main.pdf` |

默认文件夹名 `<repo小写>-notes`；单页 URL（`/blob/...`）只取该文件。
常用开关：`--auto` 强制章节自动发现、`--preset ustc-ai-notes` 用内置模板、
`--mirror https://ghproxy.com/` 走代理、`--no-compile` 只转换、
`--force` 覆盖已有目录。

## 双击刷新（交付给用户的形态）

项目文件夹里的 `refresh.bat` 即用户要的「双击即可运行」程序：

- 默认模式：重跑 `refresh.py --refresh`——**重新下载笔记 + 重新编译 PDF**，
  跑完 pause 显示结果；
- 追加参数 `force`：所有文件（含图片/课件）强制重下；
- bat 是 **纯 ASCII**（见下方 Windows 坑），调的是项目内的
  `_scripts\refresh.py`，整个文件夹可以拷贝/打包带走。

手动等价命令：

```bash
python <项目>/_scripts/refresh.py --refresh --workdir <项目>
```

`chapters.json` sidecar 记录了 repo/branch/标题，刷新无需重敲参数。

## 章节顺序如何决定
优先级：`--config file.json` > 源根目录的 `chapters.json` > `--preset`
（`ustc-ai-notes`）> `--auto` 自动发现。详见 `reference/chapters_schema.md`。
自动发现规则：顶层目录=章（按数字前缀排序），`x.y-*.md`=节，与目录同名的
md=章索引，`基本概念/算法/定理/模型` 子目录=卡片组。

对「每章一个 README」式教程仓库（如 dive-into-llms）：用 `--auto`，或写一个
简单 `chapters.json` 列出各章 README 路径即可。

## 关键坑（Windows / GBK 环境，务必遵守）

1. **.bat 与 .ps1 禁止非 ASCII 字面量**。PowerShell 5.1 / cmd 按 GBK 解码
   无 BOM 脚本，UTF-8 中文会烧成乱码——中文输出文件名会变成乱码文件名。
   解决：bat 保持 ASCII；中文产物名（封面标题、PDF 文件名）一律在
   Python（UTF-8）里生成。
2. **PowerShell 管道传参**：空字符串参数会报错，用数组 splatting 拼参数。
3. **`raw.githubusercontent.com` 下载大 PDF 不稳**：用 `curl.exe --retry`
   带重试；一次超时就换 curl，不要死磕 urllib。
4. **GitHub zip 会多包一层目录**：`refresh.py` 的 `vault_root()` 会自动下钻
   一层，转换前不要手写死路径。
5. **中文文件名落盘后**用 Python `os.listdir` + `repr()` 验证，不要用 GBK
   控制台肉眼判断。

## Markdown 转换要点（详见 reference/markdown-to-latex.md）
- 表格内转义竖线、跨行 `$$`、公式弯引号、代码块特殊字符、嵌套列表缩进、
  宽表格溢出、`\|`、`[[wikilink]]`、裸 URL 吞全角括号、URL 里的括号、
  Unicode 数学符号缺失——`md2tex.py` 已全部处理，改动时不要退化。
- 中文字体 `SimSun/SimHei/KaiTi`，缺失回退 Noto CJK；模板用
  `\IfFontExistsTF` 回退。数学保持 `$…$`/`$$…$$` 原样。

## 文件说明
- `scripts/make_project.py` — **入口**：URL → 新文件夹 → 下载 → 构建 → 生成
  `refresh.bat`（含脚本 vendoring）。
- `scripts/fetch_repo.py` — 抗抖动下载（TLS/重试/ZIP/API/git/mirror）。
- `scripts/md2tex.py` — Markdown→LaTeX 转换 + 章节编排。
- `scripts/refresh.py` — 构建驱动：下载（可选）→ 转换 → 编译；读 sidecar。
- `assets/main.tex` — ctexbook 模板（`@@TITLE@@` 等占位符）。
- `reference/chapters_schema.md`、`reference/markdown-to-latex.md`、
  `reference/network-troubleshooting.md` — 详细参考。

## 自检与交付
- 编译输出应为 `Compile clean (0 errors).`；否则查 `main.log` 中 `!` 行。
- 抽查：页数（`pdfinfo`）、`pdftotext` 确认章节齐全、无 U+FFFD。
- 向用户报告：项目文件夹绝对路径、`main.pdf` 页数、`refresh.bat` 位置。
