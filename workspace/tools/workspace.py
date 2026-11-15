#!/usr/bin/env python3
"""List app repositories, check workspace layout, and create, retire and refresh checkouts."""
import argparse
import concurrent.futures
import contextlib
import filecmp
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
MARKER = '<!-- BEGIN WORKSPACE LAYOUT -->'
CLAUDE_IMPORT = '@AGENTS.md'
# Files the instruction installer owns in every checkout. It rewrites them on each sync.
MANAGED = ('AGENTS.md', 'CLAUDE.md', 'AGENT_ENVIRONMENTS.md', '.cursor/rules/workspace-layout.mdc')
# Ignored files that can be rebuilt, so retiring a checkout need not preserve them.
DISPOSABLE = {'node_modules', '.next', 'dist', 'build', '.turbo', 'coverage', '.vercel', '__pycache__',
              '.DS_Store', '.eslintcache', 'tsconfig.tsbuildinfo', 'next-env.d.ts', 'playwright-report',
              'test-results'}


def git(path, *args):
    result = subprocess.run(['git', '--no-optional-locks', '-C', str(path), *args],
                            capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr.strip())
    return result.stdout.strip()


def registry():
    return json.loads((ROOT / '_shared/workspace.json').read_text())


def save_registry(data):
    p = ROOT / '_shared/workspace.json'
    temp = p.with_suffix('.json.tmp')
    temp.write_text(json.dumps(data, indent=2) + '\n')
    temp.replace(p)


def safe_path(relative):
    p = ROOT / relative
    if not p.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('Path leaves this workspace: ' + str(relative))
    return p


def policy(repo, app):
    return Path(__file__).with_name('workspace-policy.md').read_text()


