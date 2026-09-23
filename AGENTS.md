<!-- BEGIN MEAVO RELEASE POLICY -->
## Release safety — mandatory for all AI agents

- Default scope: create `feat/`, `fix/`, or `chore/` branches from `staging`; use PRs into `staging` and squash only after required checks pass.
- Do not merge to `main`, enable auto-merge/queue a production PR, or change production without **explicit human approval for this repository, the specific action, and the reviewed PR/head SHA or exact artifact/configuration scope**. Changed scope or head invalidates approval; never infer or generate it. Reuse still-valid approval without asking again.
- Never push directly to `main`/`staging` or bypass protections. Missing `staging` is not permission to use `main`.
- Read [RELEASE_POLICY.md](RELEASE_POLICY.md) before any release, deployment, environment, schema, or tag/package publication action. Verify actual environment destinations before writes.
<!-- END MEAVO RELEASE POLICY -->
