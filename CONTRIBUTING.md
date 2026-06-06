# Contributing

Thanks for opening this. This repo is a *reference architecture* — the conventions matter as much as the code, because they're the thing other teams will copy.

The two questions to ask before you start:

1. **Which service does this change belong to?** If you can't answer, the change probably belongs in the BFF (`frontend/hc-portal/`) or doesn't belong here at all.
2. **Does it require a schema change?** If yes, your feature branch will need a Lakebase branch — set it up early.

---

## Branching model (GitFlow)

```
main         ─●───────────●──────────●──────●───────  (only release/hotfix merges, tags = prod)
              ▲           ▲          ▲      ▲
              │           │          │      │
release/v0.2  │      ●────┘          │      │
              │      │               │      │
develop  ─●──●┴──●───●──●──●─●──●──●─┴──●──●┴──   (integration → dev workspace)
          ▲      ▲         ▲     ▲        ▲
          │      │         │     │        │
          feature/HC-12... │  feature/HC-15...
                           hotfix/HC-99-...
```

| Branch | Branched from | Merges into | Triggers deploy to |
|---|---|---|---|
| `feature/<TICKET>-<slug>` | `develop` | `develop` | preview app + Lakebase branch in **dev** |
| `release/<version>` | `develop` | `main` *and* `develop` | **test** |
| `main` HEAD (no tag) | — | — | **test** |
| Tag `v*` on `main` | — | — | **prod** (after manual approval) |
| `hotfix/<TICKET>-<slug>` | `main` | `main` *and* `develop` | **test** then **prod** |

### Naming

- Lowercase, dash-separated, ticket prefix.
- `feature/HC-123-add-allergies` ✅
- `feature/Add Allergies` ❌
- `bugfix/...` is just `feature/...` — no separate branch type.

### Commit style

Conventional Commits. The `<scope>` is the service name (or `bff`, `infra`, `docs`).

```
feat(patient): add allergies endpoint
fix(lab): correct flag for critical_low results
chore(infra): bump databricks CLI to 0.301.0
```

---

## Per-feature workflow

Concrete steps. Most of this is automated by the skills under `.claude/skills/` — open the repo in Claude Code and ask it to "start work on HC-123".

### 1. Branch the code

```bash
git switch develop && git pull
git switch -c feature/HC-123-add-allergies
```

### 2. Branch the database (per service you're changing)

```bash
SLUG=$(./scripts/sanitize-branch-slug.sh "$(git branch --show-current)")
SERVICE=patient   # the service you're modifying

databricks postgres create-branch projects/$SERVICE-dev "feat-$SLUG" \
  --json '{"spec":{"source_branch":"projects/'$SERVICE'-dev/branches/production"}}' \
  -p hc-dev

databricks postgres create-endpoint "projects/$SERVICE-dev/branches/feat-$SLUG" read-write \
  --json '{"spec":{"endpoint_type":"ENDPOINT_TYPE_READ_WRITE",
                   "autoscaling_limit_min_cu":0.5,
                   "autoscaling_limit_max_cu":2.0}}' \
  -p hc-dev
```

Or just ask Claude Code: *"spin up a Lakebase branch for this feature in patient-svc"* (`hc-lakebase-branching` skill handles it).

### 3. Wire your local app to the branch endpoint

```bash
cd services/patient
cp .env.example .env
# edit .env — set ENDPOINT_NAME to projects/patient-dev/branches/feat-<slug>/endpoints/<name>
apx dev start
```

### 4. Code, test, push

- Add an Alembic migration if you're changing schema.
- Run `apx dev check` and `pytest` locally.
- Push the branch.

### 5. Open a PR against `develop`

The `pr-validate.yml` workflow:

- Runs lint + unit tests for every changed service.
- Looks up your existing feature branch in Lakebase (creates it if missing — idempotent for contributors who skipped step 2).
- Deploys preview apps `<svc>-dev-feat-<slug>` wired to that branch.
- Runs integration tests + contract tests against the previews.
- Posts the preview URL(s) as a PR comment.

### 6. Iterate

Push more commits → the same Lakebase branch and preview app are reused, so your migrations and seed data persist across pushes.

### 7. Merge

PR merge or close → the workflow tears down the preview apps, endpoints, and Lakebase branches automatically.

---

## Independence rules (monorepo discipline)

Even though everything lives in one repo, services are independent. The five rules:

1. **No backend-to-backend HTTP calls.** If `lab-svc` needs patient name, the BFF resolves it on read. Service code never imports another service's client.
2. **No shared Python library between services.** Each service is its own uv workspace member with its own `pyproject.toml`. Shared utilities (e.g. `OAuthConnection`) are *copied* into each service from the `hc-obo-auth` skill, not imported. This is deliberate — it keeps the boundary visible.
3. **No cross-DB FKs.** Cross-service references are bare UUID columns.
4. **One service per PR ideally.** If a feature legitimately spans multiple services + the BFF, that's fine, but call it out in the PR description.
5. **Service ownership in `CODEOWNERS`.** A change to `services/patient/` requires a `@patient-team` review.

CI enforces some of these:

- `services/<svc>` paths only trigger that service's preview app.
- A linter rejects imports from `services.<other-svc>` inside `services/<svc>`.
- A linter rejects FK constraints whose referenced table doesn't exist in the migration scope (catches accidental cross-DB FKs).

---

## Pull request checklist

Copy this into the PR description:

```markdown
## What
<one sentence>

## Why
<one paragraph>

## Affected services
- [ ] patient
- [ ] provider
- [ ] appointment
- [ ] lab
- [ ] prescription
- [ ] billing
- [ ] hc-portal (BFF + frontend)
- [ ] infra (DAB / GH Actions)

## Schema changes
- [ ] No
- [ ] Yes — Alembic migration in services/<svc>/migrations/

## Cross-service contract changes
- [ ] No
- [ ] Yes — describe and bump API version

## Tested
- [ ] Locally against feature-branch DB
- [ ] Preview app from PR CI (link)
```

