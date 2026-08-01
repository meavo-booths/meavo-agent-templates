# Meavo branching & release process

How code gets from a laptop to `meavo.app`. Applies to **every meavo-booths repo**. Nothing reaches
production except by merging a pull request.

> **The one-line version:** branch off `staging`, open a PR into `staging`, check it on the staging
> URL, then open a PR from `staging` into `main` to release.

## 1. Branches

| Branch | Meaning | Deploys to | Database |
|--------|---------|-----------|----------|
| `main` | Production. Only ever updated by merging a release PR. | the live domain, e.g. `sales.meavo.app` | production |
| `staging` | Shared integration branch. Long-lived, never deleted. | `https://<project>-git-staging-meavo-gateway.vercel.app` | `staging` Neon branch |
| `feat/…` `fix/…` `chore/…` | Your work. Short-lived, deleted on merge. | a preview URL per branch | `staging` Neon branch |

Both `main` and `staging` are protected. Direct pushes are **rejected by the server** — you cannot
force it, and neither can an AI agent. A PR plus a passing `Typecheck` check is required. Force-pushes
and branch deletion are blocked.

Reviews are *not* required, so you can merge your own PR once CI is green. The gate is CI, not a
colleague.

## 2. Daily workflow

```bash
# 1. Start from the latest staging — NOT from main
git fetch origin
git checkout -b feat/add-invoice-filter origin/staging

# 2. Work, commit, push
git commit -m "Add invoice filter"
git push -u origin feat/add-invoice-filter

# 3. Open a PR into staging
gh pr create --base staging
```

CI runs on the PR and Vercel builds a preview. When it's green, **squash merge** into `staging`. Your
branch is deleted automatically.

Then verify on the shared staging URL for that app:

```
https://<project>-git-staging-meavo-gateway.vercel.app
```

## 3. Releasing

```bash
gh pr create --base main --head staging --title "Release: <what's in it>"
```

Merge that with a **merge commit**. Merging to `main` is what deploys production.

> **Never squash `staging` into `main`.** Squashing rewrites the commits, so the two branches diverge
> permanently and every later release PR shows phantom differences.

| Merging into | Method | Why |
|--------------|--------|-----|
| `staging` | Squash | Keeps integration history to one commit per change |
| `main` | Merge commit | Preserves the commits so `staging` and `main` stay comparable |

## 4. What CI checks

`.github/workflows/ci.yml` runs on every PR and on pushes to `main` and `staging`:

- **Typecheck** — `tsc --noEmit`. Blocking; this is the required status check.
- **Tests** — where the repo has them (currently `zeron-material-checker`). Blocking.
- **Lint** — advisory only, because a few repos have no ESLint config yet and bare `next lint`
  prompts interactively without one, which would hang the runner.

Node is pinned to **24** to match what Vercel builds with. If you change that, change both.

`meavo-db` runs `prisma validate` instead of a typecheck.

## 5. Environments and data

Every app shares one Neon Postgres database. It has two branches:

| Where you are | `DATABASE_URL` resolves to |
|---------------|---------------------------|
| `main` / production deployment | **production data** |
| `staging` deployment | `staging` Neon branch |
| any `feat/` preview deployment | `staging` Neon branch |
| local `vercel env pull` (development) | production in some repos — check before you write |

So a preview deployment cannot touch production data. The `staging` branch was copied from production,
so it has realistic data and the full schema, including other apps' tables.

Three caveats:

- **Sign-in on a `feat/` preview may not work.** `AUTH_URL`, `GATEWAY_URL` and `HOLS_SYNC_URL` are
  scoped to the `staging` branch only, because pointing OAuth redirects at a different host breaks the
  callback. Use the staging URL for anything involving auth.
- **Blob storage is shared with production.** Files you upload from staging land in the real bucket.
- **Staging URLs are reachable by anyone who knows them.** Vercel Deployment Protection is switched
  off on every app project, so the only gate is the app's own Google sign-in plus tool-card access —
  the same gate production uses. Don't treat a staging URL as private, and remember the `staging`
  database is a copy of real production data.

## 6. Schema changes

Schema lives only in [`meavo-db`](https://github.com/meavo-booths/meavo-db) — see STANDARDS.md §3.
Each app pins `@meavo/db` by git tag, so apps run different schema versions at the same time.

**Therefore schema changes must be backward compatible.** Add columns and tables; do not rename or
drop them in the same release. An older app still reading the old column will break in production the
moment you drop it. Sequence: add → migrate every app to the new tag → remove in a later release.

## 7. Gotchas worth knowing

- **Changing an environment variable does nothing until you redeploy.** Vercel resolves variables when
  a deployment is *built*, so editing one leaves running deployments untouched. Redeploy the branch
  afterwards or the change silently has no effect.
- **Never run `vercel --prod`.** Production deploys happen only by merging into `main`; a manual CLI
  deploy produces a duplicate build that doesn't match any branch.
- **`vercel redeploy` needs `--scope meavo-gateway`.** Without it the CLI reports "Deployment belongs
  to a different team".
- Preview and production `DATABASE_URL` are **separate variable records** in Vercel. Never widen the
  production record back to the `preview` scope — that is exactly what used to let feature previews
  write to production.
- **Auth variables must be scoped to Preview as well as Production.** `AUTH_SECRET`,
  `AUTH_GOOGLE_ID` and `AUTH_GOOGLE_SECRET` are the exception to the rule above: unlike
  `DATABASE_URL`, staging deliberately shares production's values, because the Google OAuth client
  already whitelists the staging redirect URIs. If one of them is Production-only, the preview build
  starts Auth.js with no secret, every `/api/auth/*` route returns 500, and `/` and `/login` redirect
  at each other until the browser gives up with `ERR_TOO_MANY_REDIRECTS`. Check with:

  ```bash
  curl -s https://<project>-git-staging-meavo-gateway.vercel.app/api/auth/providers
  # healthy  -> {"google":{...}}
  # broken   -> {"message":"There was a problem with the server configuration..."}
  ```

## 8. Coverage

All 13 code repos have CI, a `staging` branch, and protection on both `main` and `staging`:

`meavo-gateway` · `hols` · `assembly` · `sales` · `meavo-mrp` · `Meavo-Factory` · `meavo-tasks` ·
`meavo-tickets` · `meavo-rp` · `meavo-clock` · `meavo-db` · `meavo-navigation` ·
`zeron-material-checker`

`meavo-db` and `meavo-navigation` stay **public** because apps consume them as anonymous git
dependencies; the app repos are private.
