# BOOTSTRAP.md — agent playbook

**Audience:** Cursor / Cloud agents bootstrapping instruction files in a meavo-booths repo.

**Input:** Target repo checkout (the app you're working in, not `meavo-agent-templates`).

**Output:** Filled agent docs, mandatory `RELEASE_POLICY.md` and managed entry-point blocks, policy verification tooling, and updated README links — as a feature PR explicitly targeting `staging`.

---

## Rules

0. **Release safety is mandatory** — read [RELEASE_PROCESS.md](RELEASE_PROCESS.md). Work on feature branches and through staging PRs. After staging integration and verification, present the release PR/head, scope and checks, then stop and ask for one human approval before main. The PR author may approve in chat or a human-authored PR comment; a clear “yes” to the specific request is sufficient. No second account or formal approving review is required. Every production action needs explicit human permission for the repository, action, and current reviewed PR/head SHA or exact artifact/configuration scope. Never remove the managed release policy as N/A.
1. **Discover first, write second** — never guess paths or stack from sibling repos.
2. **Org standards are constants** — read [STANDARDS.md](STANDARDS.md) and apply its database, UI, and security rules to every app repo; discovery fills the repo-specific blanks. If the repo deviates (older stack, no UI, schema owner), document the deviation explicitly.
3. **General templates only** — source blanks from `meavo-booths/meavo-agent-templates`; do not clone `meavo-rp` docs wholesale.
4. **Short entry, deep links** — `AGENTS.md` stays brief; details go in `docs/`.
5. **Delete or mark N/A** — remove sections that don't apply (e.g. `data-model.md` for a CLI tool with no DB).
6. **No secrets** — document env var *names* from `.env.example`, never values.
7. **Minimal scope** — install documentation and its release-policy verification tooling; do not change application code unless requested.

---

## Procedure

### Phase A — Setup

1. Confirm you're in the **target repo root** and inspect its remote/default/staging branches. Start a `feat/`, `fix/`, or `chore/` branch from `origin/staging`. If staging is absent, report missing setup and do not substitute a main PR; local feature work from the audited default branch may continue. Confirm preview isolation before pushing.
2. Fetch templates:
   - If `meavo-agent-templates` is not local: `git clone https://github.com/meavo-booths/meavo-agent-templates.git /tmp/meavo-agent-templates`
   - Run: `/tmp/meavo-agent-templates/scripts/bootstrap-agent-docs.sh .`
   - Prefer `python3 /tmp/meavo-agent-templates/scripts/sync-release-policy.py .` when refreshing only the mandatory policy in an existing repository; it preserves customized content outside managed blocks.
   - Use `--force` only when replacing customized skeleton files is within the requested scope; it is unnecessary for a policy refresh.
3. Read `STANDARDS.md` in `meavo-agent-templates` — the org-wide database, UI, and security conventions you must encode into the filled docs.
4. Read existing `README.md`, `package.json` (or equivalent), and top-level `src/` layout.

### Phase B — Discovery checklist

Fill a scratchpad (don't commit) with:

```
Product: <!-- what does this repo do, one sentence -->
URL / deploy target: <!-- e.g. rp.meavo.app, npm package, internal cron -->
Stack: <!-- language, framework, ORM, auth, hosting -->
Schema owner: <!-- meavo-db / this repo / none -->
Key paths:
  - pages/routes:
  - server actions / API:
  - domain logic:
  - integrations:
  - tests:
Auth gate: <!-- function/middleware name -->
Cron jobs: <!-- paths + schedule if any -->
Sibling repos: <!-- what this borrows from -->
Do NOT list: <!-- 5-10 hard rules -->
Task → file map: <!-- at least 8 rows -->
```

**Task → file map** is the highest-value artifact. Build it from real directories and common tasks for this app.

### Phase C — Fill files (order matters)

| Order | File | Action |
|-------|------|--------|
| 0 | `RELEASE_POLICY.md`, managed blocks, release Cursor rule and verifier | Required constants in every repo; retain verbatim |
| 1 | `AGENTS.md` | Replace placeholders below the managed release block |
| 2 | `.cursor/rules/core.mdc` | Stack, layout, do-nots, `alwaysApply: true` |
| 3 | `.cursor/rules/security.mdc` | Fill auth gate + tool-card ID from STANDARDS.md §4; delete only for pure libraries |
| 4 | `.cursor/rules/ui.mdc` | Fill globs + deviations from STANDARDS.md §5; delete if repo has no UI |
| 5 | `.cursor/rules/domain.mdc` | Skip or delete if no domain layer; else set `globs` |
| 6 | `.cursor/rules/api.mdc` | Skip or delete if no API; else set `globs` |
| 7 | `docs/architecture.md` | Full stack + data flow |
| 8 | `docs/domain.md` | Skip if no business domain (e.g. pure utility lib) |
| 9 | `docs/data-model.md` | Skip if no persistence |
| 10 | `CONTRIBUTING.md` | Match team's actual PR process |
| 11 | `.cursorignore` | Match repo artifacts |
| 12 | `README.md` | Add docs table rows; fix broken agent links |

**Placeholder syntax:** replace entire `<!-- FILL: ... -->` blocks including the comment. Remove optional sections marked `<!-- OPTIONAL: ... -->` when not applicable.

**Legacy `.cursorrules`:** If present, merge unique content into `core.mdc`, then replace `.cursorrules` with:

```
# Cursor rules moved to .cursor/rules/
# See AGENTS.md and .cursor/rules/core.mdc
```

Or delete if fully superseded.

### Phase D — Quality bar

Run the automated checker first:

```bash
/tmp/meavo-agent-templates/scripts/verify-agent-docs.sh .
```

Also run `python3 /tmp/meavo-agent-templates/scripts/sync-release-policy.py . --check`.

Then before opening PR, verify:

- [ ] Mandatory release policy and all managed blocks match the templates; release Cursor rule is always applied
- [ ] Agents stop after verified staging, present the concrete release and wait for one human decision; the PR author may approve
- [ ] GitHub main rules require zero formal approving reviews and no last-push approval, while preserving PRs, CI, conversation resolution and no-bypass protections
- [ ] Production operations require human permission; no remaining instruction directs agents to release main unconditionally

- [ ] Every path in `AGENTS.md` task table exists on disk
- [ ] Every `Do NOT` is enforceable and true for this repo
- [ ] `npm run dev` / test / lint commands are copy-paste correct (from `package.json`)
- [ ] No `<!-- FILL:` placeholders remain (grep the repo)
- [ ] `docs/domain.md` mutation map names real modules
- [ ] Cursor rule `globs` match actual directories
- [ ] STANDARDS.md rules applied (DB ownership, UI kit + mobile-first, security layers) or deviations documented
- [ ] [CHECKLIST.md](CHECKLIST.md) passes

### Phase E — PR

- Branch: `chore/agent-instruction-files` from `staging`
- Base: explicitly `staging` (`gh pr create --base staging --head chore/agent-instruction-files`)
- Title: `docs: add agent instruction files`
- Body: list files added/updated, note optional material marked N/A or skipped, link to CHECKLIST
- Do not merge/auto-merge/queue to main or publish a production deployment as part of bootstrap. Missing staging requires setup, not a main exception.

---

The release policy is never optional for any repo type. New repositories must install it, establish protected staging and main branches, and verify deployment isolation before integration/release work.

## Repo-type hints

| Repo type | Examples | Emphasize | Skip |
|-----------|----------|-----------|------|
| Next.js App Router app | `meavo-gateway`, `hols`, `assembly`, `sales`, `meavo-mrp` | `core.mdc`, `security.mdc`, `ui.mdc`, `domain.mdc`, `api.mdc`, all docs | — |
| Shared npm package (`@meavo/*`) | `meavo-navigation` | Export map, build/publish, consumer repos, release tagging | `ui.mdc` globs (it IS the UI), `domain.md` if no business rules |
| Schema owner | `meavo-db` | `data-model.md` is primary; migration-safety rules (shared DB!) | UI/domain docs, `ui.mdc`, most of `security.mdc` |
| Cron-only / worker | — | `api.mdc` → cron routes; `security.mdc` cron secret; architecture data flow | personas, `ui.mdc` |
| Legacy / pre-standard app | `meavo-rp`, `meavo-clock` | Document actual state; note deviations from STANDARDS.md | Don't pretend it follows the new-app standard |
| Legacy reference tree | `legacy-gas/` subtrees | Separate glob rules under `legacy-*/` (`--with-legacy`) | Don't document as live app |

---

## Anti-patterns

- Copying meavo-rp sheet columns into a repo that doesn't use Rep.Parts26
- Listing `src/lib/domain/` in task table when this repo uses `src/services/`
- 300-line `AGENTS.md` duplicating `docs/architecture.md`
- Leaving `<!-- FILL: -->` in merged files
- Conflicting rules in both `.cursorrules` and `.cursor/rules/core.mdc`
