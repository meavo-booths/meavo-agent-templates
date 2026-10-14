# MEAVO branching and release process

**The only human gate is the merge from `staging` into `main`.** **Feature → staging (agent) → release PR → one human yes → main.** Everything before that merge is agent work and needs no further permission: feature branches, PRs into `staging`, squash-merging or auto-merging them when green, writes to verified staging resources, re-pins to approved tags, release PRs, and read-only production queries through the guarded helper. One yes covers a whole release bundle, including its release tag and production SQL. The human may be the PR author; a second person or separate account is not required. Passing CI alone never authorizes a production release.

The complete, self-contained default policy is [templates/RELEASE_POLICY.md.template](templates/RELEASE_POLICY.md.template), installed as root `RELEASE_POLICY.md`. Read it before any release, deployment, environment, schema, or tag/package publication action. The short gate also lives in each repository's root `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, and always-applied Cursor release rule.

## Registered website exception

Only **`meavo-booths/office-phone-booths-uk`** skips staging. This separate website uses **feature → verify (agent) → one human yes → main**. Create its feature branch from `origin/main`, open the PR explicitly into `main`, and verify the feature checks/preview. Give the PR, its scope and check results in one message and wait for one human yes; the PR author may approve. Recheck required checks and scope, merge with a merge commit, and verify production. Ask again only if the PR gains unrelated changes.

No staging branch or environment is required for this website. Direct pushes, bypasses, production shortcuts, and inferred or agent-authored approval remain prohibited. Its required `Release policy` check accepts only a nonempty, non-main source branch in the same repository; forks remain blocked. All other repositories, including this template repository, retain the staging procedure below.

The exception is maintained in [the website templates](templates/repositories/meavo-booths/office-phone-booths-uk/). The synchronization tool selects it using the exact GitHub origin identity, never a directory name or a user-selectable generic exemption. An unknown repository does not gain this exception because staging is absent.

## 1. Branches (default staging process)

| Branch | Purpose | Agent workflow |
|--------|---------|----------------|
| `feat/…`, `fix/…`, `chore/…` | Short-lived implementation and preview work | Branch from the latest `origin/staging`, commit, push, and open a PR explicitly targeting `staging` |
| `staging` | Shared integration and non-production verification | PRs only; squash after required checks pass; verify the resulting staging deployment |
| `main` | Production release branch | Only a `staging` → `main` PR, one explicit human approval (PR author allowed), required checks, and a merge commit |

Never push directly to `main` or `staging`, force-push/delete them, or bypass their protections. If staging is absent, stop integration/release work and report the missing setup; local feature work from the audited default branch can continue for onboarding. Verify preview isolation before pushing. Missing staging is not permission to merge into main.

## 2. Daily workflow

```bash
# Inspect the target repository and branches first.
git remote -v
git fetch origin
git checkout -b feat/add-invoice-filter origin/staging

# Work, run the repository's checks, then publish the feature branch.
git add <reviewed-files>
git commit -m "Add invoice filter"
git push -u origin feat/add-invoice-filter
gh pr create --base staging --head feat/add-invoice-filter
```

Check the PR's actual repository, base and head. When required CI passes, squash-merge into `staging` (or enable auto-merge) without asking, and verify its deployment where applicable. Staging database scripts, staging data fixes and other writes to verified staging resources are also agent work. Confirm the actual project and environment before writing to any service: a branch name or preview URL does not prove that its database, storage, or external integrations are isolated from production.

Verify staging on the build that the Git integration created for the merged commit. The `<project>-git-staging-<team>.vercel.app` URL belongs to that integration and must never be assigned by hand: `vercel alias set` on it, `vercel deploy` or `vercel redeploy` from a `staging` checkout, or an API deployment with `staging` git metadata permanently detaches the URL from automatic updates, so every later staging build looks stale. If the URL lags, check the unique deployment URL of the READY `staging` build, and repair the URL as described in [AGENT_ENVIRONMENTS.md](AGENT_ENVIRONMENTS.md); the repair only affects staging and needs no approval.

## 3. Production release

An agent may prepare a release PR and its review evidence:

```bash
gh pr create --base main --head staging --title "Release: <scope>"
```

When several repositories release together (for example `meavo-db` + `meavo-gateway` + `sales`), open every release PR first and **ask once for the whole bundle**: list each repository and PR, the scope in plain words, check results, the staging result, any commit on `staging` that is not part of the requested work, and the production steps that come with it (for example "tag `v0.91.0` and apply `scripts/x.sql` to production"). Accept the PR author's own decision in the conversation or a human-authored PR comment. A clear “yes” covers the whole bundle; a formal approving review, another person or another account is not required. Never infer it from the original implementation request, green CI, silence, or an agent-authored message.

The yes also covers later commits that only re-pin a dependency to the approved tag. Ask again only if `staging` gains unrelated, unreviewed changes or the scope changes; an unchanged retry needs no new yes. Immediately before each merge, recheck the repository, `staging` source, `main` base and checks, and that nothing outside the approved scope arrived. Use a merge commit. Never squash or rebase the staging-to-main release.

Order for a schema release: merge the `meavo-db` release, tag its merge commit, apply its SQL to production with `scripts/apply-sql.sh production` (host- and checksum-checked, from the tag), re-pin consumers to the tag through `staging`, then merge the consumer releases. Verify each production deployment.

