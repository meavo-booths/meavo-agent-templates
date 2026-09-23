<!-- BEGIN MEAVO RELEASE POLICY -->
## Release safety — mandatory for all AI agents

- Default scope: create `feat/`, `fix/`, or `chore/` branches from `staging`; use PRs into `staging` and squash only after required checks pass.
- Do not merge to `main`, enable auto-merge/queue a production PR, or change production without **explicit human approval for this repository, the specific action, and the reviewed PR/head SHA or exact artifact/configuration scope**. Changed scope or head invalidates approval; never infer or generate it. Reuse still-valid approval without asking again.
- Never push directly to `main`/`staging` or bypass protections. Missing `staging` is not permission to use `main`.
- Read [RELEASE_POLICY.md](RELEASE_POLICY.md) before any release, deployment, environment, schema, or tag/package publication action. Verify actual environment destinations before writes.
<!-- END MEAVO RELEASE POLICY -->

# Example — filled `AGENTS.md`

> **This is a calibration sample for a fictional satellite app (`meavo-widgets`, `widgets.meavo.app`).**
> It shows the expected depth, tone, and length of a finished `AGENTS.md`. Do not copy its paths or rules into a real repo — discover your own.

---

# Agent guide — meavo-widgets

Quick orientation for AI agents working in this repo. Read this before exploring blindly.

**Cursor:** `.cursor/rules/core.mdc` and `security.mdc` are always applied. `ui.mdc`, `domain.mdc`, and `api.mdc` apply when editing matching paths.

## What this repo does

Internal tool for tracking widget production requests at `widgets.meavo.app`. Managers create requests, operators update statuses, gateway admins control who can log in. Satellite app of [meavo-gateway](https://github.com/meavo-booths/meavo-gateway) — follows [org STANDARDS](https://github.com/meavo-booths/meavo-agent-templates/blob/main/STANDARDS.md).

## Stack

- Next.js 15 App Router, TypeScript strict, React 19, Tailwind CSS 3
- Prisma 6 via `@meavo/db` (github:meavo-booths/meavo-db#v0.3.1) → shared Neon Postgres
- NextAuth v5, JWT sessions, Google invite-only + credentials
- `@meavo/navigation` shared nav; Vercel hosting

## First files to read

| Task | Start here |
|------|------------|
| Add/change a page | `src/app/(app)/requests/page.tsx`, sibling feature folders |
| Add a mutation | `src/app/actions/requests.ts` (Server Actions pattern) |
| Change request status logic | `src/lib/domain/request-status.ts` |
| Notifications on status change | `src/lib/notifications/enqueue.ts` (enqueue only — gateway sends) |
| Change who can do what | `src/lib/auth-guards.ts` (`requireWidgetsAccess`, `requireManager`) |
| Add a cron job | `src/app/api/cron/`, register in `vercel.json` |
| UI kit component | `src/components/ui.tsx` |
| Nav / tool switcher | `src/components/nav.tsx` (`@meavo/navigation`) |
| Auth & access | `src/lib/auth.ts`, `src/middleware.ts`, `WIDGETS_TOOL_CARD_ID` |
| DB schema | `node_modules/@meavo/db/prisma/schema.prisma` — **edit in meavo-db only** |
| Tests | `src/**/*.test.ts`, run `npm test` |

## Do NOT

- Edit the Prisma schema here — schema lives in [meavo-db](https://github.com/meavo-booths/meavo-db); bump the tag instead
- Run `prisma db push` from this repo — shared DB; a stale schema can drop other apps' tables
- Add shadcn/Radix/MUI — use `src/components/ui.tsx`
- Send email directly — enqueue to `NotificationOutbox`; gateway sends
- Skip the `ToolCardAccess` check in a new action or route — use `requireWidgetsAccess()`
- Add REST endpoints for mutations — Server Actions only (API routes are for cron/health/auth)
- Look up the tool card by `linkedAppKey` at runtime — use `WIDGETS_TOOL_CARD_ID`
- Commit secrets or `.env.local`

## Commands

```bash
npm install
npm run dev        # localhost:3000
npm test           # vitest
npm run lint
npm run build      # prisma generate && next build
```

## Conventions

1. Domain logic in `src/lib/domain/` — actions stay thin: validate, call domain, `revalidatePath()`.
2. Actions return `{ error?: string }` for user-facing failures; never throw to the client.
3. Side effects fire-and-forget: `void enqueueNotification({...}).catch(console.error)`.
4. Mobile-first: verify new pages at 375px and 1280px (see `.cursor/rules/ui.mdc`).

## Scoped task template (preferred from user)

```
Area/route: /requests or /admin
Behaviour: [what should happen]
Reference: [gateway pattern or doc, if any]
Out of scope: [auth / schema / other apps]
```

## Related docs

- [docs/architecture.md](docs/architecture.md) — stack, layout, data flow
- [docs/domain.md](docs/domain.md) — statuses, roles, mutation map
- [docs/data-model.md](docs/data-model.md) — WidgetRequest tables (owned here, defined in meavo-db)
- [CONTRIBUTING.md](CONTRIBUTING.md) — PR process
