# Distribution patches

`upstream/` is an immutable vendored snapshot. Do not edit it directly; CI
verifies its tree hash against `vendor.lock.json`.

When a distribution-specific fix is unavoidable, add a unified diff here:

```bash
git diff --no-index a/upstream/transports/path b/upstream/transports/path \
  | sed 's#a/upstream/#a/#; s#b/upstream/#b/#' > patches/0001-short-description.patch
```

The Docker build applies patches in lexical order inside a dedicated source
stage, before the UI and Go builds. Patches must apply cleanly with `-p1` from
the vendored repository root and must include a test or a documented rationale.
The image build consumes `ui/` and `transports/`; `core`, `framework`, and
plugins are resolved as published Go modules from `transports/go.mod`.

Keep this directory empty in normal operation. Every patch is a deliberate,
reviewed deviation from upstream and must be removed once upstream carries the
fix.
