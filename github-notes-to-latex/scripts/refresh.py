#!/usr/bin/env python3
"""Build (and optionally refresh) the LaTeX PDF from a GitHub notes repo.

This is the one-command driver used by the ``github-notes-to-latex`` skill.

Typical use:
  # first build (downloads the repo, converts, compiles)
  python refresh.py --repo LUNARKN1GHT/USTC-AI-Notes --preset ustc-ai-notes

  # later: pull the latest notes and rebuild
  python refresh.py --refresh

  # other repositories: let the converter auto-discover chapters
  python refresh.py --repo owner/repo --auto

It writes into the current working directory by default (override with --workdir):
  source-notes/   downloaded Markdown vault
  chapters/       generated .tex
  images/         extracted images
  main.tex        document (created from the bundled template if missing)
  main.pdf        final output

The script is idempotent: re-running without --refresh re-converts and
re-compiles the existing source-notes/ tree.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
TEMPLATE = SKILL / "assets" / "main.tex"
# A chapters.json sidecar records how a project was built, so refresh knows the
# repo/preset without the user retyping them.
SIDECAR = "chapters.json"


def run(cmd: list[str], **kw) -> None:
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, **kw)


def find_xelatex() -> str | None:
    return shutil.which("xelatex")


def vault_root(source: Path) -> Path:
    """GitHub zip/clone leaves one nested dir; descend into it if so."""
    for _ in range(4):
        entries = [p for p in source.iterdir() if not p.name.startswith(".")]
        dirs = [p for p in entries if p.is_dir()]
        files = [p for p in entries if p.is_file()]
        if len(dirs) == 1 and not files:
            source = dirs[0]
        else:
            break
    return source


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo", help="owner/repo or github URL (omit when --refresh)")
    p.add_argument("--branch", default="main")
    p.add_argument("--workdir", default=".", help="where to build (default: cwd)")
    p.add_argument("--refresh", action="store_true",
                   help="re-download source-notes/ before rebuilding")
    p.add_argument("--preset", help="chapter preset passed to md2tex.py")
    p.add_argument("--config", help="explicit chapter JSON passed to md2tex.py")
    p.add_argument("--auto", action="store_true", help="auto-discover chapters")
    p.add_argument("--mirror", help="mirror prefix for download")
    p.add_argument("--no-compile", action="store_true", help="convert only")
    p.add_argument("--title", help="cover title (default: repo name)")
    p.add_argument("--subtitle", help="cover subtitle (default: 笔记)")
    p.add_argument("--blurb", help="cover blurb line")
    p.add_argument("--author", help="cover author (default: repo owner)")
    args = p.parse_args(argv)

    wd = Path(args.workdir).resolve()
    wd.mkdir(parents=True, exist_ok=True)
    source = wd / "source-notes"
    sidecar_path = wd / SIDECAR

    # Resolve repo/preset from the sidecar when refreshing.
    repo, preset, config, auto, branch = args.repo, args.preset, args.config, args.auto, args.branch
    sc = {}
    if sidecar_path.is_file():
        import json
        sc = json.loads(sidecar_path.read_text(encoding="utf-8"))
        repo = repo or sc.get("repo")
        preset = preset or sc.get("preset")
        config = config or sc.get("config")
        auto = auto or sc.get("auto", False)
        branch = branch if args.branch != "main" else sc.get("branch", branch)
        # restore cover metadata written by make_project.py
        args.title = args.title or sc.get("title")
        args.subtitle = args.subtitle or sc.get("subtitle")
        args.author = args.author or sc.get("author")
        args.blurb = args.blurb or sc.get("blurb")

    if (args.refresh or not source.is_dir()) and repo:
        print(f"== Downloading {repo} @ {branch} ==")
        cmd = [sys.executable, str(HERE / "fetch_repo.py"), repo, str(source),
               "--branch", branch]
        if args.mirror:
            cmd += ["--mirror", args.mirror]
        run(cmd)
    elif not source.is_dir():
        sys.stderr.write("No source-notes/ and no --repo given; nothing to do.\n")
        return 1

    # Persist how this project was built so a later `--refresh` is one command.
    if repo or preset or config or sc:
        import json
        sidecar = {
            "repo": repo, "branch": branch, "preset": preset,
            "config": config, "auto": bool(auto),
            "title": args.title, "subtitle": args.subtitle,
            "author": args.author, "blurb": args.blurb,
        }
        sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2),
                                encoding="utf-8")

    # Ensure main.tex exists (fill the template placeholders).
    main_tex = wd / "main.tex"
    if not main_tex.is_file() and TEMPLATE.is_file():
        title = args.title or (repo or "课程笔记")
        author = args.author or (repo.split("/")[0] if repo else "")
        url = f"https://github.com/{repo}" if repo else ""
        subtitle = args.subtitle or "笔记"
        text = TEMPLATE.read_text(encoding="utf-8")
        text = (text.replace("@@TITLE@@", title)
                    .replace("@@SUBTITLE@@", subtitle)
                    .replace("@@BLURB@@", args.blurb or "")
                    .replace("@@AUTHOR@@", author)
                    .replace("@@URL@@", url))
        main_tex.write_text(text, encoding="utf-8")
        print(f"Created {main_tex} from template.")

    print("== Converting Markdown -> LaTeX ==")
    root = vault_root(source)
    if root != source:
        print(f"   (vault root: {root})")
    cmd = [sys.executable, str(HERE / "md2tex.py"), str(root), str(wd)]
    if config:
        cmd += ["--config", config]
    elif preset:
        cmd += ["--preset", preset]
    elif auto:
        cmd += ["--auto"]
    run(cmd, cwd=wd)

    if args.no_compile:
        print("Skipping compile (--no-compile).")
        return 0

    xelatex = find_xelatex()
    if not xelatex:
        sys.stderr.write("\nxelatex not found. Install TeX Live or MiKTeX, then "
                         "re-run to produce main.pdf.\n")
        return 1

    print("== Compiling with XeLaTeX (3 passes) ==")
    for i in range(3):
        print(f"  pass {i + 1}/3")
        subprocess.run([xelatex, "-interaction=nonstopmode",
                        "-file-line-error", "main.tex"],
                       cwd=wd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    log = wd / "main.log"
    if log.is_file():
        text = log.read_text(encoding="utf-8", errors="replace")
        errors = [ln for ln in text.splitlines() if ln.startswith("!")]
        if errors:
            print(f"\nWARNING: {len(errors)} LaTeX error(s); see main.log")
            for e in errors[:10]:
                print("  " + e)
        else:
            print("\nCompile clean (0 errors).")

    pdf = wd / "main.pdf"
    if pdf.is_file():
        print(f"Output: {pdf} ({pdf.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
