<!-- BEGIN WORKSPACE LAYOUT -->
## Workspace and agent entry points

- Identify this repository's owning app before writing. Run app commands and install dependencies from its Git checkout, never from an umbrella workspace root.
- At task start, completion, and after resuming an old chat, look up the ancestor containing `_shared/workspace.json`. If present, read its `AGENTS.md` and `_shared/RELOCATION.md`, resolve this checkout in that registry, and run `python3 <workspace>/_shared/tools/workspace.py check`. Do not reuse historical paths without consulting the relocation index.
- In that workspace, keep source in the app's `repo/` or registered `worktrees/`, task artifacts in its `output/<task>/`, and cross-app artifacts in `_shared/output/`. Reuse an appropriate checkout; create another only with the workspace helper and the base required by `RELEASE_POLICY.md`.
- In a standalone or cloud clone without that registry, this Git checkout is the app boundary. Keep temporary artifacts under ignored `.local/agent-output/`. Do not invent an umbrella root or require unavailable local files. If a second checkout is necessary, use ignored `.local/worktrees/<task>/` inside this app, or the host's managed worktree facility; preserve existing work.
- Never create task folders, package files, or dependency installations beside the app containers. Keep shared database changes in `meavo-db` and shared navigation changes in `meavo-navigation`.
- Preserve uncommitted, untracked, and ignored files before retiring a checkout. Do not force-delete working copies as cleanup.
- `CLAUDE.md` imports this file; Cursor's workspace rule points here. Keep shared guidance here rather than maintaining conflicting agent-specific copies. Read [environment guidance](AGENT_ENVIRONMENTS.md) before environment or deployment work; the existing release-approval policy still applies.
<!-- END WORKSPACE LAYOUT -->
