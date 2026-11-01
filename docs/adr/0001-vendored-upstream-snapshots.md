# ADR 0001: Vendor upstream snapshots instead of using a fork or submodule

- Status: Accepted
- Date: 2026-11-01

## Context

The distribution must ship upstream Bifrost releases with a hardened build and
Coolify deployment, without depending on a fork's branch history or requiring
maintainers to resolve upstream merges by hand.

Three options were considered:

1. **Fork and merge upstream.** Familiar, but every sync is a merge conflict
   surface. A fork also creates ambiguity about which branch is authoritative.
2. **Git submodule.** Keeps the upstream repository separate, but adds a clone
   step for every consumer, complicates Coolify and CI checkouts, and still
   requires pinning a commit.
3. **Vendored snapshot with a lockfile.** Copies the upstream source into this
   repository, records the source tag, commit, Git tree, and a deterministic
   tree digest, and verifies the tree in CI.

## Decision

Use a vendored snapshot.

- `upstream/` contains the mirrored source.
- `vendor.lock.json` is the source of truth for the pinned release.
- `scripts/sync_upstream.py` performs a blobless sparse clone and writes the
  snapshot atomically.
- `scripts/verify_vendor.py` recomputes the tree digest in CI.
- Distribution-specific fixes live in `patches/`, never as edits to `upstream/`.

## Consequences

### Positive

- No fork history to maintain.
- Every upstream change is a reviewable pull request.
- The build is reproducible from a single commit in this repository.
- CI can prove that the vendored tree matches the lockfile.
- Coolify and other consumers need no submodule support.

### Negative

- The repository is larger than a thin wrapper around an image reference.
- Upstream changes appear as a snapshot diff instead of a merge history.
- A distribution patch must be maintained until upstream ships the fix.

### Mitigations

- The sparse clone excludes large documentation media and upstream CI metadata.
- The sync workflow runs frequently and opens a focused pull request.
- Patches have a documented removal condition and are applied in a dedicated
  build stage.
