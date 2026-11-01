## Summary

<!-- What changes, and why? Keep it short and factual. -->

## Change type

- [ ] Distribution build or runtime image
- [ ] Upstream synchronization
- [ ] Release or deployment automation
- [ ] Documentation
- [ ] Security hardening

## Verification

- [ ] `python3 -m unittest discover -s tests -v`
- [ ] `python3 scripts/verify_vendor.py`
- [ ] `docker compose -f deploy/coolify/compose.yaml config` with validation env
- [ ] Container smoke test passes locally
- [ ] No secrets, credentials, or customer data are included

## Operational notes

<!-- Rollback plan, migration notes, or "none". -->

## Upstream alignment

<!-- For patches: link the upstream issue or pull request and explain why a
distribution patch is required instead of waiting for upstream. -->
