# Markdown → LaTeX conversion notes

How `scripts/md2tex.py` maps source syntax, and the pitfalls that were fixed.
Use this when a new repo breaks the converter.

## Syntax support

| Markdown / Obsidian            | LaTeX output                              |
| ------------------------------ | ----------------------------------------- |
| YAML frontmatter `---…---`     | stripped                                  |
| `# H1` (in index/section file) | stripped (chapter title replaces it)      |
| `## H2`                        | `\section`                                |
| `### H3`                       | `\subsection`                             |
| `#### H4`                      | `\subsubsection`                          |
| `$…$`                          | kept as inline math                       |
| `$$…$$` (standalone)           | `equation*` (or the inner `align` etc.)   |
| `[[page|label]]`               | `label` (wikilink target dropped)         |
| `![[image.png]]`               | `\includegraphics` figure                 |
| `[text](url)`                  | `\href{url}{text}`                        |
| `**bold**` / `*italic*`        | `\textbf` / `\emph`                       |
| `==highlight==`                | `\hl{…}` (coloured bold — see below)      |
| `> [!note] …` callout          | `notebox` tcolorbox                       |
| `> plain quote`                | `quote` environment                       |
| fenced ``` ```code``` ```      | `lstlisting`                              |
| GFM table                      | `tabular` with wrapping `p{}` columns     |
| `-` / `1.` lists, nested       | `itemize` / `enumerate` (depth-normalised)|
| `[^1]` footnotes               | collected into a small list at file end   |

## Pitfalls that *were* real bugs (keep the fixes!)

1. **Escaped pipes in tables.** Obsidian writes `[[target\|label]]` inside a
   table cell. Splitting the row on `|` naively breaks the wikilink. The row
   splitter uses `re.split(r"(?<!\\)\|", line)` and un-escapes `\|`.

2. **`$$` block math must be handled in the main loop**, not as a paragraph.
   Otherwise the closing `$$` line is treated as the start of the next block and
   the delimiters get escaped (`\$\$`). See the "Standalone … `$$`" branch.

3. **Blank lines inside `$$…$$`** break `align`/`matrix`. `emit_math()` strips
   blank lines and, if the content already starts with a display environment
   (`align`, `cases` via `array`, …), emits it directly instead of nesting it in
   `equation*` (which caused *"Erroneous nesting of equation structures"*).

4. **Curl-quotes / line separators in math.** `U+2019 ’` → `'`,
   `U+2028`/`U+2029` → newline. Fixed in `fix_math()`.

5. **Special characters in `\texttt` / code.** Non-language code blocks were
   rendered as `quote` + `\ttfamily`, which breaks on `_ $ % #`. Always use
   `lstlisting` (verbatim) for code.

6. **`text` / `batch` / `yaml` listings languages** are undefined in stock
   `listings`. The template defines `batch` and `yaml`; `text` maps to no
   language (`language={}`).

7. **`==highlight==` and CJK/math.** `soul`'s `\hl` throws
   *"Reconstruction failed"* on CJK/math, and `\colorbox` cannot break lines
   (overfull). The template redefines `\hl` as coloured bold text.

8. **Unicode symbols in body text** that the Latin font lacks → missing glyphs:
   `⊃ ⊂ ∈ → ⇒` etc. `TEXT_MATH_SYMBOLS` substitutes them with math-mode
   equivalents via a placeholder (so the inserted `$…$` isn't re-escaped).

9. **Circled numbers `①②③` and emoji `✅❌`** → mapped to `(1)(2)(3)` / `[OK]`.
   `xeCJK` is configured with `CJKmath=true` so full-width punctuation inside
   `\text{}` renders.

10. **Nested-list indentation jumps.** Markdown often indents a sub-list by 4
    spaces (depth jump 0→2), producing empty `\item` + nested env errors.
    `_render_list` normalises depths to increase by at most 1.

11. **Markdown links.** Early versions left `[text](url)` as literal text
    because only wikilinks were handled. `MD_LINK`/`MD_IMAGE` regexes run before
    escaping.

12. **Wide tables overflow the margin.** 2-column `l l` tables don't wrap;
    `_colspec()` uses `p{}` columns sized to the text width.

## Extending

- New callout types (`[!warning]`, `[!tip]`): `_blockquote()` already maps them
  to a Chinese title; add to `title_map` if needed.
- New code languages: add to `LANG_MAP` and (if not built in) define the
  language in `assets/main.tex`.
- New frontmatter keys: `read_frontmatter()` reads `aliases:` for link labels;
  other keys (`tags`, `status`) are ignored.