def installer():
    # Checkouts use the same portable installer as published app rules.
    import importlib.util
    path = Path(__file__).with_name('sync-agent-instructions.py')
    spec = importlib.util.spec_from_file_location('workspace_instruction_sync', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.TEMPLATES = Path(__file__).with_name('instruction-templates')
    return module


def install_policy(repo, app, quiet=False):
    module = installer()
    if quiet:
        with contextlib.redirect_stdout(io.StringIO()):
            module.sync(repo)
    else:
        module.sync(repo)


def has_ref(path, ref):
    return subprocess.run(['git', '--no-optional-locks', '-C', str(path), 'show-ref', '--verify', '--quiet', ref],
                          capture_output=True).returncode == 0


def without_import(text):
    return '\n'.join(line for line in text.splitlines() if line.strip() != CLAUDE_IMPORT).strip()


def installer_only(path, name, code):
    """True when a managed file differs from HEAD only by what the installer writes."""
    working = (path / name).read_bytes().decode(errors='replace')
    if code == '??':
        base = ''
    elif code == ' M':
        shown = subprocess.run(['git', '--no-optional-locks', '-C', str(path), 'show', 'HEAD:' + name],
                               capture_output=True)
        if shown.returncode:
            return False
        base = shown.stdout.decode(errors='replace')
    else:
        return False  # staged, deleted or conflicting: somebody's own work
    if name == 'AGENTS.md':
        try:
            module = installer()
            return module.remove_block(working).strip() == module.remove_block(base).strip()
        except ValueError:
            return False
    if name == 'CLAUDE.md':
        return without_import(working) == without_import(base)
    return True  # the installer replaces the other managed files wholesale


def local_state(path):
    """Split a checkout's local files into installer guidance, tracked changes, untracked and ignored files."""
    result = subprocess.run(['git', '--no-optional-locks', '-C', str(path), 'status', '--porcelain=v1', '-z',
                             '--untracked-files=all', '--ignored=matching'], capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr.strip())
    managed, changed, untracked, ignored = [], [], [], []
    tokens = result.stdout.split('\0')
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if len(token) < 4:
            continue
        code, name = token[:2], token[3:]
        if code[0] in 'RC':
            index += 1  # the original path of a rename or copy follows
        if code == '!!':
            if Path(name.rstrip('/')).name not in DISPOSABLE:
                ignored.append(name)
        elif name in MANAGED and installer_only(path, name, code):
            managed.append((name, code))
        elif code == '??':
            untracked.append(name)
        else:
            changed.append(code.strip() + ' ' + name)
    return managed, changed, untracked, ignored


def set_guidance_aside(path, managed):
    """Remove the installer's local files so Git sees a clean tree; return what is needed to put them back."""
    saved = {}
    for name, code in managed:
        saved[name] = (path / name).read_bytes()
        if code == '??':
            (path / name).unlink()
        else:
            git(path, 'checkout', '--', name)
    for folder in ('.cursor/rules', '.cursor'):
        candidate = path / folder
        if candidate.is_dir() and not any(candidate.iterdir()):
            candidate.rmdir()
    return saved


def put_guidance_back(path, saved):
    for name, content in saved.items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_bytes(content)


def discover_checkouts(data):
    found = []
    for app in data['apps']:
        container = safe_path(app)
        for sub in ['repo', 'worktrees', 'legacy-clones']:
            start = container / sub
            if not start.exists():
                continue
            for base, dirs, files in os.walk(start):
                p = Path(base)
                if (p / '.git').exists():
                    found.append(p)
                    dirs[:] = []
                else:
                    dirs[:] = [d for d in dirs if d not in {'node_modules', '.git', '.next', '.local', 'dist', 'build'}]
    return found


def inspect_checkout(row):
    errors = []
    try:
        p = safe_path(row['path'])
        if not (p / '.git').exists():
            return ['Missing checkout: ' + row['path']]
        top = Path(git(p, 'rev-parse', '--show-toplevel')).resolve()
        if top != p.resolve():
            errors.append('Incorrect Git root: ' + row['path'])
        common = Path(git(p, 'rev-parse', '--path-format=absolute', '--git-common-dir')).resolve()
        if common != safe_path(row['common']).resolve():
            errors.append('Incorrect Git common directory: ' + row['path'])
        if row['kind'] == 'worktree':
            admin = Path(git(p, 'rev-parse', '--absolute-git-dir'))
            back = (admin / 'gitdir').read_text().strip()
            if Path(back).resolve() != (p / '.git').resolve():
                errors.append('Broken worktree backlink: ' + row['path'])
        guide = p / 'AGENTS.md'
        if not guide.exists() or MARKER not in guide.read_text():
            errors.append('Missing workspace instructions: ' + row['path'])
        if not (p / '.cursor/rules/workspace-layout.mdc').exists():
            errors.append('Missing Cursor folder rule: ' + row['path'])
        claude = p / 'CLAUDE.md'
        if not claude.exists() or CLAUDE_IMPORT not in claude.read_text().splitlines():
            errors.append('Missing Claude Code AGENTS.md import: ' + row['path'])
    except (OSError, ValueError) as exc:
        errors.append(row['path'] + ': ' + str(exc))
    return errors


def check(data=None):
    data = data or registry()
    errors = []
    allowed = set(data['apps']) | set(data['root_entries'])
    for p in ROOT.iterdir():
        if p.name not in allowed:
            errors.append('Unexpected workspace-root entry: ' + p.name)
    allowed_children = {'repo', 'worktrees', 'output', 'legacy-clones', 'README.md', 'AGENTS.md', 'CLAUDE.md', '.DS_Store'}
    for app, info in data['apps'].items():
        container = safe_path(app)
        if not container.is_dir():
            errors.append('Missing app container: ' + app)
            continue
        for p in container.iterdir():
            if p.name not in allowed_children:
                errors.append('Misplaced app-container entry: ' + str(p.relative_to(ROOT)))
        if info['repo'] and not (safe_path(info['repo']) / '.git').exists():
            errors.append('Missing canonical repository: ' + info['repo'])
    expected = {r['path'] for r in data['checkouts']}
    actual = {str(p.relative_to(ROOT)) for p in discover_checkouts(data)}
    errors += ['Unregistered checkout: ' + p for p in sorted(actual - expected)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for issues in pool.map(inspect_checkout, data['checkouts']):
            errors.extend(issues)
    commons = {str(safe_path(r['common']).parent) for r in data['checkouts']}
    for repo in commons:
        try:
            listing = git(repo, 'worktree', 'list', '--porcelain')
            for block in listing.split('\n\n'):
                lines = block.splitlines()
                if not lines:
                    continue
                path = lines[0].removeprefix('worktree ')
                if not Path(path).exists() or any(s.startswith('prunable ') for s in lines):
                    errors.append('Stale Git worktree registration: ' + path)
        except ValueError as exc:
            errors.append(str(exc))
    return errors


def create_worktree(args):
    data = registry()
    if args.app not in data['apps'] or not data['apps'][args.app]['repo']:
        raise ValueError('Choose a registered app with a repository (run list).')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', args.task):
        raise ValueError('Task name must contain 1–64 lowercase letters, digits or hyphens.')
    repo = safe_path(data['apps'][args.app]['repo'])
    destination = safe_path(str(Path(args.app) / 'worktrees' / args.task))
    if args.branch.startswith('-') or args.base.startswith('-'):
        raise ValueError('Branch and base cannot start with a hyphen.')
    git(repo, 'check-ref-format', '--branch', args.branch)
    base = git(repo, 'rev-parse', '--verify', '--end-of-options', args.base + '^{commit}')
    if destination.exists():
        common = git(destination, 'rev-parse', '--path-format=absolute', '--git-common-dir')
        if Path(common).resolve() != (repo / '.git').resolve():
            raise ValueError('Existing destination belongs to a different repository.')
        branch = git(destination, 'symbolic-ref', '--short', 'HEAD')
        if branch != args.branch:
            raise ValueError('Existing destination uses branch ' + branch)
        print('Reusing ' + str(destination))
    elif args.dry_run:
        print(json.dumps({'repository': str(repo), 'worktree': str(destination),
                          'branch': args.branch, 'base_commit': base,
                          'output': str(ROOT / args.app / 'output' / args.task)}, indent=2))
        return
    else:
        errors = check(data)
        if errors:
            raise ValueError('Fix workspace check errors first:\n' + '\n'.join(errors))
        destination.parent.mkdir(parents=True, exist_ok=True)
        git(repo, 'worktree', 'add', '-b', args.branch, str(destination), base)
        print('Created ' + str(destination))
    if args.dry_run:
        return
    install_policy(destination, args.app)
    (ROOT / args.app / 'output' / args.task).mkdir(parents=True, exist_ok=True)
    rel = str(destination.relative_to(ROOT))
    if rel not in {r['path'] for r in data['checkouts']}:
        data['checkouts'].append({'path': rel, 'app': args.app, 'kind': 'worktree',
                                 'common': str((repo / '.git').relative_to(ROOT))})
        save_registry(data)


def preserve(path, store, untracked, ignored):
    """Copy files Git does not hold into the task's output folder, then clear the untracked ones."""
    if store.exists() and any(store.iterdir()):
        raise ValueError('Preservation folder already has content: ' + str(store))
    for name in untracked + ignored:
        source = path / name.rstrip('/')
        destination = store / name.rstrip('/')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir() and not source.is_symlink():
            shutil.copytree(source, destination, symlinks=True)
        else:
            shutil.copy2(source, destination, follow_symlinks=False)
            if not source.is_symlink() and not filecmp.cmp(source, destination, shallow=False):
                raise ValueError('Copy differs from the original: ' + name)
    # Ignored files leave with the worktree; untracked ones would make Git refuse the removal.
    for name in untracked:
        source = path / name
        source.unlink()
        parent = source.parent
        while parent != path and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent


def retire_worktree(args):
    data = registry()
    rel = str(Path(args.app) / 'worktrees' / args.task)
    row = next((r for r in data['checkouts'] if r['path'] == rel), None)
    if not row or row['kind'] != 'worktree':
        raise ValueError('Not a registered task worktree: ' + rel)
    path = safe_path(rel)
    repo = safe_path(row['common']).parent
    if not (path / '.git').is_file():
        raise ValueError('Missing checkout, or not a linked worktree: ' + rel)
    managed, changed, untracked, ignored = local_state(path)
    try:
        branch = git(path, 'symbolic-ref', '--short', 'HEAD')
    except ValueError:
        branch = None
        if not git(path, 'branch', '--all', '--contains', 'HEAD'):
            raise ValueError('HEAD is detached and on no branch. Create a branch first so its commits are kept.')
    local_only = len(git(path, 'rev-list', 'HEAD', '--not', '--remotes').splitlines())
    if changed:
        raise ValueError('Uncommitted changes to tracked files. Commit or discard them yourself first:\n  '
                         + '\n  '.join(changed[:20]))
    if (untracked or ignored) and not args.preserve:
        raise ValueError('Files Git does not hold would be lost. Move them, or rerun with --preserve to copy '
                         'them into the task output folder:\n  ' + '\n  '.join((untracked + ignored)[:20]))
    store = safe_path(str(Path(args.app) / 'output' / args.task / 'retired-checkout'))
    plan = {'worktree': str(path), 'branch_kept': branch or '(detached; commits are on another branch)',
            'commits_only_on_this_computer': local_only,
            'installer_files_removed': [name for name, _ in managed],
            'preserved_to': str(store) if (untracked or ignored) else None,
            'preserved': untracked + ignored}
    if args.dry_run:
        print(json.dumps(plan, indent=2))
        return
    if untracked or ignored:
        preserve(path, store, untracked, ignored)
    saved = set_guidance_aside(path, managed)
    try:
        git(repo, 'worktree', 'remove', str(path))
    except ValueError as exc:
        put_guidance_back(path, saved)
        raise ValueError('Git refused to remove the worktree, so it was left in place: ' + ' '.join(str(exc).split()))
    data['checkouts'] = [r for r in data['checkouts'] if r['path'] != rel]
    save_registry(data)
    print('Retired ' + rel + (f'; branch {branch} is kept' if branch else '')
          + (f' ({local_only} commit(s) exist only on this computer)' if local_only else '')
          + (f'; {len(untracked + ignored)} file(s) preserved in {store}' if (untracked or ignored) else ''))


def default_branch(path):
    try:
        return git(path, 'symbolic-ref', '--short', 'refs/remotes/origin/HEAD').split('/', 1)[1]
    except (ValueError, IndexError):
        pass
    for name in ('main', 'staging'):
        if has_ref(path, 'refs/remotes/origin/' + name):
            return name
    return None


def merged_pull_request(path, branch):
    """True when GitHub reports a merged pull request from this branch. Needs the gh command."""
    found = re.search(r'github\.com[:/](.+?)(?:\.git)?$', git(path, 'remote', 'get-url', 'origin'))
    if not found:
        return False
    try:
        result = subprocess.run(['gh', 'pr', 'list', '--repo', found.group(1), '--head', branch, '--state', 'merged',
                                 '--json', 'number', '--limit', '1'], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip() not in ('', '[]')


def refresh_checkout(app, path, switch_merged=False, dry_run=False):
    """Fast-forward one canonical checkout. Returns a one-line outcome; never discards local work."""
    try:
        git(path, 'remote', 'get-url', 'origin')
    except ValueError:
        return 'left: no origin remote'
    git(path, 'fetch', '--quiet', 'origin')
    try:
        branch = git(path, 'symbolic-ref', '--short', 'HEAD')
    except ValueError:
        return 'left: HEAD is detached'
    target = branch
    base = default_branch(path)
    side_branch = branch not in ('main', 'staging') and branch != base
    if side_branch and switch_merged and base and merged_pull_request(path, branch):
        target = base
    elif not has_ref(path, 'refs/remotes/origin/' + branch):
        return f'left: branch {branch} is not on GitHub' + (
            ' and has no merged pull request' if switch_merged else '; --switch-merged moves it to '
            + (base or 'the default branch') + ' when its pull request was merged')
    behind = int(git(path, 'rev-list', '--count', 'HEAD..origin/' + target))
    ahead = int(git(path, 'rev-list', '--count', 'origin/' + target + '..HEAD'))
    if target == branch and behind == 0:
        return f'already level with origin/{branch}' + (f' ({ahead} unpushed commit(s))' if ahead else '')
    step = (f'switch from {branch} to {target} and ' if target != branch else '') + f'fast-forward {behind} commit(s)'
    if dry_run:
        return 'would ' + step
    managed, _, _, _ = local_state(path)
    before = git(path, 'rev-parse', '--short', 'HEAD')
    saved = set_guidance_aside(path, managed)
    switched = False
    try:
        if target != branch:
            if has_ref(path, 'refs/heads/' + target):
                git(path, 'switch', '--quiet', target)
            else:
                git(path, 'switch', '--quiet', '--create', target, '--track', 'origin/' + target)
            switched = True
        git(path, 'merge', '--quiet', '--ff-only', 'origin/' + target)
    except ValueError as exc:
        if switched:
            git(path, 'switch', '--quiet', branch)
        put_guidance_back(path, saved)
        return 'left as it was: Git refused to ' + step + ' (' + ' '.join(str(exc).split())[:240] + ')'
    install_policy(path, app, quiet=True)
    return f'updated {branch}@{before} -> {target}@' + git(path, 'rev-parse', '--short', 'HEAD') + (
        f'; local branch {branch} is kept' if target != branch else '')


def refresh(args):
    data = registry()
    unknown = [a for a in args.apps if a not in data['apps']]
    if unknown:
        raise ValueError('Not a registered app: ' + ', '.join(unknown))
    for app in args.apps or list(data['apps']):
        info = data['apps'][app]
        if not info['repo']:
            outcome = 'left: no repository registered'
        else:
            try:
                outcome = refresh_checkout(app, safe_path(info['repo']), args.switch_merged, args.dry_run)
            except (OSError, ValueError) as exc:
                outcome = 'left: ' + ' '.join(str(exc).split())[:240]
        print(app + ': ' + outcome)


def main():
    global ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, help='Workspace root (defaults to this script’s workspace).')
    subs = parser.add_subparsers(dest='command', required=True)
    subs.add_parser('check', help='Read-only structural and Git-link verification.')
    subs.add_parser('list', help='Print canonical repository locations.')
    locate = subs.add_parser('locate', help='Find the new location of an old workspace path.')
    locate.add_argument('path')
    worktree = subs.add_parser('worktree', help='Create/reuse a task checkout without installing dependencies.')
    worktree.add_argument('app')
    worktree.add_argument('task')
    worktree.add_argument('--base', required=True, help='Existing local ref; obey the repository release policy.')
    worktree.add_argument('--branch', required=True)
    worktree.add_argument('--dry-run', action='store_true')
    retire = subs.add_parser('retire', help='Remove a finished task checkout and its registry entry; never forced.')
    retire.add_argument('app')
    retire.add_argument('task')
    retire.add_argument('--preserve', action='store_true',
                        help='Copy untracked and ignored files to the task output folder first.')
    retire.add_argument('--dry-run', action='store_true')
    refresh_parser = subs.add_parser('refresh', help='Fast-forward canonical repo checkouts to GitHub.')
    refresh_parser.add_argument('apps', nargs='*', help='Apps to refresh (default: every app).')
    refresh_parser.add_argument('--switch-merged', action='store_true',
                                help='Move a checkout whose side branch has a merged pull request to the default branch.')
    refresh_parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if args.root:
        ROOT = args.root.resolve()
    try:
        data = registry()
        if args.command == 'check':
            errors = check(data)
            for error in errors:
                print('ERROR: ' + error)
            if not errors:
                print(f"PASS: {len(data['apps'])} app containers, {len(data['checkouts'])} Git checkouts; layout and Git links valid.")
            return 1 if errors else 0
        if args.command == 'list':
            for app, info in data['apps'].items():
                print(app + ': ' + (str(ROOT / info['repo']) if info['repo'] else '(empty placeholder)'))
        elif args.command == 'locate':
            p = Path(args.path)
            rel = p.relative_to(ROOT) if p.is_absolute() else p
            for row in sorted(data['relocations'], key=lambda r: len(Path(r['old']).parts), reverse=True):
                try:
                    suffix = rel.relative_to(row['old'])
                except ValueError:
                    continue
                print(safe_path(str(Path(row['new']) / suffix)))
                return 0
            print(safe_path(str(rel)))
        elif args.command == 'worktree':
            create_worktree(args)
        elif args.command == 'retire':
            retire_worktree(args)
        elif args.command == 'refresh':
            refresh(args)
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
