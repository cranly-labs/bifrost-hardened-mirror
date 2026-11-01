#!/usr/bin/env python3
"""Increment the distribution revision for a build-only release."""

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
    parser.add_argument("--set", type=int, dest="revision", help="Set an explicit revision")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    lock_path = root / sync_upstream.LOCK_FILE
    versions_path = root / sync_upstream.VERSIONS_FILE
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    current = int(lock["distribution"]["revision"])
    revision = args.revision if args.revision is not None else current + 1
    if revision <= current:
        print(f"error: revision must be greater than {current}", file=sys.stderr)
        return 1

    lock["distribution"]["revision"] = revision
    sync_upstream.write_json(lock_path, lock)
    versions_path.write_text(sync_upstream.render_versions(lock), encoding="utf-8")
    print(f"Distribution revision: {current} -> {revision}")
    print(f"Next release tag: v{lock['upstream']['version']}" + ("" if revision == 1 else f"-distro.{revision}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
