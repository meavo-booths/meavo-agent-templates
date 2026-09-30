#!/usr/bin/env python3
"""List app repositories, check workspace layout, and create correctly placed worktrees."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
MARKER = '<!-- BEGIN WORKSPACE LAYOUT -->'
CLAUDE_IMPORT = '@AGENTS.md'


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


def install_policy(repo, app):
    # New checkouts use the same portable installer as published app rules.
    import importlib.util
    installer = Path(__file__).with_name('sync-agent-instructions.py')
    spec = importlib.util.spec_from_file_location('workspace_instruction_sync', installer)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.TEMPLATES = Path(__file__).with_name('instruction-templates')
    module.sync(repo)


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
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
