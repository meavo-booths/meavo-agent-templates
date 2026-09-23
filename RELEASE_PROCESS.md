# MEAVO branching and release process

AI agents may complete authorized work on feature branches and through PRs into `staging`. **Every production action requires explicit permission from a human for the repository, the specific action, and the current reviewed PR/head SHA or exact artifact/configuration scope.** **Feature → staging → stop and ask → one human approves → main.** The human may be the PR author; a second person or separate account is not required. Passing CI alone never authorizes a production release.

The complete, self-contained policy distributed to every repository is [templates/RELEASE_POLICY.md.template](templates/RELEASE_POLICY.md.template), installed as root `RELEASE_POLICY.md`. Read it before any release, deployment, environment, schema, or tag/package publication action. The short gate also lives in each repository's root `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, and always-applied Cursor release rule.

## 1. Branches

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

Check the PR's actual repository, base and head. When required CI passes, squash-merge into `staging` and verify its deployment where applicable. Confirm the actual project and environment before writing to any service: a branch name or preview URL does not prove that its database, storage, or external integrations are isolated from production.

## 3. Production release

An agent may prepare a release PR and its review evidence:

```bash
gh pr create --base main --head staging --title "Release: <scope>"
```

Complete staging integration and verification first. Present the exact release PR/head SHA, release scope, checks, staging result, and any separate migration/package/environment operations; **stop and ask for one human approval before main**. Accept the PR author's own decision in the conversation or a human-authored PR comment. A clear “yes” responding to that specific request is sufficient; a formal approving review, another person or another account is not required. Wait for that decision before merging, enabling auto-merge, queueing, or invoking any other production path. Never infer it from the original implementation request, green CI, silence, or an agent-authored approval.

Recheck the repository, `staging` source, `main` base, approved head SHA, and approval immediately before acting. Changed content or scope needs new human approval; an existing approval for the unchanged verified staging release remains valid without asking again, including when retrying a failed merge command. Confirm required server checks and branch rules pass. Never generate an approval on the human's behalf. Use a merge commit and a head-SHA match guard where available. Never squash or rebase the staging-to-main release.

The same permission gate covers production redeployments, promotions, rollbacks, domain aliases, environment changes, schema/data operations, release tags, and package publication. Do not use `vercel --prod`, an API/dashboard action, a release tag, or a manual workflow to evade the PR process. Explicit permission for a main merge does not silently authorize a separate production operation.

## 4. Required enforcement

Required configuration and deployed configuration are distinct. Inspect live rulesets, branch protections, CI and provider settings before claiming enforcement.

- `main`: PRs, passing required checks, resolved review conversations, staging-only source, merge commits for releases, and no direct/force pushes, deletion or bypass actors. Set `required_approving_review_count: 0` and `require_last_push_approval: false`. GitHub prohibits formal PR self-approval; these settings permit the author to supply the separate human consent that agents must obtain.
- `staging`: PRs and required checks; no direct/force pushes or deletion.
- Production deployment paths and credentials: human-controlled approval and access at the provider as well as GitHub. A GitHub environment gate covers only jobs that use that environment; it does not automatically gate a separate Git integration.
- Policy and source-branch validation: install the managed policy verifier/workflow and make its check required where supported. It catches missing or altered policy and wrong release source branches; it cannot prove a human supplied permission. A repository-local hash manifest is editable in the same PR and is only a drift check. The post-staging human-consent checkpoint is enforced by agent instructions, while GitHub enforces branch and CI rules. Zero required formal reviews does not give an agent permission to release.

Agents using a human's credentials look like that human to GitHub and deployment providers. Instructions, commit authors, labels and local hooks cannot solve that identity problem. Prefer separate limited agent credentials and human control of production. The author can provide that human decision; separate limited agent credentials improve identity separation but are not a second-human requirement. Do not weaken a gate to make an agent's release possible.

CI commands and required status names must match each repository. `Typecheck` is a common existing check, and `meavo-db` validates Prisma; do not assume every repository has identical scripts or required contexts.

## 5. Environment and schema safety

Verify actual destinations before deployment, migration, seed, or other writes. Preview/staging/local environments must use non-production resources; check provider scopes and local `.env` files without exposing secret values. Never broaden production database or storage credentials to preview/development. If a destination is unknown, stop that write and report the gap.

Schema changes belong in `meavo-db`. Because consumers may use different pinned tags, changes must remain backward compatible: add, migrate all consumers, then remove in a later approved release. Applying production migrations, publishing consumed tags/packages, and deploying consumer apps are separate approval scopes.

Auth callbacks, deployment protection, cross-app URLs, blob stores and staging URLs vary by project. Inspect the current configuration and document verified facts in that repository; historical settings are not organization-wide guarantees.

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

The full bootstrap also installs the release policy. Existing customized agent documentation should be preserved while managed release blocks are refreshed. Never remove the policy as “N/A” for a library, documentation repository, legacy app, or new app.

Commit policy updates on a feature branch and open a PR into `staging`. Installing these files does not itself change GitHub settings or authorize a main release. Updating the canonical default branch still requires the same human production gate.

## 7. Repository coverage

The 2026-09-23 audit inventory includes these 16 repositories:

`meavo-gateway` · `hols` · `assembly` · `sales` · `meavo-mrp` · `Meavo-Factory` · `meavo-tasks` · `meavo-tickets` · `meavo-rp` · `meavo-clock` · `meavo-db` · `meavo-navigation` · `zeron-material-checker` · `meavo-agent-templates` · `meavo-stock` · `office-phone-booths-uk`

New repositories must enroll in the same protections and policy checks before integration/release work. An organization-wide ruleset is preferred for future-repository coverage; creating or changing it requires an appropriately scoped organization-admin credential. Per-repository rules must be audited and enrolled explicitly when organization-wide coverage is unavailable.

This is an inventory, not a claim that every repository already has staging, CI, policy files, or effective production protection. Audit and record those states separately. The policy also applies to future repositories.
