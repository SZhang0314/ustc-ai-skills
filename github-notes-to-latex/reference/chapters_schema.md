# `chapters.json` schema

The converter (`scripts/md2tex.py`) needs to know the **chapter order** and
which files belong to each chapter. Supply it one of these ways (priority
order):

1. `--config <file.json>` on the command line.
2. A `chapters.json` placed at the **source root** (next to the Markdown vault).
3. A built-in `--preset` (`ustc-ai-notes`).
4. **Auto-discovery** (`--auto`, or the default for unknown repos).

## Auto-discovery rules (`--auto`)

Use `--auto` when you just want a sensible default and don't care about exact
grouping:

- Each **top-level directory** becomes a chapter. Directories are ordered by a
  leading number (`00-`, `01-` …); non-numbered ones follow alphabetically.
- Within a chapter, `*.md` files are ordered by a leading `x.y` number
  (`2.3-逻辑回归.md`), then plain numbers, then the rest.
- A file whose stem equals the directory name (sans number), or is `index` /
  `README`, becomes the chapter **index**; the rest become **sections**.
- Sub-directories named `基本概念` / `算法` / `定理` / `模型` / `常识` become
  **card groups** rendered as a chapter appendix.
- A single loose top-level `*.md` (e.g. a knowledge map) becomes an
  unnumbered intro chapter titled `总览`.

## Explicit schema

```json
[
  {
    "number": null,                 // null -> \chapter* (unnumbered); int -> \chapter
    "title": "知识地图",             // chapter title shown in the TOC
    "index": "人工智能数学原理与算法A.md",  // optional chapter-intro file
    "sections": [                   // ordered list of section files
      "00-数学基础/0.1-线性代数与张量.md",
      "00-数学基础/0.2-微积分与自动微分.md"
    ],
    "cards": [                      // optional concept-card appendix
      ["基本概念", [                 // [group title, [card files]]
        "00-公共基础/基本概念/假设类.md",
        "00-公共基础/基本概念/损失函数.md"
      ]],
      ["算法", [
        "00-公共基础/算法/Sigmoid函数.md"
      ]]
    ]
  }
]
```

All paths are **relative to the source root** and use forward slashes.

### Field summary

| field      | type              | meaning                                                        |
| ---------- | ----------------- | -------------------------------------------------------------- |
| `number`   | int \| null       | `null` = unnumbered chapter; otherwise its ordinal              |
| `title`    | string            | chapter title (TOC + running head)                             |
| `index`    | string \| null    | optional intro file (its `#` H1 is stripped, `##` → section)   |
| `sections` | list[string]      | ordered body files (their `#` H1 stripped, `##` → section)     |
| `cards`    | list[[str, list]] | appendix groups: `[group_title, [files]]`, each file → card    |

## Notes on rendering

- `index` and `sections` files: the first `#` heading is removed (the chapter
  title replaces it); `##` → `\section`, `###` → `\subsection`, `####` →
  `\subsubsection`.
- `cards` files: the first `#` heading becomes a bold card title
  (`\cardtitle`); `##` → `\subsubsection`.
- A `--config` file may also be a dict with a top-level `"chapters"` key.
