<!--
PR description template for `release/v*` -> `main` PRs. Used by:

  gh pr create --base main --title "release: v0.4.0" --body-file .github/release-template.md

After this PR merges to `main`, deploy-test.yml deploys the test workspace.
After validation in test, tag the merge commit with `vX.Y.Z` to trigger
deploy-prod.yml (which waits for manual approval).

Do NOT use this template for hotfix PRs — those are direct `hotfix/*` -> `main`
PRs without a release branch.
-->

# Release vX.Y.Z

## What's in this release

<!--
List the user-visible changes that landed since the previous release tag.
Generate this by running:

  git log <previous-tag>..HEAD --pretty=format:'- %s' --no-merges

then trim to the meaningful commits.
-->

-

## Migrations

<!--
Any new Alembic migrations? List them here, per service. The deploy workflows
run `alembic upgrade head` before `bundle deploy`, so the order is:

  test:  develop -> main merge -> alembic upgrade head (test) -> bundle deploy test
  prod:  tag -> manual approval -> alembic upgrade head (prod) -> bundle deploy prod

Migrations should be backward-compatible (additive) so the old app version
continues to work for the brief window between migration and deploy.
-->

- [ ] No schema changes
- [ ] Migrations listed below
  - `services/<svc>/migrations/versions/<rev>_<name>.py` — <one-sentence summary>

## Cross-service contract changes

<!--
A change to a service's API shape that the BFF consumes is a contract change.
Bump the API version in the affected service's `pyproject.toml` if so.
-->

- [ ] No
- [ ] Yes — describe and confirm BFF clients updated

## Verification plan

After this PR merges to `main`:

- [ ] `deploy-test.yml` succeeds end-to-end
- [ ] Smoke `https://hc-portal-test.databricksapps.com/api/healthz` returns 200
- [ ] BFF GraphQL query on test returns valid data for a known seeded patient
- [ ] No errors in test workspace's app logs for 30 minutes after deploy

Then tag and let `deploy-prod.yml` take over:

```bash
git switch main && git pull
git tag -a vX.Y.Z -m "release vX.Y.Z"
git push origin vX.Y.Z
```

After prod deploys, merge `main` back to `develop`:

```bash
gh pr create --base develop --head main --title "merge main to develop after vX.Y.Z"
```
