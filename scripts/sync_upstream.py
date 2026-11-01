#!/usr/bin/env python3
"""Vendor a pinned Bifrost upstream release into ``upstream/``.

The script is dependency-free so it can run on a laptop and on a stock GitHub
Actions runner. It performs a blobless sparse clone of the upstream tag, exports
the mirrored source tree, and atomically replaces the vendored snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

UPSTREAM_REPOSITORY = "https://github.com/maximhq/bifrost"
UPSTREAM_GIT_URL = "https://github.com/maximhq/bifrost.git"
TAG_PREFIX = "transports/v"
LOCK_FILE = "vendor.lock.json"
VERSIONS_FILE = "versions.env"
VENDOR_DIR = "upstream"

# Upstream CI, hosted documentation media, and maintainer-only metadata are not
# part of the distribution contract. Everything else is mirrored.
EXCLUDED_TOP_LEVEL = {
    ".github",
    ".git",
    ".claude",
    ".greptile",
    ".coderabbit.yaml",
    ".cursorignore",
    ".envrc",
    ".infisical.json",
    ".snyk",
    "AGENTS.md",
    "pulse.yaml",
}
EXCLUDED_PREFIXES = (
    "docs/media/",
)


class SyncError(RuntimeError):
    """Raised when the upstream snapshot cannot be produced safely."""


@dataclass(frozen=True)
class UpstreamRelease:
    tag: str
    version: str
    commit: str
    source_url: str
    release_url: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout


def ls_remote_tags() -> dict[str, str]:
    """Return tag refs (and peeled refs) from the upstream repository."""
    output = run_git("ls-remote", "--tags", UPSTREAM_GIT_URL, f"{TAG_PREFIX}*")
    refs: dict[str, str] = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        sha, ref = line.split("\t", 1)
        refs[ref.strip()] = sha.strip()
    return refs


def version_key(tag: str) -> tuple:
    """Sort SemVer-like tags without adding a packaging dependency."""
    raw = tag.removeprefix(TAG_PREFIX).removeprefix("v")
    core, _, prerelease = raw.partition("-")
    numbers: list[int] = []
    for part in core.split("."):
        match = re.match(r"^(\d+)", part)
        if not match:
            raise SyncError(f"Cannot parse upstream version from tag {tag!r}")
        numbers.append(int(match.group(1)))
    while len(numbers) < 3:
        numbers.append(0)
    # A stable release sorts after any prerelease of the same core version.
    return (*numbers, 0 if prerelease else 1, prerelease)


def latest_tag(include_prerelease: bool = False) -> str:
    refs = ls_remote_tags()
    tags = {
        ref.removeprefix("refs/tags/")
        for ref in refs
        if ref.startswith(f"refs/tags/{TAG_PREFIX}") and not ref.endswith("^{}")
    }
    if not include_prerelease:
        tags = {tag for tag in tags if "-" not in tag.removeprefix(TAG_PREFIX)}
    if not tags:
        raise SyncError("No matching upstream tags were found")
    return max(tags, key=version_key)


def resolve_release(tag: str) -> UpstreamRelease:
    refs = ls_remote_tags()
    ref = f"refs/tags/{tag}"
    if ref not in refs:
        raise SyncError(f"Upstream tag not found: {tag}")
    commit = refs.get(f"{ref}^{{}}", refs[ref])
    version = tag.removeprefix(TAG_PREFIX)
    return UpstreamRelease(
        tag=tag,
        version=version,
        commit=commit,
        source_url=(
            "https://github.com/maximhq/bifrost/tree/"
            + urllib.parse.quote(tag, safe="/")
        ),
        release_url=(
            "https://github.com/maximhq/bifrost/releases/tag/"
            + urllib.parse.quote(tag, safe="")
        ),
    )


def _sparse_patterns() -> list[str]:
    patterns = ["/*"]
    patterns.extend(f"!{name}" for name in sorted(EXCLUDED_TOP_LEVEL))
    patterns.extend(f"!/{prefix}" for prefix in EXCLUDED_PREFIXES)
    return patterns


def fetch_source(release: UpstreamRelease, destination: Path, clone_dir: Path) -> str:
    """Sparse-clone the upstream tag and export the mirrored source tree.

    A blobless sparse clone avoids downloading hosted documentation media that
    the distribution deliberately does not vendor. Returns the upstream Git
    tree SHA for the lockfile.
    """
    clone = subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--filter=blob:none",
            "--no-checkout",
            "--depth",
            "1",
            "--branch",
            release.tag,
            UPSTREAM_GIT_URL,
            str(clone_dir),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if clone.returncode != 0:
        raise SyncError(f"Unable to clone {release.tag}: {clone.stderr.strip()}")

    subprocess.run(
        ["git", "-C", str(clone_dir), "sparse-checkout", "init", "--no-cone"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    (clone_dir / ".git" / "info" / "sparse-checkout").write_text(
        "\n".join(_sparse_patterns()) + "\n", encoding="utf-8"
    )
    checkout = subprocess.run(
        ["git", "-C", str(clone_dir), "checkout", "--force"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if checkout.returncode != 0:
        raise SyncError(f"Unable to checkout {release.tag}: {checkout.stderr.strip()}")

    head = run_git("-C", str(clone_dir), "rev-parse", "HEAD").strip()
    if head != release.commit:
        raise SyncError(
            f"Resolved commit mismatch for {release.tag}: expected {release.commit}, got {head}"
        )
    tree = run_git("-C", str(clone_dir), "rev-parse", "HEAD^{tree}").strip()

    shutil.copytree(
        clone_dir,
        destination,
        symlinks=True,
        ignore=shutil.ignore_patterns(".git"),
    )
    return tree


def make_writable(root: Path) -> None:
    """Restore owner write permission on vendored files."""
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            try:
                path.chmod(path.stat().st_mode | stat.S_IWUSR)
            except OSError:
                pass


def make_readonly(root: Path) -> None:
    """Mark vendored files read-only to discourage IDE and local edits.

    Directories stay writable so Git and the sync script can replace the tree.
    Docker builds run as root and can still apply reviewed patches.
    """
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            try:
                path.chmod(path.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
            except OSError:
                pass


def prune(root: Path) -> list[str]:
    removed: list[str] = []
    for name in sorted(EXCLUDED_TOP_LEVEL):
        path = root / name
        if path.exists() or path.is_symlink():
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
            removed.append(name)

    for prefix in EXCLUDED_PREFIXES:
        path = root / prefix
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            removed.append(prefix.rstrip("/"))

    for ds_store in root.rglob(".DS_Store"):
        ds_store.unlink()
    return removed


def _hash_file(path: Path, digest: "hashlib._Hash") -> None:
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)


def tree_digest(root: Path) -> tuple[str, int]:
    """Hash path names, modes, and contents into one deterministic digest."""
    entries: list[tuple[str, int, Path]] = []
    for path in root.rglob("*"):
        if path.is_symlink() or path.is_file():
            relative = path.relative_to(root).as_posix()
            entries.append((relative, path.lstat().st_mode & 0o111, path))
    entries.sort(key=lambda item: item[0])

    digest = hashlib.sha256()
    for relative, mode, path in entries:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(f"{mode:o}".encode("ascii"))
        digest.update(b"\0")
        if path.is_symlink():
            digest.update(b"L")
            digest.update(os.readlink(path).encode("utf-8"))
        else:
            digest.update(b"F")
            _hash_file(path, digest)
        digest.update(b"\0")
    return digest.hexdigest(), len(entries)


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_versions(lock: dict) -> str:
    upstream = lock["upstream"]
    distribution = lock["distribution"]
    return (
        "# Generated by scripts/sync_upstream.py. Do not edit by hand.\n"
        f"BIFROST_VERSION={upstream['version']}\n"
        f"BIFROST_TAG={upstream['tag']}\n"
        f"BIFROST_COMMIT={upstream['commit']}\n"
        f"BIFROST_RELEASE_URL={upstream['release_url']}\n"
        f"DISTRO_REVISION={distribution['revision']}\n"
    )


def github_output(values: dict[str, str]) -> None:
    destination = os.environ.get("GITHUB_OUTPUT")
    if not destination:
        return
    with open(destination, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def build_lock(release: UpstreamRelease, git_tree: str, tree_sha: str, file_count: int,
               removed: Iterable[str], revision: int) -> dict:
    return {
        "$schema": "./vendor.lock.schema.json",
        "upstream": {
            "repository": UPSTREAM_REPOSITORY,
            "tag": release.tag,
            "version": release.version,
            "commit": release.commit,
            "git_tree": git_tree,
            "source_url": release.source_url,
            "release_url": release.release_url,
        },
        "vendor": {
            "directory": VENDOR_DIR,
            "tree_sha256": tree_sha,
            "file_count": file_count,
            "excluded": sorted(
                set(removed)
                | EXCLUDED_TOP_LEVEL
                | {prefix.rstrip("/") for prefix in EXCLUDED_PREFIXES}
            ),
        },
        "distribution": {
            "revision": revision,
            "generator": "scripts/sync_upstream.py",
        },
        "synced_at": utc_now(),
    }


def sync(args: argparse.Namespace) -> dict:
    root = Path(args.root).resolve()
    vendor = root / VENDOR_DIR
    lock_path = root / LOCK_FILE
    versions_path = root / VERSIONS_FILE

    existing_lock = load_json(lock_path)
    if vendor.exists() and existing_lock:
        expected = existing_lock.get("vendor", {}).get("tree_sha256")
        if expected:
            actual, _ = tree_digest(vendor)
            if actual != expected and not args.force:
                raise SyncError(
                    "The vendored tree has local modifications. Re-run with --force "
                    "only after moving those changes into patches/."
                )

    tag = args.ref or latest_tag(include_prerelease=args.include_prerelease)
    release = resolve_release(tag)
    if existing_lock.get("upstream", {}).get("tag") == tag:
        revision = int(existing_lock.get("distribution", {}).get("revision", 1))
        if args.bump_revision:
            revision += 1
        if not args.force and not args.bump_revision:
            print(f"Already pinned to {tag}; nothing to do.")
            github_output(
                {
                    "tag": tag,
                    "version": release.version,
                    "commit": release.commit,
                    "changed": "false",
                }
            )
            return existing_lock
    else:
        revision = 1

    with tempfile.TemporaryDirectory(prefix="bifrost-sync-") as temporary:
        temporary_path = Path(temporary)
        extracted = temporary_path / "extracted"
        clone_dir = temporary_path / "clone"
        print(f"Cloning {release.tag} ({release.commit[:12]}) with sparse checkout")
        git_tree = fetch_source(release, extracted, clone_dir)
        removed = prune(extracted)
        tree_sha, file_count = tree_digest(extracted)

        lock = build_lock(release, git_tree, tree_sha, file_count, removed, revision)
        print(
            f"Prepared {release.tag} ({release.commit[:12]}): "
            f"{file_count} files, tree sha256 {tree_sha[:16]}…"
        )

        if args.dry_run:
            print(json.dumps(lock, indent=2, sort_keys=True))
            github_output(
                {
                    "tag": release.tag,
                    "version": release.version,
                    "commit": release.commit,
                    "tree_sha256": tree_sha,
                    "changed": "true",
                }
            )
            return lock

        backup = temporary_path / "previous-upstream"
        if vendor.exists():
            make_writable(vendor)
            shutil.move(str(vendor), backup)
        try:
            shutil.move(str(extracted), vendor)
            write_json(lock_path, lock)
            versions_path.write_text(render_versions(lock), encoding="utf-8")
            make_readonly(vendor)
        except Exception:
            if vendor.exists():
                make_writable(vendor)
                shutil.rmtree(vendor)
            if backup.exists():
                make_writable(backup)
                shutil.move(str(backup), vendor)
            raise
        if backup.exists():
            make_writable(backup)
            shutil.rmtree(backup)

    print(f"Vendored {release.tag} into {vendor}")
    github_output(
        {
            "tag": release.tag,
            "version": release.version,
            "commit": release.commit,
            "tree_sha256": tree_sha,
            "changed": "true",
        }
    )
    return lock


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--ref", help="Explicit upstream tag, for example transports/v2.4.0")
    parser.add_argument("--latest", action="store_true", help="Resolve the latest stable upstream tag")
    parser.add_argument("--include-prerelease", action="store_true")
    parser.add_argument("--force", action="store_true", help="Replace a locally modified vendored tree")
    parser.add_argument("--bump-revision", action="store_true", help="Rebuild the same upstream version")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not args.ref and not args.latest:
        args.latest = True
    if args.ref and args.latest:
        parser.error("--ref and --latest are mutually exclusive")
    return args


def main(argv: list[str] | None = None) -> int:
    try:
        sync(parse_args(argv))
    except (SyncError, subprocess.CalledProcessError, urllib.error.URLError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
