<!-- BEGIN MEAVO RELEASE POLICY -->
## Branches and production permission

Create `feat/`, `fix/`, or `chore/` branches from `staging` and open PRs explicitly into `staging`; squash after required checks pass. Never push directly to `main` or `staging`. Production releases use a `staging` → `main` PR and a merge commit. AI agents require explicit human authorization for the repository, production action, and current reviewed PR/head SHA or artifact/configuration scope before merging, enabling auto-merge, queueing, or making any production change. See [RELEASE_POLICY.md](RELEASE_POLICY.md) for the mandatory approval and environment checks; missing staging does not authorize a main release.
<!-- END MEAVO RELEASE POLICY -->
