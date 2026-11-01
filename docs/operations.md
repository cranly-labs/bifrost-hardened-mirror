# Operations

## Service contract

| Property | Value |
|---|---|
| HTTP port | `8080` |
| Health endpoint | `GET /health` |
| Version endpoint | `GET /api/version` |
| Metrics endpoint | `GET /metrics` when Prometheus telemetry is enabled |
| Data directory | `/app/data` |
| Runtime user | `10001:10001` |
| Shutdown signal | `SIGTERM`, forwarded by TINI |
| Shutdown window | Up to 30 seconds internally; 45-second container grace period |

`/health` returns `200` only when the gateway is ready. By default it also
checks the configured config, log, and vector stores and returns `503` when a
required dependency is unavailable.

## Sizing

Start with 2 vCPU and 2 GB of memory for a small team or evaluation workload.
Increase memory before CPU for large request bodies, semantic caching, and
high-concurrency streaming.

| Workload | CPU | Memory | `GOGC` | `GOMEMLIMIT` |
|---|---:|---:|---:|---:|
| Evaluation | 1 | 1 GB | 100 | 900MiB |
| Small production | 2 | 2 GB | 200 | 1800MiB |
| High throughput | 4 | 4 GB | 200 | 3600MiB |
| Memory constrained | 2 | 1 GB | 50 | 900MiB |

Bifrost uses `automaxprocs` to honor the container CPU quota. `GOMAXPROCS` does
not need manual configuration.

## Logging

Container logs are JSON on stdout. The Compose manifest rotates the Docker log
file at 20 MB with five retained files.

Recommended log levels:

- `info` in production.
- `debug` only for a bounded investigation.
- `warn` or `error` for high-volume installations with external log collection.

Request logs are stored separately in `logs.db` when SQLite logging is enabled.
Plan retention and backup accordingly.

## Backup

### What to back up

- `/app/data/config.db` — gateway configuration and encrypted provider
  credentials.
- `/app/data/logs.db` — request logs, if required for audit.
- `/app/data/config.json` — declarative configuration, if used.
- `BIFROST_ENCRYPTION_KEY` — from the secret store, never from the container.
- `BIFROST_SETUP_TOKEN` — only until the first administrator exists.

### Consistent SQLite backup

```bash
docker run --rm \
  -v bifrost-data:/data:ro \
  -v "$PWD/backup:/backup" \
  alpine:3.23 \
  sh -c 'apk add --no-cache sqlite >/dev/null && \
    sqlite3 /data/config.db ".backup /backup/config.db" && \
    sqlite3 /data/logs.db ".backup /backup/logs.db"'
```

Run the backup from the same host as the volume. For a cold backup, stop the
container first.

### Restore

1. Stop the Coolify service.
2. Restore `config.db` and `logs.db` into the volume.
3. Restore the same `BIFROST_ENCRYPTION_KEY`.
4. Start the service.
5. Confirm `/health`, then verify that a configured provider still resolves.

A database restored without the original encryption key will start, but
encrypted provider credentials will be unreadable.

## Upgrade

Upgrades are automatic. The release workflow only updates the `production`
branch after the image is built, scanned, signed, and attached to a release.

To upgrade manually, redeploy the Coolify resource after the `production` branch
advances. To pin an older release, change the image digest in Coolify to the
prior release artifact.

## Rollback

Rollback uses an immutable artifact, not a source rebuild.

1. Open the previous GitHub release and copy the image digest from its notes.
2. Alternatively, use Coolify's rollback list or a locally retained image.
3. Redeploy the corresponding digest in Coolify.

The `production` branch is force-pushed and intentionally history-free. GitHub
Releases, distribution tags, and Coolify's rollback list are the rollback
sources. Do not rebuild an old source tag during an incident; the signed digest
is the recoverable artifact.

## Secret rotation

### Provider credentials

Provider keys are managed in the Bifrost dashboard or configuration. Rotate them
through the upstream rotation flow. They are encrypted at rest when
`BIFROST_ENCRYPTION_KEY` is set.

### Gateway virtual keys

Create the replacement key, distribute it, then revoke the old key. Bifrost's
virtual-key rotation has a grace window controlled by `vk_rotation_cooldown`.

### Encryption key

Treat `BIFROST_ENCRYPTION_KEY` as immutable for the life of the data set.
Rotating it without re-encrypting stored credentials makes them unreadable.

### Setup token

The setup token is only needed before the first administrator exists. Remove it
from Coolify after the administrator is created.

## Monitoring

Minimum production signals:

- `/health` availability and latency from an external prober.
- Container restarts and OOM kills.
- CPU and memory versus configured limits.
- Go runtime heap and GC pause metrics, when Prometheus telemetry is enabled.
- Provider error rate and latency from Bifrost logs or an observability plugin.
- Disk usage for the `bifrost-data` volume.

Alert on sustained `/health` failures, repeated restarts, and volume usage above
80%.

## Incident response

### Container is unhealthy

1. Check Coolify deployment logs and container logs.
2. Confirm `/health` from inside the container:
   `wget -q -O - http://127.0.0.1:8080/health`.
3. Check volume writability and free space.
4. Check database connectivity if PostgreSQL is configured.
5. If the previous digest was healthy, roll back first and investigate after
   service is restored.

### Container exits immediately

Common causes:

- `/app/data` is not writable by UID `10001`.
- PostgreSQL is unreachable or older than version 16.
- `config.json` is invalid.
- A required environment variable is missing from the Compose interpolation.

### High memory or OOM

1. Compare `GOMEMLIMIT` with the container memory limit. It should be about 90%.
2. Reduce `GOGC` if memory is constrained.
3. Inspect request body size limits and semantic-cache configuration.
4. Increase the memory limit only after confirming the workload requires it.

### Streaming responses are buffered

The reverse proxy is buffering. Confirm that Coolify's Traefik configuration
forwards streaming responses and that no intermediate proxy or CDN buffers
`text/event-stream` responses.

### SQLite database is locked

Confirm that only one Bifrost process uses the database. Do not scale a SQLite
deployment horizontally or share the volume between containers.
