# Instructions — adopting agent docs in a Meavo repo

Use this guide when adding or refreshing instruction files in any **meavo-booths** repository.

## Who does what

| Role | Action |
|------|--------|
| **Human (repo owner)** | Review docs and give specific production permission when a release is intended |
| **AI agent** | Follow [BOOTSTRAP.md](BOOTSTRAP.md), fill docs, and open a feature PR explicitly into `staging` |
| **Org maintainer** | Keep templates in `meavo-agent-templates` generic and up to date |

## Step 1 — Bootstrap file skeleton

From the **target repo root**:

```bash
# Clone the complete pack; the script requires the adjacent template files.
git clone https://github.com/meavo-booths/meavo-agent-templates.git /tmp/meavo-agent-templates
/tmp/meavo-agent-templates/scripts/bootstrap-agent-docs.sh .
```

The script copies:

- `AGENTS.md`, `CLAUDE.md`, and `CONTRIBUTING.md` with mandatory managed release blocks
- `RELEASE_POLICY.md`, release-policy verification tooling/workflow, and `.cursor/rules/release-process.mdc`
- `.cursorignore`
- `.cursor/rules/core.mdc`, `domain.mdc`, `api.mdc`, `ui.mdc`, `security.mdc`
- `docs/architecture.md`, `domain.md`, `data-model.md` (skip `data-model.md` if no database)
- `--with-legacy` adds `.cursor/rules/legacy.mdc` for repos with a read-only legacy subtree

Existing customized agent docs are preserved unless `--force` is used. Mandatory release-policy files and managed blocks are refreshed separately; do not remove or mark them N/A. For an existing repo that only needs a policy refresh, run:

```bash
python3 /tmp/meavo-agent-templates/scripts/sync-release-policy.py .
python3 /tmp/meavo-agent-templates/scripts/sync-release-policy.py . --check
```

Work on `feat/`, `fix/`, or `chore/` from `staging` and set the PR base explicitly to `staging`. If staging is missing, report the setup gap rather than using main. See [RELEASE_PROCESS.md](RELEASE_PROCESS.md) before release or deployment work.

## Step 2 — Read the org standards

Read [STANDARDS.md](STANDARDS.md) before filling anything. It defines the unified database, UI (mobile + desktop), and security conventions shared across all meavo-booths repos. Copy applicable rules into the target repo's docs verbatim; document deviations explicitly.

## Step 3 — Discover the repo (before writing prose)

Agents and humans should read the codebase first. Minimum discovery:

| Question | Where to look |
|----------|----------------|
| Stack & runtime | `package.json`, `pyproject.toml`, `go.mod`, `Dockerfile`, `vercel.json` |
| Folder layout | `src/`, `app/`, `lib/`, `packages/` |
| Entry points | `README.md`, main `page.tsx` / `index.ts` |
| Auth | `auth.ts`, `middleware.ts`, env vars in `.env.example` |
| Database | `prisma`, `@meavo/db`, `drizzle`, or none |
| External integrations | `integrations/`, `api/`, cron routes |
| Tests & lint | `package.json` scripts, `eslint.config.*`, `vitest.config.*` |
| Legacy / parity | `legacy-*`, comments referencing old systems |

Take notes — you'll paste findings into template placeholders.

## Step 4 — Fill templates (priority order)

Work top-down. Stop when a section doesn't apply and mark it `N/A` or delete it. Pull org constants (stack, DB rules, UI system, security patterns) from [STANDARDS.md](STANDARDS.md); pull repo specifics from your Step 3 discovery. See [examples/AGENTS.example.md](examples/AGENTS.example.md) for the quality bar.

### 4.1 `AGENTS.md` (required)

Keep under **~150 lines**. Must include:

- The managed release-safety block at the top, pointing to root `RELEASE_POLICY.md`
- One-sentence product description
- Stack bullets
- **Task → file** table (most valuable section)
- 5–10 **Do NOT** rules
- Dev commands (`install`, `dev`, `test`, `lint`, `build`)
- Links to `docs/` and `.cursor/rules/`

### 4.2 `.cursor/rules/core.mdc` and release policy (required)

`alwaysApply: true` — stack, layout table, hard guardrails, data-flow one-liner. Keep the release-safety pointer. `.cursor/rules/release-process.mdc` is also always applied and must match its canonical template; it has no repo-specific placeholders. Root `RELEASE_POLICY.md` applies to every repo, including pure libraries and documentation.

