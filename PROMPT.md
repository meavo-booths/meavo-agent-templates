# Bootstrap prompt for repo-specific agents

Copy-paste the prompt below into a Cursor / Cloud agent session **in the target repo** (not in this repo). It works for any meavo-booths repository.

---

```
You are working in a meavo-booths repository. Your task is to create repo-specific
AI agent instruction files and mandatory release safeguards
(AGENTS.md, CLAUDE.md, RELEASE_POLICY.md, .cursor/rules/*, docs/*, CONTRIBUTING.md)
using the org template pack, so that future agents can produce better code faster
in THIS repo.

## Setup

1. Clone the template pack:
   git clone https://github.com/meavo-booths/meavo-agent-templates.git /tmp/meavo-agent-templates
2. Read these files from it, in order:
   - RELEASE_PROCESS.md — mandatory feature/staging workflow and specific human production permission.
   - STANDARDS.md  — org-wide database, UI (mobile + desktop), and security rules. These are
                     CONSTANTS: copy the applicable ones into this repo's docs verbatim.
   - BOOTSTRAP.md  — your step-by-step playbook. Follow it exactly.
   - examples/AGENTS.example.md — the quality bar for a finished AGENTS.md.
3. Run the skeleton copier from this repo's root:
   /tmp/meavo-agent-templates/scripts/bootstrap-agent-docs.sh .
   (add --with-legacy only if this repo has a read-only legacy subtree like legacy-gas/)

## Rules

- Work on feat/, fix/, or chore/ from origin/staging and explicitly target staging in PRs.
  Missing staging is not permission to push or merge main; report the setup gap.
- Preserve RELEASE_POLICY.md and every managed MEAVO RELEASE POLICY block verbatim.
  No repo type may mark these N/A. Production actions require a real human
  to approve this repository, exact action, and current reviewed PR/head SHA or artifact/configuration scope.
  For a release, complete staging integration and verification, present the concrete PR/head, scope and checks,
  then stop and ask for one human approval before main. The PR author may approve in chat or a human-authored
  PR comment; a clear “yes” to that specific request is sufficient. No second account or formal review is required.
  Changed head/scope needs fresh approval; an unchanged retry can reuse valid approval.
  Never infer or manufacture approval, enable production auto-merge, queue a main PR, or bypass protections.
- DISCOVER FIRST, WRITE SECOND. Read package.json, README, src/ layout, auth code,
  vercel.json, and .env.example before writing any prose. Never guess paths, and never
  copy another Meavo repo's paths, sheet columns, or business rules.
- Org standards from STANDARDS.md apply to every app repo (schema owned by meavo-db,
  no `prisma db push` from apps, auth verified at every layer, tool-card access gating,
  in-house UI kit + @meavo/navigation, mobile-first responsive rules). If this repo
  deviates (older stack, no UI, schema owner, pure package), state the deviation
  explicitly in AGENTS.md — silence means "follows STANDARDS.md".
- Replace every <!-- FILL: ... --> placeholder with repo-specific content, or delete
  the section/file when it does not apply (e.g. docs/data-model.md for a repo with
  no database, ui.mdc for a repo with no UI).
- AGENTS.md stays under ~150 lines. The Task → file table (>= 8 rows, every path must
  exist on disk) and the Do NOT list (5–10 enforceable rules) are the highest-value
  sections. Deep detail goes in docs/, not AGENTS.md.
- Commands in AGENTS.md must be copy-paste correct from package.json scripts.
- Document env var NAMES from .env.example only — never values, never secrets.
- If a root .cursorrules file exists, merge its unique content into
  .cursor/rules/core.mdc and reduce .cursorrules to a one-line pointer (or delete it).
- Update this repo's README.md with a docs table linking AGENTS.md, .cursor/rules/,
  and docs/. Remove stale doc references.
- Scope: documentation plus its managed release-policy verification tooling. Do not change application code.

## Verify

1. Run: /tmp/meavo-agent-templates/scripts/verify-agent-docs.sh .
   Fix every FAIL; resolve or justify every warning.
2. Work through /tmp/meavo-agent-templates/CHECKLIST.md manually — especially the
   "Org standards" and "Accuracy spot-checks" sections.
3. Run: python3 /tmp/meavo-agent-templates/scripts/sync-release-policy.py . --check
4. Grep for leftover placeholders: no "FILL:" may remain in filled agent docs.

## Deliver

Open a PR:
- Branch: chore/agent-instruction-files from staging
- Base: staging (set --base staging explicitly)
- Title: "docs: add agent instruction files"
- Body: list files added/updated, everything marked N/A or deleted (with reason),
  any deviations from STANDARDS.md, and the verify script output summary.
Do not release to main or production as part of this bootstrap task.
```

---

## Repo-specific notes (append to the prompt when relevant)

| Target repo | Append this line |
|-------------|------------------|
| `meavo-db` | "This repo OWNS the shared schema: docs/data-model.md is the primary doc; emphasize migration safety (shared DB across all apps); delete ui.mdc and most of security.mdc." |
| `meavo-navigation` | "This is a shared npm package: emphasize export map, build/publish, release tagging, and consumer repos; it IS the UI so drop ui.mdc globs; skip domain.md." |
| `meavo-rp`, `meavo-clock` | "This is a legacy/pre-standard app: document the ACTUAL current state, and list deviations from STANDARDS.md explicitly rather than describing the target architecture." |
| Repos with `legacy-gas/` or similar | "Run the bootstrap script with --with-legacy and glob-scope legacy.mdc to that subtree only." |
