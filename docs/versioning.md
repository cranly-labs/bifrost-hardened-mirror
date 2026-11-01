# Versioning

## Version source

The distribution version follows the upstream gateway tag:

| Upstream | Distribution |
|---|---|
| `transports/v2.4.0` | `v2.4.0` |
| `transports/v2.4.0-rc.1` | `v2.4.0-rc.1` |

The gateway image version is independent of upstream `core/`, `framework/`, and
plugin versions. Those components are resolved by `transports/go.mod` at build
time.

## Distribution revision

A distribution revision is needed when the upstream source is unchanged but the
distribution must publish a new image, for example:

- A Dockerfile hardening change.
- A base-image security update.
- A build-only fix that changes the artifact.

Run `make bump-revision` and commit the updated lockfile and `versions.env`.
The next release uses:

```text
v2.4.0-distro.2
```

The first build of a version uses the plain tag, `v2.4.0`.

## Image tags

| Tag | Meaning |
|---|---|
| `v2.4.0` | Exact distribution release. Immutable in production. |
| `v2.4.0-distro.2` | Distribution rebuild of the same upstream version. |
| `latest` | Most recent stable release. Convenience only; never use in production. |
| `sha-<commit>` | Build provenance tag for the release commit. |

Production deployments pin a digest:

```text
ghcr.io/OWNER/REPO@sha256:<64 hex characters>
```

Tags are human-readable pointers. Digests are the deployment identity.

## Pre-release policy

Upstream prerelease tags are excluded from automatic synchronization. They can
be synced manually for evaluation, and the release workflow marks the GitHub
release as a prerelease. Prerelease images do not update `latest`.

## Compatibility

- The distribution does not modify upstream API or configuration semantics.
- Distribution patches must be documented and removed when upstream ships the
  fix.
- Breaking upstream changes are called out in the upstream release notes and in
  this repository's release entry.

## Deprecation

A distribution tag is never deleted or moved. If a release is defective, publish
a new distribution revision and document the superseded tag in the release
notes.
