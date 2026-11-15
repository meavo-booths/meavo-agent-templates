# One folder per app

This directory preserves the reusable CursorDev organization rules and tools.
The app repositories themselves remain independent Git repositories. The umbrella
workspace does not need to become a monorepo.

```text
Workspace/
  AGENTS.md
  CLAUDE.md
  app-name/
    repo/
    worktrees/
    output/
    legacy-clones/
  _shared/
    workspace.json
    RELOCATION.md
    tools/
    output/
```

For an existing workspace, retain its registry and relocation index. Update only
the reusable files: copy `AGENTS.md` and `CLAUDE.md` to the workspace root and the
contents of `tools/` to `_shared/tools/`. Review existing custom root instructions
before replacing them. Never copy another machine's registry or migration logs.

For a fresh workspace, create app containers and clone each canonical repository
into its own `repo/`. Adapt `workspace.example.json` to the actual app paths and
save it as `_shared/workspace.json`. Register every checkout and its Git common
directory. Write `_shared/RELOCATION.md` with any actual path changes, or state
that the workspace is new. This setup does not move existing files automatically.

Run from the umbrella root:

```sh
python3 _shared/tools/workspace.py list
python3 _shared/tools/workspace.py check
python3 _shared/tools/workspace.py worktree app-name task-name \
  --base origin/staging --branch chore/task-name
python3 _shared/tools/workspace.py retire app-name task-name --dry-run
python3 _shared/tools/workspace.py refresh --dry-run
```

Choose the base from the owning repository's release policy; the registered
website exception uses `origin/main`. Fetch current refs from inside the app
checkout first. The helper installs portable AGENTS/Claude/Cursor guidance and
registers the task checkout under that app. It does not install dependencies,
copy secrets, publish branches, merge PRs, or grant release permission.

`retire` removes a finished task checkout and its registry entry. It never forces:
it stops if tracked files have uncommitted changes, and if untracked or ignored
files would be lost unless `--preserve` is given, which copies them to the task's
`output/<task>/retired-checkout/` first. Rebuildable folders such as `node_modules`
and `.next` leave with the checkout. The branch and the output folder are kept, so
commits stay reachable even when they were never pushed.

`refresh` fast-forwards each app's canonical `repo/` checkout to GitHub (name apps
to limit it). The guidance files the installer keeps uncommitted in a checkout would
make a plain `git pull` refuse, so `refresh` sets them aside, fast-forwards, and
installs them again. It never resets, stashes or merges: when Git refuses, for
example because a local edit conflicts, the checkout is put back exactly as it was
and reported. A checkout on a side branch is left alone unless `--switch-merged` is
given and GitHub (through the `gh` command) reports a merged pull request for that
branch; it then moves to the default branch and the local side branch is kept.
`refresh` does not install dependencies.

Run the checker at task start/completion and read the relocation index when
resuming old chats. It detects unexpected top-level entries, misplaced app files,
missing agent entry points, unregistered checkouts and broken Git worktree links.
Instructions and this checker detect mistakes; they do not prevent every possible
filesystem write or substitute for GitHub/provider permissions.

Offline tests: `python3 tools/test_workspace.py` from this directory. Standalone
and cloud app clones use the portable instructions installed by
`scripts/sync-agent-instructions.py`; they do not need this umbrella setup.
