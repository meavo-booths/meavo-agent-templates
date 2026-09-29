# Registered website release exception — 29 September 2026

The owner requested that the separate, low-risk `meavo-booths/office-phone-booths-uk` website release feature PRs directly into main without staging. Explicit human approval of the verified PR/head remains required; the PR author may supply it. Required PRs, CI, conversation resolution, merge commits, and branch protections remain.

A live read found this workflow already installed in the website's main branch, at `4119f00640b23c964f16071fc1d2d17b7a456753`, under policy version `2026-09-28.1`. Its staging branch no longer exists. There were no open PRs, pending auto-merges, or queued merges. Main rules already accept zero formal approving reviews with latest-pusher approval disabled and no bypass actors; `Release policy` and `Website quality` remain required and bound to GitHub Actions. No GitHub settings change is needed for this exception.

The remaining defect was central synchronization: the website's local policy warned that syncing from this template pack would restore staging. Its policy also incorrectly stated that a staging branch still existed.

This correction registers website-specific policy, agent blocks, and Cursor guidance in the canonical templates. Synchronization selects them by the exact GitHub repository identity and records that selection. Runtime event validation permits same-repository non-main source branches only for this website; other repositories retain staging-only main releases. The shared release process and onboarding instructions identify this sole exception. A lost or conflicting identity must not silently reset an installed exception.

This template repository itself continues through feature → staging → human approval → main. The website prepares a feature PR directly into main and stops after verification for human approval. This settings/documentation request does not authorize either new main merge. No production deployment, migration, tag/package publication, or preview-login change is included.
