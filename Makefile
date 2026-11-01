SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

ROOT := $(CURDIR)
VERSION := $(shell python3 -c 'import json; print(json.load(open("vendor.lock.json"))["upstream"]["version"])')
TAG := $(shell python3 -c 'import json; print(json.load(open("vendor.lock.json"))["upstream"]["tag"])')
COMMIT := $(shell python3 -c 'import json; print(json.load(open("vendor.lock.json"))["upstream"]["commit"])')
REVISION := $(shell python3 -c 'import json; print(json.load(open("vendor.lock.json"))["distribution"]["revision"])')
GIT_REVISION ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo local)
BUILD_DATE ?= $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
IMAGE ?= bifrost-distribution:local

.PHONY: help sync sync-ref bump-revision verify test build smoke up down logs compose-check render-production personalize release-check sbom scan clean

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*##"; printf "\nBifrost distribution\n\nUsage: make <target>\n\n"} /^[a-zA-Z0-9_.-]+:.*?##/ { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@printf "\nPinned upstream: %s (%s)\n\n" "$(TAG)" "$(COMMIT)"

sync: ## Sync the latest stable upstream gateway release
	python3 scripts/sync_upstream.py --latest

sync-ref: ## Sync an explicit upstream tag (REF=transports/v2.4.0)
	@test -n "$(REF)" || (echo "REF is required, for example REF=transports/v2.4.0" >&2; exit 1)
	python3 scripts/sync_upstream.py --ref "$(REF)" --force

bump-revision: ## Increment distribution revision for a build-only release
	python3 scripts/bump_revision.py

verify: ## Verify the vendored tree and run distribution tests
	python3 scripts/verify_vendor.py
	python3 -m unittest discover -s tests -v

test: verify ## Alias for verify

build: ## Build the local image
	docker build \
		--build-arg BIFROST_VERSION="$(VERSION)" \
		--build-arg BIFROST_REVISION="$(GIT_REVISION)" \
		--build-arg BUILD_DATE="$(BUILD_DATE)" \
		-t "$(IMAGE)" .

smoke: build ## Build and smoke-test the local image
	IMAGE="$(IMAGE)" BIFROST_VERSION="$(VERSION)" scripts/smoke_test.sh

up: ## Start the local stack
	BIFROST_VERSION="$(VERSION)" BIFROST_REVISION="$(GIT_REVISION)" BUILD_DATE="$(BUILD_DATE)" docker compose up -d --build

down: ## Stop the local stack
	docker compose down

logs: ## Follow local stack logs
	docker compose logs -f --tail=100

compose-check: ## Validate the Coolify Compose template
	BIFROST_IMAGE=ghcr.io/example/bifrost:v$(VERSION) \
	BIFROST_ENCRYPTION_KEY=validation-only \
	docker compose -f deploy/coolify/compose.yaml config >/dev/null

render-production: ## Render a digest-pinned production manifest (IMAGE=... VERSION=...)
	@test -n "$(IMAGE)" || (echo "IMAGE is required" >&2; exit 1)
	@test -n "$(VERSION)" || (echo "VERSION is required" >&2; exit 1)
	python3 scripts/render_production.py --image "$(IMAGE)" --version "$(VERSION)" \
		--upstream-tag "$(TAG)" --upstream-commit "$(COMMIT)"

personalize: ## Replace repository placeholders (OWNER=... REPO=...)
	@test -n "$(OWNER)" || (echo "OWNER is required" >&2; exit 1)
	@test -n "$(REPO)" || (echo "REPO is required" >&2; exit 1)
	python3 scripts/personalize.py --owner "$(OWNER)" --repo "$(REPO)"

release-check: ## Validate release inputs without building
	python3 scripts/verify_vendor.py
	python3 -m unittest discover -s tests -v
	@test -z "$$(git status --porcelain)" || (echo "Working tree is not clean" >&2; exit 1)
	@echo "Release candidate: v$(VERSION) (distribution revision $(REVISION))"

sbom: ## Generate an SBOM with Syft
	mkdir -p sbom
	syft "$(IMAGE)" -o spdx-json=sbom/bifrost.spdx.json

scan: ## Scan the local image with Trivy
	trivy image --severity HIGH,CRITICAL --ignore-unfixed "$(IMAGE)"

clean: ## Remove local build and runtime artifacts
	rm -rf dist .tmp data sbom
