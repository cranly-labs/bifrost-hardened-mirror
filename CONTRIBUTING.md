# Contributing

## Repository model

This repository is a distribution, not a fork. The upstream gateway source is
vendored under `upstream/` from a pinned `transports/v*` release tag. The
distribution layer owns the build, release pipeline, deployment manifests, and
operations documentation.

Three rules keep the model stable:

1. Do not edit `upstream/` by hand. CI verifies its tree hash against
   `vendor.lock.json`. Vendored files are read-only on POSIX; disable IDE Go
   module auto-tidy for this repository so it cannot rewrite upstream module
   files.
2. Put build or runtime fixes in the distribution layer whenever possible.
3. If an upstream patch is unavoidable, add a reviewed unified diff under
   `patches/` and document why the fix cannot wait for upstream.

## Local workflow

Requirements: Docker with BuildKit, Python 3.11 or newer, Git, and `make`.

```bash
make help          # list targets
make verify        # vendor integrity and distribution tests
make build         # build the local image
make smoke         # build, start, and probe the image
make up            # start the local Compose stack
```

The local stack listens on `127.0.0.1:8080` and stores state in the
`bifrost-data` volume.

## Upstream synchronization

```bash
make sync                                  # latest stable gateway release
make sync-ref REF=transports/v2.4.0        # explicit release
python3 scripts/sync_upstream.py --dry-run # inspect without writing
```

The synchronization script performs a blobless sparse clone, excludes upstream
CI metadata and hosted documentation media, and writes a new `vendor.lock.json`
and `versions.env`. The scheduled workflow opens a pull request and enables
auto-merge. Branch protection requires CI to pass before the pull request can
merge.

## Distribution rebuilds

A build-only change for the same upstream version needs a new distribution
revision:

```bash
make bump-revision
git add vendor.lock.json versions.env
git commit -m "chore: bump distribution revision"
```

The next release is tagged `vX.Y.Z-distro.N`. Distribution tags are immutable.

## Patches

A distribution patch must include:

- A unified diff in `patches/` that applies with `-p1` from the repository root.
- A short rationale in the patch or a linked issue.
- A test that fails without the patch, or a documented reason why a test is not
  practical.
- A removal condition: the upstream release that makes the patch unnecessary.

## Pull requests

- Keep changes focused and explain the operational impact.
- Update documentation when a deployment contract changes.
- Do not commit secrets, generated credentials, or customer data.
- Complete the verification checklist in the pull request template.

## Commit conventions

Use Conventional Commits:

```text
feat(deploy): add Coolify health-check guidance
fix(docker): preserve SQLite static linking on arm64
chore(upstream): sync Bifrost v2.4.0
docs(security): document Cosign verification
```

## Release process

Releases are automatic:

1. A verified upstream synchronization lands on `main`.
2. CI builds, smoke-tests, and scans the image.
3. The release workflow publishes a multi-arch signed image to GHCR.
4. A digest-pinned manifest is written to the `production` branch.
5. Coolify is triggered through an authenticated deploy webhook.

A failed build, smoke test, scan, or signing step stops the pipeline before the
production branch changes.
