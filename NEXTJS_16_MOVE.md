# Moving a MEAVO app from Next.js 15.5 to 16

Written 17 November 2026, before the first app was moved. Update it after each move with what was actually needed.

## Why

On Next.js 15.5 a client-side page change that follows a Server Action can stay on the old page until the next router update. Measured on Sales staging in a real browser on 17 November 2026: 5 of 20 saves stalled for 28 to 54 seconds, each released by the notification bell's once-a-minute poll. The router fix is vercel/next.js#95391. It shipped in **16.3.0** and is in no 15.5 release. Target the latest 16.4 or later.

Until an app is on 16.3 or later, two rules keep it out of trouble (Sales follows both since sales#263 to #267):

1. Nothing that runs by itself may be a Server Action. A read that fires when a page opens, or on a timer, goes through a GET route. The notification bell is given `refreshUrl` (`@meavo/navigation` 0.3.0-rc.6 or later), not a `refresh` action.
2. After a Server Action, do not call `router.push()`. Let the browser load the next page (`window.location.assign`). Sales has a helper, `src/lib/navigate-after-action.ts`, and a check that rejects the old patterns.

## Before you start

- `next-auth` must be `5.0.0-beta.31` or later. Earlier betas declare Next.js 14 and 15 only, and `npm ci` fails on the peer range.
- `@meavo/navigation` declares `next >= 15`, so any version works; use 0.3.0-rc.6 or later for `refreshUrl`.
- Node.js 20.9 or later and TypeScript 5.1 or later. Vercel runs these apps on Node 24.
- Read the official guide for the version you are installing: <https://nextjs.org/docs/app/guides/upgrading/version-16>. After the upgrade, the docs that match the installed version are in `node_modules/next/dist/docs/`.

## Steps

1. Worktree from `staging`.
2. `npx @next/codemod@canary upgrade latest`. It updates `next`, `react` and `react-dom`, replaces `next lint` with the ESLint CLI, moves `experimental.turbopack` to the top level and removes `unstable_` prefixes.
3. **Build tool.** Turbopack is the default in 16. If `next.config` has a `webpack` function (Sales has one; so does any app using a plugin that adds one, as MRP's service-worker plugin does), the build fails until you either pass `--webpack` to `next dev` and `next build`, or move the setting to `turbopack`. Passing `--webpack` is the smaller change; MRP does this.
4. **`middleware.ts`.** Leave the file name as it is for the move. It is deprecated in favour of `proxy.ts` but still works, and renaming it changes the runtime to Node.js only. Rename in a separate change.
5. **`revalidateTag(tag)`** now needs a second argument. `revalidateTag(tag, "max")` keeps serving the old data while it refreshes; inside a Server Action where the person must see their own change at once, use `updateTag(tag)`.
6. **Images.** Only `quality={75}` is allowed unless `images.qualities` lists more. Local images with a query string need `images.localPatterns`. None of the shared-database apps used these on 17 November 2026; check again.
7. Request APIs (`params`, `searchParams`, `cookies()`, `headers()`) must be awaited. The apps were written on 15 and already do; if the type check disagrees, run `npx @next/codemod@canary next-async-request-api .`.
8. Do **not** turn on `cacheComponents` or `reactCompiler` as part of the move. They are separate decisions.
9. Run the type check, the lint command, the build and the repository's own checks.
10. Pull request into `staging`. On the staging site, signed in, in a real browser window that is visible: open a list, open a record, save something, move between pages with links, sign out and in if the app's sign-in was touched.
11. Release pull request; one yes per wave of apps.

## Checking in a browser

Use a real browser window that is in front. A hidden or embedded browser pane may not paint frames (`requestAnimationFrame` never fires), and then parts of the page never become interactive and page changes appear stuck for reasons that have nothing to do with the app. If you measure timings, confirm frames are painting first.

To measure whether in-app page changes after a save still stall, Sales has a per-browser switch: `localStorage.setItem("sales.in-app-navigation", "1")` restores `router.push()` + `router.refresh()` after a save in that browser. Run the same save 20 times, half of them within two seconds of the page opening, and count the ones that take more than a few seconds.

## Order

MRP first (already on 16.2.6, a step inside version 16), with one small app as the first real move. Then the small apps, then Assembly, RP and Factory, then Gateway, then Sales. Gateway is the sign-in for every app: move it alone, at a quiet time.
