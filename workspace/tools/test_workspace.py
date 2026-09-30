#!/usr/bin/env python3
"""Offline integration tests using disposable Git repositories, never app data."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('workspace.py')
spec = importlib.util.spec_from_file_location('workspace', SCRIPT)
workspace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workspace)


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='workspace-layout-test-')
        self.root = Path(self.temp.name).resolve()
        workspace.ROOT = self.root
        self.repo = self.root / 'meavo-assembly/repo'
        self.repo.mkdir(parents=True)
        (self.root / '_shared').mkdir()
        subprocess.run(['git', 'init', '-b', 'staging', str(self.repo)], check=True, capture_output=True)
        workspace.git(self.repo, 'config', 'user.name', 'Workspace Test')
        workspace.git(self.repo, 'config', 'user.email', 'workspace-test@example.invalid')
        (self.repo / 'README.md').write_text('fixture\n')
        workspace.install_policy(self.repo, 'meavo-assembly')
        workspace.git(self.repo, 'add', '.')
        workspace.git(self.repo, 'commit', '-m', 'Local test fixture')
        workspace.save_registry({'apps': {'meavo-assembly': {'repo': 'meavo-assembly/repo'}},
                                 'root_entries': ['_shared'],
                                 'checkouts': [{'path': 'meavo-assembly/repo', 'app': 'meavo-assembly',
                                                'kind': 'repository', 'common': 'meavo-assembly/repo/.git'}],
                                 'relocations': [{'old': 'assembly-old', 'new': 'meavo-assembly/repo'}]})

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, *args):
        return subprocess.run(['python3', str(SCRIPT), '--root', str(self.root), *args], capture_output=True, text=True)

    def create(self, *extra):
        return self.cli('worktree', 'meavo-assembly', 'sample-task', '--base', 'staging',
                        '--branch', 'feat/sample-task', *extra)

    def test_create_and_reuse_keeps_everything_in_app(self):
        result = self.create()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / 'meavo-assembly/worktrees/sample-task/.git').is_file())
        self.assertTrue((self.root / 'meavo-assembly/output/sample-task').is_dir())
        self.assertEqual(workspace.check(), [])
        again = self.create()
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(len(workspace.registry()['checkouts']), 2)

    def test_dry_run_and_old_path_lookup_are_read_only(self):
        result = self.create('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / 'meavo-assembly/worktrees').exists())
        translated = self.cli('locate', 'assembly-old/README.md')
        self.assertEqual(translated.stdout.strip(), str(self.repo / 'README.md'))

    def test_root_clutter_blocks_creation(self):
        (self.root / 'package.json').write_text('{}')
        self.assertTrue(any('package.json' in e for e in workspace.check()))
        self.assertNotEqual(self.create().returncode, 0)

    def test_invalid_task_and_symlink_escape_are_rejected(self):
        invalid = self.cli('worktree', 'meavo-assembly', '../escape', '--base', 'staging', '--branch', 'feat/escape')
        self.assertNotEqual(invalid.returncode, 0)
        with tempfile.TemporaryDirectory() as outside:
            (self.root / 'meavo-assembly/worktrees').symlink_to(outside)
            self.assertNotEqual(self.create().returncode, 0)

    def test_wrong_existing_branch_does_not_get_reused(self):
        self.assertEqual(self.create().returncode, 0)
        result = self.cli('worktree', 'meavo-assembly', 'sample-task', '--base', 'staging', '--branch', 'fix/other')
        self.assertNotEqual(result.returncode, 0)

    def test_missing_policy_and_broken_link_are_detected(self):
        self.assertEqual(self.create().returncode, 0)
        p = self.root / 'meavo-assembly/worktrees/sample-task'
        (p / 'AGENTS.md').unlink()
        self.assertTrue(any('instructions' in e for e in workspace.check()))
        admin = Path(workspace.git(p, 'rev-parse', '--absolute-git-dir'))
        (admin / 'gitdir').write_text(str(self.root / 'missing/.git'))
        self.assertTrue(any('backlink' in e or 'Stale' in e for e in workspace.check()))

    def test_claude_import_is_installed_and_existing_guidance_preserved(self):
        guide = self.repo / 'CLAUDE.md'
        guide.write_text('# Existing release rules\nKeep human release approval.\n')
        self.assertTrue(any('Claude Code' in e for e in workspace.check()))
        workspace.install_policy(self.repo, 'meavo-assembly')
        self.assertEqual(guide.read_text(), '# Existing release rules\nKeep human release approval.\n\n@AGENTS.md\n')
        workspace.install_policy(self.repo, 'meavo-assembly')
        self.assertEqual(guide.read_text().count('@AGENTS.md'), 1)
        self.assertEqual(workspace.check(), [])


if __name__ == '__main__':
    unittest.main()
