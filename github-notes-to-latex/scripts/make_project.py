#!/usr/bin/env python3
"""One-shot project initializer: GitHub URL -> new folder -> PDF -> refresh .bat.

This is the *front door* of the ``github-notes-to-latex`` skill. Given a GitHub
URL (repo, a sub-page, or a raw file) it:

  1. derives a clean project folder name and creates it (in --parent, default cwd);
  2. downloads the notes into ``<project>/source-notes/``;
  3. picks a chapter preset (or auto-discovers) and records ``chapters.json``;
  4. compiles ``<project>/main.pdf`` with XeLaTeX;
  5. writes ``<project>/refresh.bat`` — double-click to re-download the content
     AND rebuild the PDF.

Usage
-----
  # whole repo, into ./<repo>-notes/
  python make_project.py https://github.com/owner/repo

  # choose folder + title
  python make_project.py https://github.com/owner/repo \
      --name my-course --title "机器学习讲义" --author "原作者"

  # a single page (raw markdown) instead of the whole repo
  python make_project.py https://github.com/owner/repo/blob/main/notes/ch1.md

  # other repos: force chapter auto-discovery
  python make_project.py https://github.com/owner/repo --auto
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def log(msg: str) -> None:
    print(msg, flush=True)


def run(cmd: list[str], **kw) -> int:
    log("+ " + " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, **kw).returncode


def parse_github_url(url: str) -> dict:
    """Return {owner, repo, branch, page} from any common GitHub URL form."""
    u = url.strip().rstrip("/")
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    if not u.startswith("github.com"):
        raise SystemExit(f"Not a github.com URL: {url}")
    u = u[len("github.com/"):]
    parts = u.split("/")
    if len(parts) < 2:
        raise SystemExit(f"Need at least owner/repo in URL: {url}")
    owner, repo = parts[0], parts[1]
    repo = repo.removesuffix(".git")
    branch, page = None, None
    # /blob/<branch>/<path>  (view) or /tree/<branch>/...  (listing)
    if len(parts) >= 4 and parts[2] in ("blob", "tree"):
        branch = parts[3]
        if parts[2] == "blob" and len(parts) >= 5:
            page = "/".join(parts[4:])
    # /raw/<branch>/<path>
    elif len(parts) >= 4 and parts[2] == "raw":
        branch = parts[3]
        page = "/".join(parts[4:])
    return {"owner": owner, "repo": repo, "branch": branch or "main", "page": page}


def slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "notes"


def vendor_scripts(project: Path) -> Path:
    """Copy the skill's runtime scripts + template into <project>/_scripts so the
    project (and its refresh.bat) is self-contained and portable."""
    dst = project / "_scripts"
    dst.mkdir(parents=True, exist_ok=True)
    # refresh.py looks for the template at <SKILL>/assets/main.tex where SKILL is
    # its parent dir; vendored, that is <project>/assets/main.tex.
    assets = project / "assets"
    assets.mkdir(exist_ok=True)
    for name in ("refresh.py", "fetch_repo.py", "md2tex.py"):
        shutil.copy2(HERE / name, dst / name)
    shutil.copy2(HERE.parent / "assets" / "main.tex", assets / "main.tex")
    return dst


def write_bat(project: Path, repo_spec: str, title: str) -> Path:
    """Write an ASCII-only refresh.bat that re-downloads and rebuilds.

    It calls the *vendored* _scripts/refresh.py next to it, so the whole project
    folder can be moved or zipped without breaking the refresher.
    """
    bat = project / "refresh.bat"
    # Keep the batch file ASCII-only; all CJK lives in chapters.json / main.tex.
    content = f"""@echo off
rem ============================================================
rem  Double-click to refresh this lecture PDF:
rem    1) re-download the notes from GitHub
rem    2) rebuild main.pdf
rem  Default: refresh text (fast).  "force" re-downloads everything.
rem  Project: {repo_spec}
rem ============================================================
setlocal
cd /d "%~dp0"
set "PY=python"
set "REFRESH=%~dp0_scripts\\refresh.py"

echo.
echo === Refresh: {repo_spec} ===
echo.

