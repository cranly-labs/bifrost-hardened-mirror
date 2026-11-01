#!/usr/bin/env python3
"""Replace repository placeholders with the target GitHub owner and repository."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

TEXT_SUFFIXES = {".md", ".yml", ".yaml", ".json", ".env", ".example", ".toml", ".txt", ""}
SKIP_PARTS = {".git", "upstream", "dist", "node_modules", ".tmp", "vendor"}
REMOTE_PATTERN = re.compile(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$")


def detect_remote(root: Path) -> tuple[str, str] | None:
    try:
        output = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    match = REMOTE_PATTERN.search(output)
    if not match:
        return None
    return match.group("owner"), match.group("repo")


def candidates(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_PARTS for part in relative.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
            "CODEOWNERS",
            "Makefile",
            "Dockerfile",
        }:
            continue
        yield path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--owner")
    parser.add_argument("--repo")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.owner and args.repo:
        owner, repo = args.owner, args.repo
    else:
        detected = detect_remote(root)
        if not detected:
            print("error: pass --owner and --repo, or add a GitHub origin remote", file=sys.stderr)
            return 1
        owner, repo = detected

    display = f"{owner}/{repo}"
    image = f"{owner}/{repo}".lower()
    changes: list[Path] = []
    for path in candidates(root):
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated = original.replace(
            "OWNER/REPO/pkgs/container/REPO", f"{display}/pkgs/container/{repo}"
        )
        updated = updated.replace("OWNER%2FREPO", f"{owner}%2F{repo}")
        updated = updated.replace("ghcr.io/OWNER/REPO", f"ghcr.io/{image}")
        updated = updated.replace("OWNER/REPO", display)
        updated = updated.replace("@OWNER", f"@{owner}")
        if updated != original:
            changes.append(path)
            if not args.check:
                path.write_text(updated, encoding="utf-8")

    if args.check:
        if changes:
            print("Placeholders still need personalization:", file=sys.stderr)
            for path in changes:
                print(f"  {path.relative_to(root)}", file=sys.stderr)
            return 1
        print("Repository placeholders are personalized.")
        return 0

    if changes:
        for path in changes:
            print(f"updated {path.relative_to(root)}")
    else:
        print("No placeholders found; repository is already personalized.")
    print(f"Repository: {display}")
    print(f"Container image: ghcr.io/{image}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
