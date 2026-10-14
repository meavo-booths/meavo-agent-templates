<!-- BEGIN MEAVO RELEASE POLICY -->
## Branches and production permission

Create `feat/`, `fix/`, or `chore/` branches from `staging` and open PRs explicitly into `staging`; squash after required checks pass. Never push directly to `main` or `staging`. Production releases use a `staging` → `main` PR and a merge commit. The only human gate is that merge: AI agents list every release PR in the bundle with its scope and production steps (release tag, production SQL) and wait for one human yes, which covers the whole bundle. No second account or formal approving review is required. Everything before the merge, including staging integration and staging database changes, is agent work. See [RELEASE_POLICY.md](RELEASE_POLICY.md) for the environment checks; missing staging does not authorize a main release.
<!-- END MEAVO RELEASE POLICY -->
