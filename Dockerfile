# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
#
# Production image for the Bifrost distribution.
#
# The upstream source is vendored under upstream/ and verified in CI before this
# file is built. Base images are pinned by digest; update them through
# Dependabot or an explicit, reviewed change.

# ---------------------------------------------------------------------------
# Source preparation: apply optional distribution patches once.
# ---------------------------------------------------------------------------
FROM --platform=$BUILDPLATFORM alpine:3.23.5@sha256:fd791d74b68913cbb027c6546007b3f0d3bc45125f797758156952bc2d6daf40 AS source

RUN apk add --no-cache patch
WORKDIR /src
COPY upstream/ ./
COPY patches/ /tmp/patches/
RUN set -eu; \
    found=0; \
    for patch_file in /tmp/patches/*.patch; do \
      [ -f "$patch_file" ] || continue; \
      echo "Applying distribution patch: $patch_file"; \
      patch -p1 -d /src < "$patch_file"; \
      found=1; \
    done; \
    [ "$found" -eq 1 ] || echo "No distribution patches present"

# ---------------------------------------------------------------------------
# UI build
# ---------------------------------------------------------------------------
FROM --platform=$BUILDPLATFORM node:25-alpine3.23@sha256:bdf2cca6fe3dabd014ea60163eca3f0f7015fbd5c7ee1b0e9ccb4ced6eb02ef4 AS ui-builder

ENV NEXT_TELEMETRY_DISABLED=1 \
    npm_config_update_notifier=false \
    npm_config_fund=false \
    npm_config_audit=false

WORKDIR /src/ui
COPY --from=source /src/ui/package.json /src/ui/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund --fetch-retries=5 --fetch-retry-maxtimeout=120000
COPY --from=source /src/ui/ ./
RUN npm run build-enterprise

# ---------------------------------------------------------------------------
# Go build (CGO + statically linked SQLite)
# ---------------------------------------------------------------------------
FROM golang:1.27.3-alpine3.24@sha256:d200d2dd76b03a99b52651fd1325aff7dcd35422c35c01bac56571b0507f3deb AS go-builder

ARG TARGETOS
ARG TARGETARCH
ARG BIFROST_VERSION=dev
ARG GOPROXY="https://proxy.golang.org|https://goproxy.io|direct"

# Docker Desktop and some corporate proxies mishandle HTTP/2 to Go module
# proxies under parallel downloads. HTTP/1.1 is slower but reliable.
ENV CGO_ENABLED=1 \
    GOWORK=off \
    GOTOOLCHAIN=local \
    GOFLAGS=-buildvcs=false \
    GOPROXY=${GOPROXY} \
    GODEBUG=http2client=0

RUN apk add --no-cache gcc musl-dev sqlite-dev binutils binutils-gold

WORKDIR /src/transports
COPY --from=source /src/transports/go.mod /src/transports/go.sum ./
RUN --mount=type=cache,id=bifrost-go-mod,target=/go/pkg/mod \
    set -eu; \
    attempt=1; \
    until go mod download; do \
      if [ "$attempt" -ge 5 ]; then \
        echo "go mod download failed after ${attempt} attempts" >&2; \
        exit 1; \
      fi; \
      echo "go mod download failed (attempt ${attempt}); retrying in $((attempt * 5))s" >&2; \
      sleep $((attempt * 5)); \
      attempt=$((attempt + 1)); \
    done
COPY --from=source /src/transports/ ./
COPY --from=ui-builder /src/ui/out ./bifrost-http/ui

RUN --mount=type=cache,id=bifrost-go-mod,target=/go/pkg/mod \
    --mount=type=cache,id=bifrost-go-build,target=/root/.cache/go-build \
    CGO_ENABLED=1 \
    GOOS="${TARGETOS:-linux}" \
    GOARCH="${TARGETARCH:-$(go env GOARCH)}" \
    go build \
      -ldflags="-w -s -X main.Version=v${BIFROST_VERSION} -extldflags '-static'" \
      -trimpath \
      -tags "sqlite_static" \
      -o /out/main \
      ./bifrost-http

RUN test -x /out/main

# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------
FROM alpine:3.23.5@sha256:fd791d74b68913cbb027c6546007b3f0d3bc45125f797758156952bc2d6daf40 AS runtime

ARG BIFROST_VERSION=dev
ARG BIFROST_REVISION=unknown
ARG BUILD_DATE=unknown

RUN apk add --no-cache ca-certificates tzdata libgcc tini \
    && addgroup -g 10001 -S bifrost \
    && adduser -u 10001 -S -G bifrost -h /app -s /sbin/nologin bifrost

WORKDIR /app
COPY --from=go-builder /out/main /app/main
COPY --from=source /src/transports/docker-entrypoint.sh /app/docker-entrypoint.sh
COPY docker/healthcheck.sh /app/healthcheck.sh
RUN mkdir -p /app/data/logs \
    && chown -R 10001:10001 /app/data \
    && chmod 0755 /app/docker-entrypoint.sh /app/healthcheck.sh

LABEL org.opencontainers.image.title="Bifrost Distribution" \
      org.opencontainers.image.description="Reproducible, supply-chain-hardened Bifrost AI Gateway distribution" \
      org.opencontainers.image.version="${BIFROST_VERSION}" \
      org.opencontainers.image.revision="${BIFROST_REVISION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.source="https://github.com/OWNER/REPO" \
      org.opencontainers.image.base.name="alpine:3.23.5" \
      com.bifrost.distribution="true"

ENV APP_PORT=8080 \
    APP_HOST=0.0.0.0 \
    APP_DIR=/app/data \
    LOG_LEVEL=info \
    LOG_STYLE=json

USER 10001:10001
VOLUME ["/app/data"]
EXPOSE 8080
STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD ["/app/healthcheck.sh"]

ENTRYPOINT ["/sbin/tini", "--", "/app/docker-entrypoint.sh"]
CMD ["/app/main"]
