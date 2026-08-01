# Meavo org-wide standards

Canonical conventions **every meavo-booths repo must follow**, so all apps stay unified in database structure, UI (mobile + desktop), security, and architecture.

> **How to use this file:** When bootstrapping agent docs in a target repo ([BOOTSTRAP.md](BOOTSTRAP.md)), copy the applicable rules below into that repo's `AGENTS.md` / `.cursor/rules/*` **verbatim where they apply**, and mark deviations explicitly. Repo-specific discovery fills the blanks; these standards fill the constants.
>
> **Reference implementation:** [meavo-gateway](https://github.com/meavo-booths/meavo-gateway) (`meavo.app`). Its `AGENTS.md` is the deep-dive companion to this file — section references below (§n) point into it.

## 1. Ecosystem

One Neon Postgres database shared by all apps. Gateway owns identity; satellite apps read shared tables and write only their own domain tables.

| App | Repo | Domain | Owns in DB |
|-----|------|--------|------------|
| Gateway | `meavo-gateway` | `meavo.app` | Users, teams, tool cards, access, HR, notifications outbox |
| Hols | `hols` | `hols.meavo.app` | Vacation requests, allowances, public holidays |
| Assembly | `assembly` | `assembly.meavo.app` | Questionnaires, submissions |
| Sales | `sales` | `sales.meavo.app` | Deals, clients, products |
| MRP | `meavo-mrp` | `mrp.meavo.app` | Materials, stock movements, invoices |
| Factory | `Meavo-Factory` (private) | `factory.meavo.app` | Production batches, stations |
| Tasks | `meavo-tasks` | `tasks.meavo.app` | Task tracking |
| Requests | `meavo-tickets` | `requests.meavo.app` | Feature requests & voting |
| RP | `meavo-rp` | `rp.meavo.app` | RP-specific data |
| Clock | `meavo-clock` | `clock.meavo.app` | Clock-in / time tracking |

Shared packages: `@meavo/db` (canonical Prisma schema — [meavo-db](https://github.com/meavo-booths/meavo-db)) and `@meavo/navigation` (shared top nav + tool switcher — [meavo-navigation](https://github.com/meavo-booths/meavo-navigation)).

## 2. Required stack (new apps)

| Layer | Choice |
|-------|--------|
| Framework | Next.js 15+ App Router, TypeScript strict, React 19 |
| Styling | Tailwind CSS 3 — **no shadcn / Radix / MUI** unless explicitly approved |
| ORM / DB | Prisma 6 via `@meavo/db` → shared Neon Postgres (`DATABASE_URL` same as gateway) |
| Auth | NextAuth v5 (JWT sessions), bcryptjs 12 rounds for passwords |
| Hosting | Vercel; file storage Vercel Blob; email via gateway + Resend (satellites **enqueue only**) |

No separate backend service, GraphQL, tRPC, or alternative ORM without an explicit architectural decision.

Standard layout (single Next.js repo, `@/*` → `./src/*`):

```
src/app/(app)/        # authenticated routes (route group)
src/app/login/        # public login
src/app/actions/      # Server Actions — primary mutation pattern
src/app/api/          # route handlers: cron, health, streaming, auth ONLY
src/components/       # UI kit (ui.tsx) + feature components
src/lib/              # domain logic, auth, prisma singleton, integrations
src/middleware.ts     # page-level auth gate
```

## 3. Database (unified)

1. **All schema changes go in `meavo-db`** — never in app repos. Workflow: edit schema in meavo-db → tag release → bump `@meavo/db` git ref in every affected app → `npm install` + `prisma generate`.
2. `package.json` points Prisma at the shared package: `"prisma": { "schema": "node_modules/@meavo/db/prisma/schema.prisma" }`.
3. **Never run `prisma db push` from an app repo** — a stale schema can drop other apps' tables. Disable the script like gateway does. Apply schema only from the canonical `@meavo/db` schema; targeted fixes via idempotent `scripts/*.sql` + `prisma db execute`.
4. Naming: PascalCase models, camelCase fields, `cuid()` string IDs, `SCREAMING_SNAKE` enum values, schema organized by owning app with `// ── app ──` section comments.
5. Never duplicate `User` / `Team` tables — foreign-key to shared models.
6. New satellite app additions to meavo-db: domain models, `ToolCard` seed (kind `APP_ACCESS`, stable `seed-<app>-tool` ID), notification event types in gateway's catalog.

Deep dive: gateway `AGENTS.md` §8.

## 4. Security (unified)

1. Auth is verified at **every layer independently**: middleware (pages), section layouts, Server Actions, and API routes. Middleware passes `/api/*` through — API routes are never assumed protected.
2. Satellite apps gate login **and every request** on `ToolCardAccess` for the app's stable tool-card ID (env var, e.g. `SALES_TOOL_CARD_ID`) — never look up by `linkedAppKey` at runtime. Revocation in gateway Admin must take effect immediately.
3. Session: JWT strategy; extend `Session.user` with `id`, `systemRole`, `hrAccess` via `src/types/next-auth.d.ts`; refresh role fields from DB in the JWT callback.
4. Cron routes require `CRON_SECRET` Bearer auth. Health check `GET /api/health` (`SELECT 1`).
5. Credentials login: bcrypt 12 rounds, minimum 8 chars, login throttling via shared `LoginThrottle` table (10 failures / 15 min). Google OAuth is invite-only (user must already exist).
6. Security headers in `next.config.ts`: `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin`, `Strict-Transport-Security`.
7. Uploads: Vercel Blob, 10 MB limit, validate MIME + extension, store `storageKey`, stream downloads through an authenticated route with sanitized filenames. Embedded HTML → sandboxed same-origin iframe with CSP.
8. `export const dynamic = "force-dynamic"` on authenticated layouts and any page touching the DB at request time.
9. No secrets in client code or committed files; document env var **names** in `.env.example` only.

Deep dive: gateway `AGENTS.md` §6, §7, §14.

## 5. UI — desktop and mobile (unified)

1. **No external component library.** Small in-house kit in `src/components/ui.tsx`: `Card`, `Button` (`primary` / `secondary` / `danger` / `ghost`), `Input`, `Textarea`, `Select`, `PageHeader`.
2. **Brand palette:** brand green `#30A46C` (500/600), `#0C8F61` (700) for primary actions; Tailwind `slate` scale for neutrals; errors `text-red-600`. Official reference: [meavo.com/style-guide](https://meavo.com/style-guide).
3. **Shell:** `@meavo/navigation` top nav + tool switcher (`MEAVO_APP_KEY`, `GATEWAY_URL` env vars), then `<main className="mx-auto max-w-6xl px-3 py-4 sm:px-4 sm:py-8">`.
4. **Visual language:** cards `rounded-xl border border-slate-200 bg-white shadow-sm`; inputs/buttons `rounded-lg`; page titles `text-xl sm:text-2xl font-semibold text-slate-900`; body `text-sm text-slate-600`; focus rings `focus:ring-brand-100 focus:border-brand-500`.
5. **Mobile-first responsive — required on every page:**
   - Style for the narrow viewport first; add `sm:` / `lg:` upward overrides. Grids: `grid gap-6 sm:grid-cols-2 lg:grid-cols-3`.
   - Wide data tables must degrade on mobile: stacked cards or `overflow-x-auto` — never clipped columns.
   - Touch targets ≥ 44px; no hover-only affordances for critical actions.
   - Verify each new page at 375px and 1280px widths before PR.
6. Server Components by default; `"use client"` only for interactive leaves. `loading.tsx` skeletons (`animate-pulse` slate blocks) in feature route folders. Modals: accessible custom pattern (focus trap, Escape, `role="dialog"`).

Deep dive: gateway `AGENTS.md` §5.

## 6. Mutations & side effects (unified)

1. Mutations are **Server Actions** returning `{ error?: string }` for user-facing failures; `revalidatePath()` after writes. New REST endpoints only for cron / streaming / auth.
2. Notifications: satellite apps **enqueue** to `NotificationOutbox` (copy gateway's `enqueue.ts` pattern); only gateway sends email. Event types `{app}.{domain}.{action}`, registered in gateway's `event-catalog.ts` first.
3. Fire-and-forget side effects with `.catch(console.error)` — never block the mutation.

## 7. New-app launch & registration

Follow gateway `AGENTS.md` §9 (tool card registry, navigation package update, seeds) and §13 (deployment checklist + Vercel config). Minimum env vars: `DATABASE_URL`, `AUTH_SECRET`, `AUTH_URL`, `<APP>_TOOL_CARD_ID`, `MEAVO_APP_KEY`, `GATEWAY_URL`.

## 8. Known deviations (do not copy into new apps)

- Some older repos (`meavo-rp`, `meavo-clock`) predate parts of this standard (JS instead of TS, sheet-based flows). Document their actual state in their own `AGENTS.md`, but port toward this standard when rewriting.
- Admin bypass of tool-card access is inconsistent across apps today (gateway §6.5) — new apps should grant admins explicit access via seed rather than invent another bypass.

## 9. Branching & release (unified)

Every repo uses `main` (production) and `staging` (integration), both protected: no direct pushes, PR + passing `Typecheck` required, no force-push or deletion. Branch off `staging` → PR into `staging` (**squash**) → verify on `https://<project>-git-staging-meavo-gateway.vercel.app` → PR `staging` into `main` (**merge commit**) to release. Never squash `staging` into `main`, and never `vercel --prod`.

Preview deployments — `staging` and every feature branch — resolve the `staging` Neon branch; only production resolves production data. Because `@meavo/db` is pinned per app by tag, schema changes must be backward compatible (add, migrate every app, then remove in a later release).

Full guide: [RELEASE_PROCESS.md](RELEASE_PROCESS.md). Distributed to repos as `.cursor/rules/release-process.mdc` — an org-wide constant, copied verbatim with nothing to fill in.

## 10. Keeping this file authoritative

When a convention changes (new shared package, auth pattern, palette update):

1. Update this file **and** gateway's `AGENTS.md` in the same change window.
2. Refresh affected repos' `.cursor/rules/security.mdc` / `ui.mdc` copies.
3. Deviating repos must state the deviation in their own `AGENTS.md` — silence means "follows STANDARDS.md".
