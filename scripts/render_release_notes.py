#!/usr/bin/env python3
"""Render GitHub release notes for a distribution release."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.github.com/repos/maximhq/bifrost/releases/tags/"


def upstream_notes(tag: str) -> str:
    url = API + urllib.parse.quote(tag, safe="")
    request = urllib.request.Request(url, headers={"User-Agent": "bifrost-distribution-release/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as error:
        return f"_Upstream release notes could not be fetched: {error}_"
    body = (payload.get("body") or "").strip()
    if len(body) > 50000:
        body = body[:50000] + "\n\n_Release notes truncated._"
    return body or "_Upstream release notes were empty._"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--upstream-tag", required=True)
    parser.add_argument("--upstream-commit", required=True)
    parser.add_argument("--upstream-release-url", default="")
    parser.add_argument("--repository", required=True, help="GitHub owner/repository")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    release_url = args.upstream_release_url or (
        "https://github.com/maximhq/bifrost/releases/tag/"
        + urllib.parse.quote(args.upstream_tag, safe="")
    )
    notes = f"""## Bifrost distribution {args.version}

An immutable, supply-chain-verified build of the Bifrost AI Gateway.

| | |
|---|---|
| Upstream release | [{args.upstream_tag}]({release_url}) |
| Upstream commit | `{args.upstream_commit}` |
| Container image | `{args.image}` |
| Immutable digest | `{args.digest}` |

### Verify the artifact

```bash
docker pull {args.image}@{args.digest}
cosign verify {args.image}@{args.digest} \\
  --certificate-identity-regexp '^https://github.com/{args.repository}/' \\
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

The release includes an SPDX JSON SBOM. The image is built for
`linux/amd64` and `linux/arm64`, runs as a non-root user, and carries a
container health check.

### Upstream release notes

{upstream_notes(args.upstream_tag)}
"""

    output = Path(args.output)
    output.write_text(notes, encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
