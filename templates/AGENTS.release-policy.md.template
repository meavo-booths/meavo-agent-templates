<!-- BEGIN MEAVO RELEASE POLICY -->
## Release safety — mandatory for all AI agents

- **The only human gate is merging `staging` → `main`.** Everything before it is agent work: create `feat/`, `fix/`, or `chore/` branches from `staging`, open PRs into `staging`, and squash-merge or enable auto-merge once checks pass, without asking.
- Agents may also write to verified staging resources (staging DB scripts and data, staging deployments), re-pin dependencies to approved tags through `staging`, open release PRs, and run read-only production queries through the guarded helper.
- To release, list every release PR in the bundle with its scope and production steps (release tag, production SQL) in one message and wait for one human yes. That yes covers the bundle, including re-pins to the approved tag; ask again only if `staging` gains unrelated changes. Merge releases with a merge commit.
- Never push directly to `main`/`staging`, bypass protections, or change production outside an approved release. From staging, never touch records in an external system shared with production.
- Read [RELEASE_POLICY.md](RELEASE_POLICY.md) before release, deployment, environment, schema, or tag work. Verify actual environment destinations before writes.
<!-- END MEAVO RELEASE POLICY -->
