---
name: hc-gitflow-cicd
description: Apply GitFlow rules to this repo and map them onto the CI/CD pipelines. Use when the user asks to "open a PR", "cut a release", "create a hotfix", "what branch should this go on", "promote to test/prod", "what does pr-validate do", or anything about the four GitHub Actions workflows or the branch → environment mapping. Codifies the branch protection rules, naming conventions, and the deploy triggers.
---

# hc-gitflow-cicd

GitFlow + branch-driven deploys + per-feature-branch Lakebase isolation. This skill is the source of truth for **which branch produces what deployment and when**.

## When to use

- "I need to start work on HC-123" → which branch?
- "Cut a release for v0.4.0"
- "Hotfix prod" — what's the procedure?
- "What does the pr-validate workflow do?"
- "Why isn't my deploy triggering?"
- The user is editing `.github/workflows/*.yml`

## When NOT to use

- The user is configuring a Lakebase branch — that's `hc-lakebase-branching`.
- The user is editing DAB resources — that's `hc-dab-deployment`.
- The user is configuring branch protection rules in GitHub UI — that's a one-time setup, documented at the bottom of this skill.

## The branch → environment map

| Branch / event | Environment deployed | Workflow file | Lakebase isolation |
|---|---|---|---|
| `feature/<TICKET>-<slug>` (PR open) | preview app(s) `<svc>-dev-feat-<slug>` in **dev** workspace | `pr-validate.yml` | per-feature Lakebase branch `feat-<slug>`, used for both local dev and PR CI |
| `develop` (push) | full **dev** target (`<svc>-dev`) | `deploy-dev.yml` | `production` branch only |
| `release/<version>` (push) | **test** target (`<svc>-test`) | `deploy-test.yml` | `production` branch in `<svc>-test` |
| `main` (push, no tag) | **test** target | `deploy-test.yml` | same as above |
| Tag `v*` on `main` (push) | **prod** target (`<svc>-prod`), gated by manual approval | `deploy-prod.yml` | `production` branch in `<svc>-prod` |
| `hotfix/<TICKET>-<slug>` (PR open) | preview app in **dev** workspace, *no* fast-track | `pr-validate.yml` | same per-feature isolation |

```
                                  ┌──────────────┐
                                  │   dev WS     │ ← develop + per-feature previews
                                  └──────────────┘
                                          ▲
   feature/HC-123 ──── PR ────► develop ──┘
                                   │
                                   │ (cut release branch when ready)
                                   ▼
                            release/v0.4.0  ─── PR ────► main ──── tag v0.4.0
                                   │                      │              │
                                   │                      ▼              ▼
                                   │              ┌──────────────┐ ┌──────────────┐
                                   │              │   test WS    │ │   prod WS    │
                                   │              └──────────────┘ └──────────────┘
                                   ▼                      ▲              ▲
                              hotfix/HC-456 ─── PR ───────┘              │
                                                                  (manual approval)
```

## The four workflows

### `pr-validate.yml`

Triggered on PR open / synchronize / reopen against `develop`, `release/*`, or `main`.

```yaml
on:
  pull_request:
    branches: [develop, release/*, main]

permissions:
  id-token: write    # OIDC to Databricks
  contents: read
  pull-requests: write  # to post the preview URL comment
```

Steps (per service that changed):

1. **Detect changed services** (path-scoped):
   ```yaml
   - uses: dorny/paths-filter@v3
     id: filter
     with:
       filters: |
         patient: 'services/patient/**'
         provider: 'services/provider/**'
         # ...etc
         hc-portal: 'frontend/hc-portal/**'
         infra: ['databricks.yml', 'resources/**']
   ```
   Then matrix over `${{ fromJSON('["' + join(steps.filter.outputs.changes, '","') + '"]') }}`.

2. **Lint + unit tests** (`apx dev check`, `pytest -m 'not integration'`).

3. **Idempotently provision the Lakebase feature branch** for the service:
   ```bash
   SLUG=$(./scripts/sanitize-branch-slug.sh "$GITHUB_HEAD_REF")
   ./scripts/lakebase-branch-up.sh "$SVC" "$SLUG"
   ```
   See [`hc-lakebase-branching`](../hc-lakebase-branching/SKILL.md) for what the script does.

4. **Run migrations against the feature branch** so the DB schema matches what the PR's code expects.
   ```bash
   cd services/$SVC
   uv run alembic upgrade head
   ```

5. **Deploy preview app** with the per-PR overrides — see `hc-dab-deployment` "Per-PR preview deployment" for the full rationale:
   ```bash
   databricks bundle deploy -t dev \
     --var "app_name_suffix=-feat-$SLUG" \
     --var "lakebase_branch=feat-$SLUG"
   ```
   The suffix prefixes every app name (`patient-dev-feat-<slug>`) AND the bundle's dev `root_path`, so per-PR previews are isolated on disk and in app names. `lakebase_branch` rebinds every postgres resource to the per-feature branch — `pr-validate.yml` provisions branches for all six services up-front so untouched services' postgres references still resolve.

