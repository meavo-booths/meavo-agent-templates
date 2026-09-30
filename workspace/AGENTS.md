# CursorDev workspace rules

This is the MEAVO-Apps umbrella workspace, not an application repository.

- Before starting or resuming any task, read `_shared/RELOCATION.md`, identify the owning app using `_shared/workspace.json`, and run `python3 _shared/tools/workspace.py check`. Old chat paths may be stale; use `workspace.py locate OLD_PATH`.
- Each app owns one top-level container: `repo/` holds its canonical Git checkout; `worktrees/` holds task checkouts; `output/<task>/` holds screenshots, reports and local verification artifacts; `legacy-clones/` preserves existing independent Git histories.
- Run commands and install dependencies inside the selected Git checkout. Read its `AGENTS.md` before changing files. Application source and durable tests/scripts belong in that repository.
- Never create task directories, application code, package files or `node_modules` directly under CursorDev. Root additions are limited to registered app containers, `_shared`, and workspace configuration/instructions. Register a deliberately requested new app in `_shared/workspace.json`.
- Reuse an appropriate worktree. To create one, use `python3 _shared/tools/workspace.py worktree APP TASK --base REF --branch BRANCH`; resolve the base using that repository's release policy. The helper prints the destination and supports `--dry-run`. Do not create extra full clones for ordinary task isolation.
- Shared database code belongs to `meavo-db`; shared navigation belongs to `meavo-navigation`. A cross-app task uses each owning repository. Keep cross-app reports in `_shared/output/<task>/` and workspace utilities in `_shared/tools/`.
- Keep the single MEAVO-Apps project pointing to CursorDev. Select the actual checkout as each command's working directory; app containers are not Git roots.
- Run the checker again at completion. Review temporary worktrees then: retain unfinished work; retire a checkout only after preserving needed uncommitted, untracked and ignored files and confirming its commits are retained. Never force-delete a checkout or prune a real working directory as cleanup.
- Existing release, database and production-approval rules remain in effect. Moving local files grants no release authorization.
