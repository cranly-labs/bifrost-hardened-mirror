# Repository Settings

Configure these settings once after the repository is uploaded to GitHub. They
are part of the release safety model, not optional polish.

## Initial publication

The repository ships with repository placeholders in badges, documentation
links, CODEOWNERS, and the image label. Replace them before the first push:

```bash
make personalize OWNER=<github-owner> REPO=<repository-name>
git add -A
git commit -m "chore: personalize distribution"
git remote add origin git@github.com:<github-owner>/<repository-name>.git
git push -u origin main
```

The first push to `main` starts the verification and release workflows. The
release workflow creates the `production` branch and the first distribution
tag after the image passes every gate.


## Default branch

Keep `main` as the repository default branch. Automation assumes `main` is the
integration branch and `production` is a generated deployment branch.

## Actions permissions

**Settings > Actions > General**

- Allow all actions and reusable workflows.
- Workflow permissions: **Read repository contents and packages permissions**.
- Enable **Allow GitHub Actions to create and approve pull requests**.

The workflows request elevated permissions per job. The repository default stays
read-only.

## Branch protection: `main`

**Settings > Branches > Add branch protection rule**

- Branch name pattern: `main`
- Require a pull request before merging.
- Require approvals: `1` for team repositories; `0` is acceptable for a
  single-maintainer repository only if required status checks are enabled.
- Dismiss stale pull request approvals when new commits are pushed.
- Require status checks to pass before merging:
  - `Lint and integrity`
  - `Compose manifests`
  - `Build, smoke test, and scan`
- Require branches to be up to date before merging.
- Require linear history.
- Do not allow force pushes.
- Do not allow deletions.
- Restrict who can push if the organization supports it.

## Auto-merge

**Settings > General > Pull Requests**

- Enable **Allow auto-merge**.
- Enable **Automatically delete head branches**.

The sync workflow enables squash auto-merge. Without repository auto-merge, the
pull request remains open for a maintainer to merge after CI.

## Branch protection: `production`

Do not protect `production` with rules that block GitHub Actions. The release
workflow force-pushes an orphan deployment branch after a successful release.

If organizational policy requires protection, allow the release workflow's
GitHub App or token to bypass the rule.

## Environments

Create an environment named `production`.

- Optional: add required reviewers for manual approval of production promotion.
- Optional: restrict deployment branches to `main`.
- Add environment secrets only if they differ from repository secrets.

When no protection rules are configured, promotion is automatic after a
successful release. When reviewers are configured, the image and release are
published first; the production branch waits for approval.

## Secrets

**Settings > Secrets and variables > Actions**

| Secret | Required | Purpose |
|---|---|---|
| `COOLIFY_WEBHOOK` | For automatic deployment | Resource deploy webhook URL from Coolify. |
| `COOLIFY_TOKEN` | For automatic deployment | Coolify API token with `deploy` permission. |

`GITHUB_TOKEN` is provided automatically and is used for GHCR, tags, releases,
and the production branch.

Do not add provider API keys, gateway virtual keys, or database passwords to
GitHub. They belong in Coolify or a secret manager.

## GHCR package visibility

After the first release:

1. Open the package under the repository owner's **Packages**.
2. Set visibility to public, or keep it private and authenticate every Coolify
   server with a `read:packages` token.

Private package access is independent of repository access.

## Security features

Enable:

- Dependabot alerts.
- Dependabot security updates.
- Code scanning (CodeQL) if the repository is public.
- Secret scanning and push protection.
- Private vulnerability reporting.

## Tag protection

Protect `v*` and `upstream/**` tags from deletion and force updates after the
first release. Release tags are immutable audit records.

## Required checks after the first run

GitHub only offers status checks that have run at least once. Push the initial
commit, let CI and the first release run, then add the check names to the `main`
protection rule.

## Release recovery

Release tags and image tags are immutable.

- If a release fails **before** the distribution tag exists, fix the failing
  step and rerun the **Release** workflow. It retries the same version.
- If the tag exists but a later step failed, run `make bump-revision`, commit,
  and push. The next run publishes `vX.Y.Z-distro.N` and leaves the failed tag
  untouched for audit.

Never rebuild and overwrite an existing distribution tag.
