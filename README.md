# meavo-agent-templates

Org-wide template pack for **AI coding agent instruction files** in [meavo-booths](https://github.com/meavo-booths) repositories.

Use this pack to bootstrap or refresh agent docs in any Meavo project (Next.js apps, shared packages, cron workers, legacy GAS reference trees, etc.) without copying from a sibling app like `meavo-rp`.

## What's in the pack

| Path | Purpose |
|------|---------|
| [STANDARDS.md](STANDARDS.md) | **Org-wide conventions** — unified database, UI (mobile + desktop), security, and architecture rules every repo must follow |
| [INSTRUCTIONS.md](INSTRUCTIONS.md) | **Start here** — human + agent workflow for adopting templates in a target repo |
| [BOOTSTRAP.md](BOOTSTRAP.md) | Agent-only playbook: discover repo → fill templates → verify |
| [CHECKLIST.md](CHECKLIST.md) | Post-bootstrap verification (manual) |
| [templates/](templates/) | Blank files with `<!-- FILL: ... -->` placeholders |
| [examples/](examples/) | A fully filled `AGENTS.md` example + pointers to reference repos |
| [scripts/bootstrap-agent-docs.sh](scripts/bootstrap-agent-docs.sh) | Copies templates into a target repo (strips `.template` suffix) |
| [scripts/verify-agent-docs.sh](scripts/verify-agent-docs.sh) | Automated post-fill verification (placeholders, paths, rule frontmatter) |

## Quick start (human)

```bash
# From your target repo root (e.g. meavo-sales, meavo-gateway)
curl -fsSL https://raw.githubusercontent.com/meavo-booths/meavo-agent-templates/main/scripts/bootstrap-agent-docs.sh | bash -s -- .

# Or clone this repo and run locally:
git clone https://github.com/meavo-booths/meavo-agent-templates.git
./meavo-agent-templates/scripts/bootstrap-agent-docs.sh /path/to/your-repo
```

Then open `AGENTS.md` and the `docs/` files and replace every `<!-- FILL: ... -->` block with repo-specific content. See [INSTRUCTIONS.md](INSTRUCTIONS.md) for the full workflow.

## Quick start (Cursor / Cloud Agent)

Paste into the agent:

```
Bootstrap agent instruction files for this repo using meavo-booths/meavo-agent-templates.
Follow BOOTSTRAP.md in that repo, and apply the org-wide rules from its STANDARDS.md.
Do not copy meavo-rp-specific content — discover this repo's stack, layout, and domain from the codebase.
```

## Design principles

1. **Task-oriented** — agents need “where to change X”, not essays.
2. **Layered** — `STANDARDS.md` (org constants) → `AGENTS.md` (short) → `docs/*` (deep) → `.cursor/rules/*` (enforced).
3. **Repo-specific** — templates are blanks; each app fills in its own stack, paths, and business rules. Org-wide constants come from [STANDARDS.md](STANDARDS.md), not from guessing.
4. **Single source of truth** — link between files; don't duplicate long sections.
5. **Minimal diff discipline** — encoded in `CONTRIBUTING.md` and cursor rules.

## Org-wide conventions

[STANDARDS.md](STANDARDS.md) is the canonical list — database ownership (meavo-db), UI system (Tailwind + in-house kit + `@meavo/navigation`, mobile-first), security (NextAuth v5, tool-card gating, cron secrets, headers), and mutation patterns. The deep-dive reference implementation is [meavo-gateway's AGENTS.md](https://github.com/meavo-booths/meavo-gateway/blob/main/AGENTS.md).

Not every repo uses all of it (e.g. `meavo-db`, `meavo-navigation`, legacy JS apps) — mark deviations explicitly in the target repo's docs.

## Maintaining this pack

When you improve agent docs in one Meavo repo and the pattern is reusable:

1. Generalize the improvement into a template here (keep placeholders).
2. Open a PR to `meavo-agent-templates`.
3. Optionally refresh sibling repos in a follow-up PR.