6. **Run integration + contract tests** against the preview app URL.

7. **(For frontend changes only)** Run Playwright smoke against the deployed `hc-portal-dev-feat-<slug>`.

8. **Post results as a PR comment**: preview URLs, test results, link to logs.

On PR close / merge: a `pr-cleanup.yml` workflow runs `databricks bundle destroy` for the preview resources and the `lakebase-branch-down.sh` script.

### `deploy-dev.yml`

```yaml
on:
  push:
    branches: [develop]
```

Steps:

1. Run all unit tests across services.
2. For each service, run `alembic upgrade head` against `<svc>-dev/production`.
3. `databricks bundle deploy -t dev`.
4. Smoke-test all deployed apps' `/healthz` endpoints.

### `deploy-test.yml`

```yaml
on:
  push:
    branches: [release/*, main]
```

Steps:

1. Run all unit tests + integration tests (against deployed dev environment, since test isn't yet up).
2. For each service, run `alembic upgrade head` against `<svc>-test/production`.
3. `databricks bundle deploy -t test`.
4. Run smoke + E2E tests against test workspace.

### `deploy-prod.yml`

```yaml
on:
  push:
    tags: ['v*']

jobs:
  deploy:
    environment:
      name: prod
      url: https://hc-portal-prod.<workspace>.databricksapps.com
    # ↑ this `environment:` triggers GitHub's manual approval gate
    runs-on: ubuntu-latest
    steps:
      - ...
```

Steps:

1. Verify the tag is on `main`.
2. Wait for manual approval (configured per `prod` environment in GitHub Settings).
3. Run all migrations against `<svc>-prod/production`.
4. `databricks bundle deploy -t prod`.
5. Smoke-test prod URLs.
6. On failure, the rollback is "redeploy the previous tag":
   ```bash
   git checkout <previous-tag>
   databricks bundle deploy -t prod
   ```
   Documented in `docs/runbooks/prod-rollback.md` (deferred).

## Authentication: per-env secrets + M2M client-secret

GitHub Actions authenticates to Databricks via service-principal client-secret M2M, with the secret scoped to a GitHub *environment* (not a repo secret). The env-scoped layout is what's actually wired today; the OIDC migration is a future follow-up.

Setup (one-time, see Phase 0 of `ROADMAP.md`):

1. **One service principal per workspace.** In each Databricks workspace (dev/test/prod), create an account-level service principal and grant it the workspace permissions the bundle needs (workspace admin is fine for a reference repo; tighten in production usage). Generate a client-secret pair for each.

2. **Repo variables — the workspace hosts.** In GitHub repo Settings → Secrets and variables → Actions → **Variables**:
   - `DATABRICKS_HOST_DEV`
   - `DATABRICKS_HOST_TEST`
   - `DATABRICKS_HOST_PROD`

   Hosts are not secret; they go in `vars`. They're repo-scoped because they're identical across the workflows that need them.

3. **Environment secrets — the credentials.** Create three GitHub environments named `dev`, `test`, `prod` (Settings → Environments). For each, add two **environment secrets** (NOT repo secrets):
   - `DATABRICKS_CLIENT_ID`
   - `DATABRICKS_CLIENT_SECRET`

   Same names across all three environments — the GitHub environment binding selects which secret values flow into the job. This lets every workflow reference `secrets.DATABRICKS_CLIENT_ID` regardless of environment, and makes copy-paste between deploy-dev/test/prod safe.

4. **Bind every Databricks-touching job to its environment.** This is what makes GitHub inject the right env-scoped secrets:
   ```yaml
   jobs:
     deploy:
       runs-on: ubuntu-latest
       environment:
         name: dev    # or test, or prod — picks the right secrets
   ```
   For `prod`, `environment.name: prod` *also* triggers the manual-approval gate configured on that environment.

5. **Write the named profile in each workflow.** The bundle's `workspace.profile: hc-<env>` reference is resolved by the CLI against `~/.databrickscfg`, so we have to materialize the named section explicitly:
   ```yaml
   - uses: databricks/setup-cli@main
     with:
       version: "0.295.0"

   - name: Write hc-dev profile to ~/.databrickscfg
     env:
       DATABRICKS_HOST: ${{ vars.DATABRICKS_HOST_DEV }}
       DATABRICKS_CLIENT_ID: ${{ secrets.DATABRICKS_CLIENT_ID }}
       DATABRICKS_CLIENT_SECRET: ${{ secrets.DATABRICKS_CLIENT_SECRET }}
     run: |
       mkdir -p "$HOME"
       cat > "$HOME/.databrickscfg" <<EOF
       [hc-dev]
       host = ${DATABRICKS_HOST}
       client_id = ${DATABRICKS_CLIENT_ID}
       client_secret = ${DATABRICKS_CLIENT_SECRET}
       EOF
       chmod 600 "$HOME/.databrickscfg"
       databricks current-user me -p hc-dev
   ```
   `chmod 600` is paranoia — the runner is ephemeral, but the cfg file holds a long-lived secret and someone reading the artifact archive shouldn't be able to grep it.

6. **Migration to OIDC (deferred).** When OIDC trust can be configured on each workspace's account: bind a federation policy on each workspace's service principal allowing GitHub-issued tokens from `repo:<org>/<repo>`, then in the workflows replace `client_secret = ${DATABRICKS_CLIENT_SECRET}` with `auth_type = github-oidc`, add `permissions: id-token: write`, and drop `DATABRICKS_CLIENT_SECRET` from the three environment secrets. The `dab-ci-auth` memory note tracks the rollback story.

## Manual procedures

### Cut a release

```bash
git switch develop && git pull
git switch -c release/v0.4.0
# bump versions in services/*/pyproject.toml and frontend/hc-portal/pyproject.toml
# update CHANGELOG.md
git commit -am "chore(release): v0.4.0"
git push -u origin release/v0.4.0
gh pr create --base main --title "release: v0.4.0" --body-file .github/release-template.md
```

When the PR merges to `main`, `deploy-test.yml` runs. After validation in test:

```bash
git switch main && git pull
git tag -a v0.4.0 -m "release v0.4.0"
git push origin v0.4.0
```

This triggers `deploy-prod.yml` with manual approval.

After prod deploy, merge `main` back to `develop`:

```bash
gh pr create --base develop --head main --title "merge main to develop after v0.4.0" --body "Sync after prod release."
```

### Hotfix

```bash
git switch main && git pull
git switch -c hotfix/HC-456-fix-billing-rounding
# fix it
git commit -am "fix(billing): correct rounding on partial payments"
git push -u origin hotfix/HC-456-fix-billing-rounding
gh pr create --base main --title "hotfix: HC-456 billing rounding"
```

PR merge to `main` → `deploy-test.yml`. After validation, tag and `deploy-prod.yml`:

```bash
git switch main && git pull
git tag -a v0.4.1 -m "hotfix HC-456"
git push origin v0.4.1
```

Then merge `main` → `develop`.

### What if a hotfix can't wait for test validation?

It still has to. Skipping test isn't a procedure — it's an outage waiting to happen. If the test deploy is broken, the hotfix is to fix the test deploy first. Document the policy in `docs/runbooks/hotfix.md` (deferred).

## One-time GitHub setup (do once when the repo is created)

| Setting | Value |
|---|---|
| Branch protection on `main` | Require PR + 1 approval, require status checks (`pr-validate / *`), require linear history, do not allow force-push |
| Branch protection on `develop` | Require PR + 1 approval, require status checks |
| Environments | Create `prod` env with required reviewers (you or your team) and `wait-timer: 0` |
| Repo settings | Disallow merge commits on `develop` (squash-and-merge only); allow merge commits on `main` (preserves release/hotfix shape) |
| Default branch | `main` |
| Allowed Actions | Allow github.com/databricks/* and trusted third parties (paths-filter, etc.) |

## Checklist before merging changes to `.github/workflows/`

- [ ] All workflow files pass `actionlint`
- [ ] Every Databricks-touching job has `environment: dev|test|prod` so secrets resolve, not just repo-wide
- [ ] Secrets used: `secrets.DATABRICKS_CLIENT_ID` + `secrets.DATABRICKS_CLIENT_SECRET` (env-scoped). Hosts via `vars.DATABRICKS_HOST_<ENV>` (repo-scoped)
- [ ] `~/.databrickscfg` writes use the `client_secret = …` shape (current) — track OIDC migration in `dab-ci-auth` memory
- [ ] `pr-validate.yml` is path-scoped (changes to `services/lab/` don't spin up `patient`'s preview)
- [ ] Cleanup workflow handles all PR close paths (merged AND closed-without-merge)
- [ ] Deploy workflows include `alembic upgrade head` BEFORE `bundle deploy`, not after

## Verification

```bash
# Local: lint workflows
brew install actionlint
actionlint .github/workflows/*.yml

# After pushing a feature branch: PR should produce
# 1. A comment with preview URLs
# 2. A green pr-validate / matrix=<svc> check
# 3. A new Lakebase branch visible in:
databricks postgres list-branches "projects/<svc>-dev" -p hc-dev | grep "feat-"

# After closing/merging: cleanup workflow should leave nothing behind:
databricks postgres list-branches "projects/<svc>-dev" -p hc-dev | grep "feat-$SLUG"  # → no match
databricks apps list -p hc-dev | grep "<svc>-dev-feat-$SLUG"                           # → no match
```
