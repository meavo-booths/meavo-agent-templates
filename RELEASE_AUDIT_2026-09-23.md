# MEAVO release-policy audit — 23 September 2026

All 16 current organization repositories were checked using the live GitHub API. This change updates policy files on feature branches for integration into staging. It does not authorize or perform any merge to main or production deployment.

## Findings and corrections

- The previous central process and Cursor rules explicitly allowed self-merging green release PRs without human review. Root agent entry points often omitted the release gate.
- The 13 established code repos had active main/staging rulesets but required zero approvals. The templates, stock, and UK website repos had no staging branch; stock and templates lacked main protection.
- Some database/navigation instructions directed direct main writes or automatic release-tag publication. App runbooks also omitted approval for production migration, deployment and rollback actions.
- New managed policy files cover Codex, Claude, Cursor and contributor entry points. Approval must name the repository, production action and reviewed content; changed content invalidates it. Dedicated sync and verification tooling preserves custom documentation and detects drift.

## Live protection changes

An additive, active main ruleset now requires an independent approval, dismisses stale approvals, requires approval of the latest push, permits merge commits only, and blocks bypass actors, deletion and force pushes. Existing checks and branch rules remain in place.

Protected staging branches were created for meavo-agent-templates, meavo-stock and office-phone-booths-uk at their unchanged audited main commits. No main ref was changed.

| Repository | Initial staging | Initial release rule on staging | Main approval ruleset |
|---|---|---|---|
| assembly | Present | Present but permissive | [Active rule](https://github.com/meavo-booths/assembly/rules/23894011) |
| hols | Present | Present but permissive | [Active rule](https://github.com/meavo-booths/hols/rules/23894005) |
| meavo-agent-templates | Missing; now created | Missing | [Active rule](https://github.com/meavo-booths/meavo-agent-templates/rules/23894028) |
| meavo-clock | Present | Present but permissive | [Active rule](https://github.com/meavo-booths/meavo-clock/rules/23894019) |
| meavo-db | Present | Missing | [Active rule](https://github.com/meavo-booths/meavo-db/rules/23894014) |
| Meavo-Factory | Present | Present but permissive | [Active rule](https://github.com/meavo-booths/Meavo-Factory/rules/23894007) |
| meavo-gateway | Present | Present but permissive | [Active rule](https://github.com/meavo-booths/meavo-gateway/rules/23894006) |
| meavo-mrp | Present | Present but permissive | [Active rule](https://github.com/meavo-booths/meavo-mrp/rules/23894004) |
| meavo-navigation | Present | Missing | [Active rule](https://github.com/meavo-booths/meavo-navigation/rules/23894012) |
| meavo-rp | Present | Present but permissive | [Active rule](https://github.com/meavo-booths/meavo-rp/rules/23894016) |
| meavo-stock | Missing; now created | Missing | [Active rule](https://github.com/meavo-booths/meavo-stock/rules/23894038) |
| meavo-tasks | Present | Present but permissive | [Active rule](https://github.com/meavo-booths/meavo-tasks/rules/23894025) |
| meavo-tickets | Present | Present but permissive | [Active rule](https://github.com/meavo-booths/meavo-tickets/rules/23894031) |
| office-phone-booths-uk | Missing; now created | Missing | [Active rule](https://github.com/meavo-booths/office-phone-booths-uk/rules/23894032) |
| sales | Present | Present but permissive | [Active rule](https://github.com/meavo-booths/sales/rules/23894013) |
| zeron-material-checker | Present | Present but permissive | [Active rule](https://github.com/meavo-booths/zeron-material-checker/rules/23894030) |

## Validation and remaining limits

- All installed policy files and managed blocks match the canonical templates; all repository diffs pass whitespace checks. Ten regression tests cover idempotent installation, preservation of custom docs, missing/tampered files, malformed markers and invalid release PR sources.
- The Release policy workflow validates installed policy and accepts a main PR only from the same repository’s staging branch. Its editable local manifest is a consistency check, not an authorization boundary. GitHub review requirements are the independent merge gate.
- Organization-wide ruleset creation is unavailable to the current credential because it lacks admin:org scope. All current repos have repository rules; an organization administrator should add equivalent organization-wide protection so future repos inherit it.
- An AI using human administrator credentials is indistinguishable from that human to GitHub/Vercel. Use separate limited agent credentials and keep production credentials and approval under human control. GitHub checks do not gate independent Vercel CLI/API/dashboard routes.
- Vercel metadata confirms main is the production branch for the linked apps. This audit did not change provider permissions or production environment values, and does not certify every staging integration or data destination.
- MRP’s existing build includes SQL migration/backfill scripts. Its database values are marked sensitive and the provider does not reveal their endpoints through the read API, so endpoint isolation could not be verified. Automatic deployment is disabled only for this policy feature branch in its vercel.json; do not merge its PR to staging until the staging database destination is verified. Database migrations must be explicitly included in future production release scope. Legacy production helper scripts elsewhere likewise remain subject to the policy.

Main promotion of these documentation changes remains a separate human-approved release. Do not merge unrelated accumulated staging changes merely to distribute the policy.
