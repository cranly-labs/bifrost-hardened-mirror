# Troubleshooting

## Build failures

### Go build cannot find SQLite headers

The builder stage must include `gcc`, `musl-dev`, and `sqlite-dev`. The official
Dockerfile installs them and builds with:

```text
CGO_ENABLED=1
-tags sqlite_static
-extldflags '-static'
```

Do not switch the runtime image to a non-musl base without revalidating the
static SQLite link.

### UI build fails on `npm ci`

Confirm that `upstream/ui/package-lock.json` is present and matches
`package.json`. The sync workflow mirrors both. If upstream changes the lockfile
format or Node major version, update the `node` base image and rerun CI.

### ARM64 build fails under QEMU

Multi-architecture builds use QEMU for `linux/arm64`. A failure usually means a
native dependency is not available for the target architecture. Check the
builder logs for the failing package and confirm that the Alpine package exists
for `aarch64`.

## Smoke test failures

### Container exits with a data-directory error

The runtime user is `10001:10001`. A named volume created from the image inherits
that ownership. A bind mount must be writable by the same UID/GID.

```bash
docker run --rm -v bifrost-data:/data alpine:3.23 ls -ln /data
```

### `/health` returns 503

`/health` checks configured stores. Confirm:

- PostgreSQL is reachable and version 16 or newer.
- The database user can run migrations.
- The SQLite volume is writable and has free space.
- The vector store is reachable if semantic caching is enabled.

### `/api/version` does not match the release

The binary embeds `main.Version` from the build argument. Confirm the build used
`BIFROST_VERSION` from `vendor.lock.json` and that the release tag matches the
lockfile.

## Coolify failures

### `pull access denied` or `unauthorized`

The GHCR package is private. Authenticate the deployment server:

```bash
echo "$GHCR_READ_TOKEN" | docker login ghcr.io --username "$GHUB_USERNAME" --password-stdin
```

Then redeploy. The token needs `read:packages`.

### Compose interpolation error

The production branch manifest requires `BIFROST_ENCRYPTION_KEY`. Set it in
Coolify. If deploying the main-branch template directly, also set
`BIFROST_IMAGE`.

### Container is running but the domain returns 404

- Confirm the Coolify domain targets service `bifrost` and port `8080`.
- Confirm the container is healthy.
- Confirm Coolify generated the Traefik labels; do not add manual labels.
- Confirm the proxy network is attached to the Compose service.

### Streaming responses arrive all at once

A proxy is buffering. Verify that Coolify's Traefik configuration forwards
streaming responses and that no CDN or intermediate proxy buffers
`text/event-stream`.

### Deployment succeeds but the old version still serves

- Confirm Coolify pulled the digest from the new `production` commit.
- Confirm the service image is digest-pinned, not a local cached tag.
- Force a redeploy in Coolify.
- Check that the release workflow actually updated `production`.

## Runtime failures

### Dashboard has no password

A fresh instance starts without a dashboard password. Create the first admin
account immediately and enable password protection. The first admin creation
requires `BIFROST_SETUP_TOKEN`.

### Provider credentials are unreadable after restore

The restore used a different `BIFROST_ENCRYPTION_KEY`. Restore the original key
or re-enter the provider credentials.

### SQLite database is locked

Only one Bifrost process may use a SQLite database. Scale out with PostgreSQL
instead of sharing the volume.

### High memory usage

- Set `GOMEMLIMIT` to about 90% of the container memory limit.
- Lower `GOGC` under memory pressure.
- Inspect request body size and semantic-cache settings.
- Confirm the container limit matches the host capacity.

## Release failures

### Tag already exists

Distribution tags are immutable. If the tag exists but a later release step
failed, run `make bump-revision`, commit, and push. The next run publishes
`vX.Y.Z-distro.N`. Do not delete or move the existing tag.

### Vulnerability scan fails

Review the Trivy output. Add an exception to `.trivyignore` only with a CVE,
rationale, and expiry date. Prefer a base-image update or an upstream fix.

### Cosign signing fails

Keyless signing requires `id-token: write` and a GitHub OIDC token. Confirm the
job permissions and that the repository is on GitHub.com. Private repositories
can use keyless signing; the resulting certificate identity is the workflow
identity.

### Coolify webhook returns 401 or 403

- The token must have `deploy` permission.
- The token must belong to the team that owns the resource.
- Copy the resource webhook URL again; it must contain a `uuid`.
- Check that the token has not expired.
