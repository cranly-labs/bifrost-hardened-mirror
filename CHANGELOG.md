# Changelog

All notable changes to the distribution layer are documented here. Upstream
application changes are described in the corresponding Bifrost release notes.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
the distribution uses upstream gateway versions with an optional distribution
revision suffix.

## [Unreleased]

## [2.4.0] - 2026-11-01

### Added

- Initial distribution repository with a verified vendored snapshot of Bifrost
  `transports/v2.4.0`.
- Multi-stage production image with pinned base images, non-root runtime,
  TINI signal handling, and a container health check.
- Automated upstream synchronization with integrity verification and pull
  request gating.
- Multi-architecture GHCR releases for `linux/amd64` and `linux/arm64`.
- Trivy vulnerability gate, SPDX SBOM generation, BuildKit provenance, and
  Cosign keyless signing.
- Digest-pinned `production` branch and Coolify deploy webhook integration.
- Coolify Compose manifest with persistent storage, resource limits, log
  rotation, and hardened container options.

[Unreleased]: https://github.com/OWNER/REPO/compare/v2.4.0...HEAD
[2.4.0]: https://github.com/OWNER/REPO/releases/tag/v2.4.0