---

## Releases

Cutting a release:

```bash
git switch develop && git pull
git switch -c release/v0.4.0
# bump versions in pyproject.toml files
git commit -am "chore(release): v0.4.0"
git push -u origin release/v0.4.0
gh pr create --base main --title "release: v0.4.0"
```

Merging to `main` deploys to **test**. After validation:

```bash
git switch main && git pull
git tag v0.4.0
git push origin v0.4.0
```

Tag push triggers `deploy-prod.yml`, which waits for manual approval in the `prod` GitHub environment.

Merge `main` back into `develop` to keep them in sync (`gh pr create --base develop --head main`).

---

## Hotfixes

```bash
git switch main && git pull
git switch -c hotfix/HC-456-fix-billing-rounding
# fix it
git commit -am "fix(billing): correct rounding on partial payments"
gh pr create --base main
```

After merge to `main`, tag and deploy to prod the same way as a release. Then merge `main` → `develop`.

---

## Running CI locally (`scripts/ci-local.sh`)

The GitHub Actions workflows under `.github/workflows/` are the source of truth for the deploy pipeline. GH-hosted runners can't reach the dev workspace today (FE-VM's managed IP allowlist blocks them — see the `github-runner-ip-acl` memory note); use `scripts/ci-local.sh` to run the same logical pipelines from your workstation, where your IP is already allowlisted.

**The script mirrors the workflow files step-for-step. The intended division of labor is:**

- **Trunk deploys (`deploy dev`/`deploy test`/`deploy prod`) belong to a CI service principal.** Developers don't normally run these from their machines — once the IP-ACL workaround lands, the workflows do this in CI. The `ci-local.sh deploy <env>` subcommand exists for the bootstrap path (first-ever deploy of an env, recovery from incidents) and as the manual fallback while CI is blocked.
- **Per-PR previews (`pr-validate` / `pr-cleanup`) belong to developers.** Run from your machine, against your feature branch's Lakebase feature branch. Even when CI unblocks, this stays a dev-machine workflow.

The two are intentionally isolated in the bundle: previews override `app_name_suffix=-<slug>` + `lakebase_branch=<slug>` so they live alongside the trunk-dev deploy with different app names and different feature-branch DBs. Lakebase projects (the shared infra) are managed entirely outside the bundle via `scripts/lakebase-project-{up,down}.sh` so a `bundle destroy` of a preview can't touch them.

```bash
# Day-to-day: fast feedback during dev — lint + tests + bundle-validate, no deploy.
./scripts/ci-local.sh pr-validate --no-deploy

# Before opening a PR (or after a meaningful push): full preview deploy.
# Provisions 6 Lakebase feature branches, alembic on changed services,
# deploys preview apps suffixed with your branch slug, smoke-tests 7 apps.
./scripts/ci-local.sh pr-validate

# Tear down the preview when you're done iterating.
./scripts/ci-local.sh pr-cleanup

# Bootstrap a fresh env, or rebuild after wipe (CI's job, normally).
# `--skip-tests` is fine when you've just verified the same SHA locally.
./scripts/ci-local.sh deploy dev [--skip-tests]
./scripts/ci-local.sh deploy test
./scripts/ci-local.sh deploy prod        # CI-only in normal operation

# GC orphaned Lakebase branches whose PR is closed (the cron workflow's manual equivalent).
./scripts/ci-local.sh nightly-cleanup
```

`pr-validate` and `pr-cleanup` use `hc-dev`. `deploy` picks `hc-{dev,test,prod}` based on the target. All subcommands fail fast if the corresponding profile is missing or invalid in `~/.databrickscfg` — run `databricks auth login -p hc-<env>` if so.

**Footgun: don't run `deploy dev` and `pr-validate` back-to-back on the same machine.** DAB caches terraform state locally at `.databricks/bundle/<target>/` keyed only by target name, so two `-t dev` runs (trunk + preview) clobber each other's cache. In CI this never happens (each runner is ephemeral). On a single dev machine, pick one or the other, or `rm -rf .databricks/bundle/dev/` between them.

---

## When to bump the API version

Each service exposes `/api/v1/...`. Bump to `v2`:

- When a request or response schema changes in a way the BFF can't handle transparently.
- Never as a "we're refactoring" — refactors that don't change the wire format don't need a version bump.

The BFF must continue calling `v1` until it's been updated to call `v2`. Both versions ship together for one release cycle, then `v1` is removed.

---

## Tools and skills

| Need | Tool / skill |
|---|---|
| Scaffold a new service | `.claude/skills/hc-microservice-scaffold/` |
| Branch / unbranch DB | `.claude/skills/hc-lakebase-branching/` |
| Add an authenticated route | `.claude/skills/hc-obo-auth/` |
| Deploy to dev/test/prod | `.claude/skills/hc-dab-deployment/` |
| Add a BFF aggregation route | `.claude/skills/hc-bff-pattern/` |
| Cut a release / hotfix | `.claude/skills/hc-gitflow-cicd/` |

Open the repo in Claude Code; the skills are auto-discovered.

---

## What does *not* belong in this repo

- Real PHI. Synthetic only.
- Long-lived secrets (PATs, DB passwords). Auth is OBO + OIDC; secrets in CI are short-lived OIDC tokens.
- Per-environment hardcoded values. Use DAB variables and `${bundle.target}` instead.
- "Quick fixes" that bypass the CODEOWNERS for someone else's service. If you need a change in another service, open a separate PR for it.
