# Documentation

This directory describes the distribution layer: how upstream source becomes a
verified container image, how that image reaches Coolify, and how to operate it
in production.

| Document | Purpose |
|---|---|
| [Architecture](architecture.md) | System boundaries, release flow, and trust model |
| [Coolify deployment](coolify.md) | Production Compose deployment, storage, TLS, and rollback |
| [Operations](operations.md) | Health, sizing, backups, upgrades, and incident response |
| [Upstream synchronization](upstream-sync.md) | Vendoring model, lockfile, and automation |
| [Versioning](versioning.md) | Tag formats, distribution revisions, and release policy |
| [Repository settings](repository-settings.md) | Branch protection, secrets, environments, and registry access |
| [Troubleshooting](troubleshooting.md) | Common failure modes and diagnostics |
| [ADR 0001](adr/0001-vendored-upstream-snapshots.md) | Why the repository vendors snapshots instead of using a fork or submodule |

For upstream product behavior, provider configuration, and gateway APIs, use the
[Bifrost documentation](https://docs.getbifrost.ai/).