Migrate any legacy root `.cursorrules` content here, then **delete or slim** `.cursorrules` to avoid duplicate/conflicting rules. Point `.cursorrules` at `.cursor/rules/` with one line if your team still expects the file.

### 4.3 `.cursor/rules/security.mdc` (required for apps; delete for pure libraries)

`alwaysApply: true` — org security standard (STANDARDS.md §4) with this repo's auth gate and tool-card ID filled in.

### 4.4 `.cursor/rules/ui.mdc` (required for apps with UI; delete otherwise)

Glob-scoped to `src/app/**` and `src/components/**` — org UI standard (STANDARDS.md §5): in-house kit, brand palette, mobile-first responsive rules.

### 4.5 `.cursor/rules/domain.mdc` (if `lib/domain/` or equivalent exists)

Glob-scoped rules for business logic: thin handlers, mutation patterns, side effects (sheet sync, webhooks, etc.).

### 4.6 `.cursor/rules/api.mdc` (if HTTP API / Server Actions / routes exist)

Glob-scoped: auth on every route, cron secret, validation, error shape.

### 4.7 `docs/architecture.md` (recommended for non-trivial apps)

Stack, sibling repos, folder map, data flow diagram, cron/job list, env vars overview.

### 4.8 `docs/domain.md` (recommended when business rules exist)

Glossary, roles/permissions, status values, mutation map, legacy port index.

### 4.9 `docs/data-model.md` (database repos only)

Schema ownership (usually **meavo-db**), entity diagram, field notes agents can't infer.

### 4.10 `CONTRIBUTING.md` (recommended)

Branch naming, PR checklist, test expectations, cross-repo bump process. Preserve the mandatory production-permission block; normal PRs target staging.

### 4.11 `.cursorignore` (recommended)

Tune for the repo — exclude build dirs, `node_modules`, generated code, large fixtures.

## Step 5 — Wire up entry points

Update the target repo's `README.md` documentation table:

```markdown
| [AGENTS.md](AGENTS.md) | Quick orientation for AI coding agents |
| [.cursor/rules/](.cursor/rules/) | Always-on Cursor rules |
| [docs/architecture.md](docs/architecture.md) | Stack and data flow |
```

Remove stale references (e.g. pointing at `.mdc` files that don't exist).

## Step 6 — Verify

Run the automated checker from the target repo root, then the manual checklist:

```bash
/tmp/meavo-agent-templates/scripts/verify-agent-docs.sh .
```

Then run through [CHECKLIST.md](CHECKLIST.md). Open a PR explicitly targeting `staging`, titled e.g. `docs: add agent instruction files`. Production is a separate human-authorized action.

## Step 7 — Keep docs alive

Update agent docs in the **same PR** when you:

- Add a new top-level area (`src/lib/integrations/foo/`)
- Change auth, schema ownership, or deployment constraints
- Introduce a new persona, status, or cron job

Stale `AGENTS.md` is worse than none — agents will trust wrong paths.

## Optional: legacy / sub-project rules

If the repo contains a **read-only legacy subtree** (e.g. `legacy-gas/`):

- Add `legacy-gas/.cursorrules` or `.cursor/rules/legacy.mdc` with a glob for that path only
- State clearly: **not the live deployment target**

## Optional: monorepo packages

For repos with `packages/*`:

- One `AGENTS.md` at repo root with a package index table
- Optional per-package `packages/foo/AGENTS.md` for package-specific tasks (keep short)
- Cursor rules: `core.mdc` at root; add `packages/foo/.cursor/rules/` only when conventions differ

## Getting help from an agent

Use this prompt in the target repo:

```
Read meavo-booths/meavo-agent-templates BOOTSTRAP.md and STANDARDS.md, then bootstrap agent docs for THIS repo.
Discover stack and layout from the codebase. Fill all <!-- FILL: --> placeholders.
Apply org-wide rules from STANDARDS.md; mark any deviations explicitly.
Keep the managed release-policy files and blocks intact. Do not copy repo-specific content
from other Meavo repos. Open a feature PR explicitly into staging when done; no main release.
Run scripts/verify-agent-docs.sh and CHECKLIST.md to verify.
```