Production actions outside a release PR (redeploys, promotions, rollbacks, domain aliases, environment/secret changes, production data fixes) each need their own yes. Do not use `vercel --prod`, an API/dashboard action, or a manual workflow to evade the PR process.

## 4. Required enforcement

Required configuration and deployed configuration are distinct. Inspect live rulesets, branch protections, CI and provider settings before claiming enforcement.

- `main`: PRs, passing required checks, resolved review conversations, staging-only source, merge commits for releases, and no direct/force pushes, deletion or bypass actors. Set `required_approving_review_count: 0` and `require_last_push_approval: false`. GitHub prohibits formal PR self-approval; these settings permit the author to supply the separate human consent that agents must obtain.
- `staging`: PRs and required checks; no direct/force pushes or deletion.
- Production deployment paths and credentials: human-controlled approval and access at the provider as well as GitHub. A GitHub environment gate covers only jobs that use that environment; it does not automatically gate a separate Git integration.
- Policy and source-branch validation: install the managed policy verifier/workflow and make its check required where supported. It catches missing or altered policy and wrong release source branches; it cannot prove a human supplied permission. A repository-local hash manifest is editable in the same PR and is only a drift check. The staging → main human checkpoint is enforced by agent instructions, while GitHub enforces branch and CI rules. Zero required formal reviews does not give an agent permission to release.

Agents using a human's credentials look like that human to GitHub and deployment providers. Instructions, commit authors, labels and local hooks cannot solve that identity problem. Prefer separate limited agent credentials and human control of production. The author can provide that human decision; separate limited agent credentials improve identity separation but are not a second-human requirement. Do not weaken a gate to make an agent's release possible.

CI commands and required status names must match each repository. `Typecheck` is a common existing check, and `meavo-db` validates Prisma; do not assume every repository has identical scripts or required contexts.

## 5. Environment and schema safety

Verify actual destinations before deployment, migration, seed, or other writes. Preview/staging/local environments must use non-production resources; check provider scopes and local `.env` files without exposing secret values. Never broaden production database or storage credentials to preview/development. If a destination is unknown, stop that write and report the gap. Some staging integrations talk to real external systems (for example Sales staging uses the real Xero organisation); from staging, never create, change or delete records there.

Schema changes belong in `meavo-db`. Because consumers may use different pinned tags, changes must remain backward compatible: add, migrate all consumers, then remove in a later release. SQL scripts are transactional and idempotent; agents apply them to staging (twice, to prove reruns are safe) with `scripts/apply-sql.sh staging`. Production application, the release tag and consumer re-pins are part of the approved `meavo-db` release bundle, not separate approvals.

Auth callbacks, deployment protection, cross-app URLs, blob stores and staging URLs vary by project. Inspect the current configuration and document verified facts in that repository; historical settings are not organization-wide guarantees.

[Development and staging guidance](AGENT_ENVIRONMENTS.md) covers auth variable scopes and callback diagnosis, database destinations, isolated storage, staging branch URLs, and deployment protection. Verify each project's current configuration instead of assuming all environments share the same settings. Distribute it with `scripts/sync-agent-instructions.py`; do not copy production credentials or disable protection based on documentation alone.

## 6. Distribution and verification

From a checkout of this template repository:

```bash
# Update only managed release-policy files, entry-point blocks and tooling.
python3 scripts/sync-release-policy.py /path/to/target-repo

# Check that the managed copies match the canonical templates.
python3 scripts/sync-release-policy.py /path/to/target-repo --check

# Verify installed policy and release-source rules in the target repository.
python3 /path/to/target-repo/scripts/verify-release-policy.py /path/to/target-repo
```

For a source archive without an origin remote, pass `--repository meavo-booths/office-phone-booths-uk` to select the registered website policy explicitly. An explicit identity must match an existing GitHub origin; an unknown/conflicting origin or lost identity on an installed exception fails before writing. Manifest identity/profile fields record policy selection and detect drift; they do not authorize releases. Runtime source validation uses the GitHub event repository identity.

The full bootstrap also installs the selected release policy. Existing customized agent documentation should be preserved while managed release blocks are refreshed. Never remove the policy as “N/A” for a library, documentation repository, legacy app, or new app.

Commit policy updates on a feature branch and open a PR into `staging`, except for the registered website, whose feature PR targets `main` and waits for the human yes before merging. Installing these files does not itself change GitHub settings or authorize a main release. Releasing the canonical default branch goes through the same staging → main gate; a policy roll-out across repositories is one release bundle.

## 7. Repository coverage

The 2026-09-23 audit inventory includes these 16 repositories:

`meavo-gateway` · `hols` · `assembly` · `sales` · `meavo-mrp` · `Meavo-Factory` · `meavo-tasks` · `meavo-tickets` · `meavo-rp` · `meavo-clock` · `meavo-db` · `meavo-navigation` · `zeron-material-checker` · `meavo-agent-templates` · `meavo-stock` · `office-phone-booths-uk`

New repositories must enroll in the same protections and policy checks before integration/release work. An organization-wide ruleset is preferred for future-repository coverage; creating or changing it requires an appropriately scoped organization-admin credential. Per-repository rules must be audited and enrolled explicitly when organization-wide coverage is unavailable.

This is an inventory, not a claim that every repository already has staging, CI, policy files, or effective production protection. Audit and record those states separately. The policy also applies to future repositories.
