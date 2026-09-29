#!/usr/bin/env python3
"""Fetch a GitHub repository (or a single page) into a local folder, resilient
to the flaky / TLS-reset GitHub connectivity seen from some networks.

It tries, in order:
  1. Direct ZIP archive download  (https://github.com/<owner>/<repo>/archive/refs/heads/<branch>.zip)
  2. GitHub API tarball/zipball   (https://api.github.com/repos/<owner>/<repo>/zipball/<branch>)
  3. git clone                    (if git is on PATH)
  4. A configured mirror prefix   (e.g. a ghproxy) via --mirror

All HTTP requests use an explicit TLS 1.2+ context, a browser User-Agent and a
retry loop, because on some networks the first few connections are reset.

Usage:
  python fetch_repo.py <owner/repo> [dest] [--branch main] [--timeout 90]
  python fetch_repo.py https://github.com/owner/repo [dest]
  python fetch_repo.py <owner/repo> [dest] --page <path>   # single raw file

Exit code 0 on success, 1 if every method failed.
"""

from __future__ import annotations

import argparse
import io
import os
import shutil
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def make_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    # Explicitly enable TLS >= 1.2: some networks reset otherwise.
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    except Exception:
        pass
    return ctx


def http_get(url: str, timeout: int, retries: int = 8, *, binary: bool = False):
    """GET a URL with retries and a TLS>=1.2 context."""
    last = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout, context=make_context()) as r:
                return r.read() if binary else r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            last = e
            sys.stderr.write(f"  attempt {attempt}/{retries} failed: {e}\n")
            time.sleep(min(2 * attempt, 6))
    raise RuntimeError(f"all attempts failed for {url}: {last}")


def parse_repo(spec: str) -> tuple[str, str]:
    spec = spec.rstrip("/")
    spec = spec.replace("https://github.com/", "").replace("http://github.com/", "")
    spec = spec.removesuffix(".git")
    parts = [p for p in spec.split("/") if p]
    if len(parts) < 2:
        raise SystemExit(f"Expected owner/repo, got: {spec}")
    return parts[0], parts[1]


def extract_zip(data: bytes, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        z.extractall(dest)
    # GitHub zips contain a single top-level dir; return it.
    children = [p for p in dest.iterdir() if p.is_dir()]
    return children[0] if len(children) == 1 else dest


def try_zip(owner: str, repo: str, branch: str, dest: Path, timeout: int) -> Path | None:
    url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
    print(f"[1] ZIP archive: {url}")
    try:
        data = http_get(url, timeout, binary=True)
        root = extract_zip(data, dest)
        print(f"    ok ({len(data)} bytes) -> {root}")
        return root
    except Exception as e:  # noqa: BLE001
        print(f"    failed: {e}")
        return None


def try_api(owner: str, repo: str, branch: str, dest: Path, timeout: int) -> Path | None:
    url = f"https://api.github.com/repos/{owner}/{repo}/zipball/{branch}"
    print(f"[2] GitHub API zipball: {url}")
    try:
        data = http_get(url, timeout, binary=True)
        root = extract_zip(data, dest)
        print(f"    ok ({len(data)} bytes) -> {root}")
        return root
    except Exception as e:  # noqa: BLE001
        print(f"    failed: {e}")
        return None


def try_git(owner: str, repo: str, branch: str, dest: Path) -> Path | None:
    print("[3] git clone")
    if shutil.which("git") is None:
        print("    git not found on PATH")
        return None
    try:
        subprocess.run(["git", "clone", "--depth", "1", "--branch", branch,
                        f"https://github.com/{owner}/{repo}.git", str(dest)],
                       check=True)
        print(f"    ok -> {dest}")
        return dest
    except Exception as e:  # noqa: BLE001
        print(f"    failed: {e}")
        return None


def try_mirror(owner: str, repo: str, branch: str, dest: Path, mirror: str,
               timeout: int) -> Path | None:
    base = mirror.rstrip("/") + "/"
    url = f"{base}https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
    print(f"[4] mirror: {url}")
    try:
        data = http_get(url, timeout, binary=True)
        root = extract_zip(data, dest)
        print(f"    ok ({len(data)} bytes) -> {root}")
        return root
    except Exception as e:  # noqa: BLE001
        print(f"    failed: {e}")
        return None


def fetch_page(owner: str, repo: str, branch: str, path: str, dest_file: Path,
               timeout: int) -> None:
    raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    print(f"Fetching raw file: {raw}")
    text = http_get(raw, timeout)
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    dest_file.write_text(text, encoding="utf-8")
    print(f"    ok -> {dest_file}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", help="owner/repo or a github.com URL")
    p.add_argument("dest", nargs="?", default="source-notes",
                   help="destination directory for the extracted repo")
    p.add_argument("--branch", default="main", help="branch/tag (default: main)")
    p.add_argument("--timeout", type=int, default=90, help="per-request timeout (s)")
    p.add_argument("--mirror", help="mirror/proxy prefix for GitHub URLs")
    p.add_argument("--page", help="fetch a single raw file path instead of the repo")
    args = p.parse_args(argv)

    owner, repo = parse_repo(args.repo)
    dest = Path(args.dest)

    if args.page:
        fetch_page(owner, repo, args.branch, args.page,
                   dest / Path(args.page).name, args.timeout)
        return 0

    if dest.exists():
        print(f"Removing existing destination: {dest}")
        shutil.rmtree(dest)

    root = try_zip(owner, repo, args.branch, dest, args.timeout)
    if root is None:
        api_dest = dest.with_name(dest.name + "_api")
        root = try_api(owner, repo, args.branch, api_dest, args.timeout)
    if root is None:
        git_dest = dest.with_name(dest.name + "_git")
        root = try_git(owner, repo, args.branch, git_dest)
    if root is None and args.mirror:
        mirror_dest = dest.with_name(dest.name + "_mirror")
        root = try_mirror(owner, repo, args.branch, mirror_dest, args.mirror, args.timeout)

    if root is None:
        sys.stderr.write("\nAll download methods failed. Suggestions:\n"
                         "  * retry (the first few connections are often reset)\n"
                         "  * try a mirror:  --mirror https://ghproxy.com/\n"
                         "  * or a jsDelivr/Gitee mirror of the repo\n")
        return 1

    print(f"\nDone. Source tree: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
