# Security Policy

## Supported versions

Only the latest published distribution release receives security updates. The
distribution tracks upstream security fixes through the automated synchronization
pipeline. Older tags remain available for rollback but are not patched in place.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability.

Use GitHub's private vulnerability reporting:

1. Open the repository's **Security** tab.
2. Select **Advisories**.
3. Select **Report a vulnerability**.

Include the affected release tag, image digest, reproduction steps, and the
security impact. If the issue originates in upstream Bifrost, the report will be
coordinated with the upstream maintainers through their published security
process.

## Supply-chain controls

The distribution is designed so that a compromised or broken upstream release
cannot reach production silently.

| Control | Implementation |
|---|---|
| Reproducible source snapshot | `upstream/` is vendored from a pinned upstream tag; `vendor.lock.json` records the commit, Git tree, file count, and SHA-256 tree digest. |
| Integrity verification | `scripts/verify_vendor.py` recomputes the tree digest in CI. Local edits to `upstream/` fail the build. |
| Build isolation | Multi-stage build; no compilers, language toolchains, or build tooling in the runtime image. |
| Non-root runtime | The production Compose manifest runs as UID/GID `10001`, drops all Linux capabilities, and enables `no-new-privileges`. |
| Immutable production image | The `production` branch pins an image digest, not a mutable tag. |
| Vulnerability gate | Trivy blocks releases with fixable `HIGH` or `CRITICAL` findings. |
| SBOM | An SPDX JSON SBOM is generated for every release and attached to the GitHub release. |
| Signing | Release images are signed with Cosign keyless signing through GitHub OIDC. |
| Provenance | BuildKit provenance and SBOM attestations are published with the image manifest. |

## Verify a release

```bash
IMAGE="ghcr.io/cranly-labs/bifrost-hardened-mirror@sha256:<digest>"

cosign verify "$IMAGE" \
  --certificate-identity-regexp '^https://github.com/cranly-labs/bifrost-hardened-mirror/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com

docker buildx imagetools inspect "$IMAGE"
```

The release page also publishes the SPDX SBOM for offline review.

## Secrets

The repository must never contain provider keys, gateway virtual keys, database
passwords, `BIFROST_SETUP_TOKEN`, or `BIFROST_ENCRYPTION_KEY`. Production
secrets belong in Coolify's environment configuration or an external secret
manager.

`BIFROST_ENCRYPTION_KEY` is a long-lived data-encryption key. Rotating it makes
previously encrypted provider credentials unreadable. Back it up with the same
care as the database.

## Scope

This policy covers the distribution layer in this repository: the container
build, release automation, deployment manifests, and documentation. Upstream
Bifrost application vulnerabilities are handled through the upstream project,
but this repository will ship the fix as soon as a verified upstream release is
available.
