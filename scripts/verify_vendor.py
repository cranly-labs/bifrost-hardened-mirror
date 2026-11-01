#!/usr/bin/env python3
"""Verify that the vendored upstream tree and generated version files are intact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_upstream  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    lock_path = root / sync_upstream.LOCK_FILE
    if not lock_path.exists():
        print(f"error: {lock_path} is missing", file=sys.stderr)
        return 1

    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    vendor = root / sync_upstream.VENDOR_DIR
    if not vendor.is_dir():
        print(f"error: {vendor} is missing", file=sys.stderr)
        return 1

    expected = lock.get("vendor", {}).get("tree_sha256")
    actual, file_count = sync_upstream.tree_digest(vendor)
    if expected != actual:
        print(
            "error: vendored tree does not match vendor.lock.json\n"
            f"  expected {expected}\n"
            f"  actual   {actual}\n"
            "Move local changes into patches/ and re-run scripts/sync_upstream.py --force.",
            file=sys.stderr,
        )
        return 1

    versions_path = root / sync_upstream.VERSIONS_FILE
    expected_versions = sync_upstream.render_versions(lock)
    if not versions_path.exists() or versions_path.read_text(encoding="utf-8") != expected_versions:
        print(
            f"error: {versions_path} is out of date; regenerate it with "
            "scripts/sync_upstream.py --force",
            file=sys.stderr,
        )
        return 1

    upstream = lock["upstream"]
    print(
        f"OK: {upstream['tag']} ({upstream['commit'][:12]}), "
        f"{file_count} files, tree sha256 {actual}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
