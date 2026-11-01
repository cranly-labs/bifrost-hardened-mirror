#!/usr/bin/env python3
"""Report whether a newer Bifrost gateway release is available upstream."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_upstream  # noqa: E402


def github_output(values: dict[str, str]) -> None:
    destination = os.environ.get("GITHUB_OUTPUT")
    if not destination:
        return
    with open(destination, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--include-prerelease", action="store_true")
    args = parser.parse_args(argv)

    lock_path = Path(args.root) / sync_upstream.LOCK_FILE
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        lock = {}

    current_tag = lock.get("upstream", {}).get("tag", "")
    try:
        latest = sync_upstream.latest_tag(include_prerelease=args.include_prerelease)
        release = sync_upstream.resolve_release(latest)
    except Exception as error:  # network or parsing failure must be visible in CI
        print(f"error: {error}", file=sys.stderr)
        return 1

    update = latest != current_tag
    print(f"current={current_tag or '<none>'}")
    print(f"latest={latest}")
    print(f"update={'true' if update else 'false'}")
    github_output(
        {
            "current": current_tag,
            "latest": latest,
            "version": release.version,
            "commit": release.commit,
            "update": "true" if update else "false",
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