"%PY%" "%REFRESH%" --refresh --workdir "%~dp0" %*
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo === Done. PDF: main.pdf ===
) else (
    echo === FAILED ^(exit %RC%^). See output above or main.log ===
)
echo.
pause
endlocal
"""
    # ASCII-only guard: refuse to write if any non-ASCII slipped in.
    try:
        content.encode("ascii")
    except UnicodeEncodeError as e:
        raise SystemExit(f"refresh.bat would contain non-ASCII: {e}")
    bat.write_text(content, encoding="ascii", newline="\r\n")
    return bat


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("url", help="GitHub URL (repo, /blob/... page, or /raw/... file)")
    p.add_argument("--parent", default=".", help="parent dir for the new project")
    p.add_argument("--name", help="project folder name (default: <repo>-notes)")
    p.add_argument("--title", help="cover title")
    p.add_argument("--subtitle", default="课程笔记")
    p.add_argument("--author", help="cover author (default: repo owner)")
    p.add_argument("--blurb", default="", help="one-line cover blurb")
    p.add_argument("--preset", help="chapter preset (default: auto-detect / ustc-ai-notes)")
    p.add_argument("--auto", action="store_true", help="force chapter auto-discovery")
    p.add_argument("--mirror", help="mirror prefix for the download")
    p.add_argument("--no-compile", action="store_true", help="download+convert only")
    p.add_argument("--force", action="store_true", help="overwrite an existing project dir")
    args = p.parse_args(argv)

    info = parse_github_url(args.url)
    repo_spec = f"{info['owner']}/{info['repo']}"
    name = args.name or f"{slugify(info['repo'])}-notes"
    project = Path(args.parent).resolve() / name

    if project.exists() and any(project.iterdir()) and not args.force:
        log(f"Project dir already exists and is non-empty: {project}")
        log("Use --force to rebuild in place, or --name to pick another folder.")
        return 1
    project.mkdir(parents=True, exist_ok=True)
    log(f"Project folder: {project}")

    # 1) download ---------------------------------------------------------
    source = project / "source-notes"
    log(f"== Downloading {repo_spec} @ {info['branch']} ==")
    dl = [sys.executable, str(HERE / "fetch_repo.py"), repo_spec, str(source),
          "--branch", info["branch"]]
    if info["page"] and not info["page"].endswith("/"):
        dl += ["--page", info["page"]]
    if args.mirror:
        dl += ["--mirror", args.mirror]
    if run(dl) != 0:
        log("Download failed. Retry, or pass --mirror https://ghproxy.com/")
        return 1

    # 2) record how to rebuild -------------------------------------------
    sidecar = {
        "repo": repo_spec, "branch": info["branch"],
        "preset": args.preset, "auto": bool(args.auto),
        "title": args.title, "subtitle": args.subtitle,
        "author": args.author, "blurb": args.blurb, "page": info["page"],
    }
    (project / "chapters.json").write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3) generate the double-click refresher (self-contained) --------------
    vendor_scripts(project)
    bat = write_bat(project, repo_spec, args.title or info["repo"])
    log(f"Wrote {bat}  (double-click to refresh + rebuild)")

    # 4) first build ------------------------------------------------------
    log("== First build ==")
    build = [sys.executable, str(project / "_scripts" / "refresh.py"),
             "--repo", repo_spec, "--branch", info["branch"],
             "--workdir", str(project)]
    if args.title:
        build += ["--title", args.title]
    if args.subtitle:
        build += ["--subtitle", args.subtitle]
    if args.author:
        build += ["--author", args.author]
    if args.blurb:
        build += ["--blurb", args.blurb]
    if args.preset:
        build += ["--preset", args.preset]
    if args.auto:
        build += ["--auto"]
    if args.mirror:
        build += ["--mirror", args.mirror]
    if args.no_compile:
        build += ["--no-compile"]
    rc = run(build)

    log("")
    log("=" * 60)
    if rc == 0:
        pdf = project / "main.pdf"
        log(f"Done. PDF: {pdf if pdf.is_file() else '(skipped compile)'}")
        log(f"Refresh anytime: double-click {project / 'refresh.bat'}")
    else:
        log(f"Build exited with {rc}; see {project / 'main.log'}")
    log("=" * 60)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
