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

    # --- retire ---------------------------------------------------------

    def worktree(self):
        self.assertEqual(self.create().returncode, 0)
        return self.root / 'meavo-assembly/worktrees/sample-task'

    def test_retire_removes_checkout_and_registry_row_but_keeps_branch_and_output(self):
        p = self.worktree()
        (p / 'feature.txt').write_text('work\n')
        workspace.git(p, 'add', 'feature.txt')
        workspace.git(p, 'commit', '-m', 'Task work')
        result = self.cli('retire', 'meavo-assembly', 'sample-task')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(p.exists())
        self.assertEqual(len(workspace.registry()['checkouts']), 1)
        self.assertEqual(workspace.check(), [])
        self.assertIn('feat/sample-task', workspace.git(self.repo, 'branch', '--list', 'feat/sample-task'))
        self.assertTrue((self.root / 'meavo-assembly/output/sample-task').is_dir())

    def test_retire_dry_run_changes_nothing(self):
        p = self.worktree()
        result = self.cli('retire', 'meavo-assembly', 'sample-task', '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((p / 'AGENTS.md').exists())
        self.assertEqual(len(workspace.registry()['checkouts']), 2)

    def test_retire_refuses_to_lose_uncommitted_untracked_or_ignored_files(self):
        p = self.worktree()
        (p / 'README.md').write_text('edited\n')
        refused = self.cli('retire', 'meavo-assembly', 'sample-task', '--preserve')
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn('README.md', refused.stderr)
        workspace.git(p, 'checkout', '--', 'README.md')
        (p / 'notes.txt').write_text('keep me\n')
        (p / '.gitignore').write_text('.env\nnode_modules/\n')
        workspace.git(p, 'add', '.gitignore')
        workspace.git(p, 'commit', '-m', 'Ignore rules')
        (p / '.env').write_text('SECRET=1\n')
        (p / 'node_modules').mkdir()
        (p / 'node_modules/pkg.js').write_text('rebuildable\n')
        refused = self.cli('retire', 'meavo-assembly', 'sample-task')
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn('notes.txt', refused.stderr)
        self.assertIn('.env', refused.stderr)
        self.assertNotIn('node_modules', refused.stderr)
        self.assertTrue((p / 'notes.txt').exists())
        self.assertEqual(workspace.check(), [])

    def test_retire_with_preserve_copies_files_to_the_task_output(self):
        p = self.worktree()
        (p / '.gitignore').write_text('.env\n')
        workspace.git(p, 'add', '.gitignore')
        workspace.git(p, 'commit', '-m', 'Ignore rules')
        (p / 'docs').mkdir()
        (p / 'docs/notes.txt').write_text('keep me\n')
        (p / '.env').write_text('SECRET=1\n')
        result = self.cli('retire', 'meavo-assembly', 'sample-task', '--preserve')
        self.assertEqual(result.returncode, 0, result.stderr)
        store = self.root / 'meavo-assembly/output/sample-task/retired-checkout'
        self.assertEqual((store / 'docs/notes.txt').read_text(), 'keep me\n')
        self.assertEqual((store / '.env').read_text(), 'SECRET=1\n')
        self.assertFalse(p.exists())
        self.assertEqual(workspace.check(), [])

    def test_retire_rejects_unknown_tasks_and_the_canonical_repository(self):
        self.assertNotEqual(self.cli('retire', 'meavo-assembly', 'missing-task').returncode, 0)
        self.assertNotEqual(self.cli('retire', 'meavo-assembly', '../repo').returncode, 0)
        self.assertTrue((self.repo / '.git').exists())

    # --- refresh --------------------------------------------------------

    def remote(self):
        """Give the fixture a bare origin plus a second clone that plays GitHub."""
        self.outside = tempfile.TemporaryDirectory(prefix='workspace-remote-test-')
        self.addCleanup(self.outside.cleanup)
        origin = Path(self.outside.name) / 'origin.git'
        subprocess.run(['git', 'init', '--bare', '-b', 'staging', str(origin)], check=True, capture_output=True)
        workspace.git(self.repo, 'remote', 'add', 'origin', str(origin))
        workspace.git(self.repo, 'push', '--quiet', '-u', 'origin', 'staging')
        other = Path(self.outside.name) / 'other'
        subprocess.run(['git', 'clone', '--quiet', str(origin), str(other)], check=True, capture_output=True)
        workspace.git(other, 'config', 'user.name', 'Workspace Test')
        workspace.git(other, 'config', 'user.email', 'workspace-test@example.invalid')
        return other

    def publish(self, other, name, text, message='Upstream change'):
        (other / name).write_text(text)
        workspace.git(other, 'add', name)
        workspace.git(other, 'commit', '-m', message)
        workspace.git(other, 'push', '--quiet', 'origin', 'HEAD')

    def test_refresh_fast_forwards_past_installer_files_and_reinstalls_them(self):
        other = self.remote()
        # Upstream does not carry the workspace guidance; locally the installer adds it uncommitted.
        for name in ('CLAUDE.md', 'AGENT_ENVIRONMENTS.md', '.cursor/rules/workspace-layout.mdc'):
            workspace.git(other, 'rm', '--quiet', name)
        (other / 'AGENTS.md').write_text('# App guide\n')
        workspace.git(other, 'add', 'AGENTS.md')
        workspace.git(other, 'commit', '-m', 'Plain guide')
        workspace.git(other, 'push', '--quiet', 'origin', 'HEAD')
        self.assertIn('updated', self.cli('refresh', 'meavo-assembly').stdout)
        self.assertIn(' M AGENTS.md', subprocess.run(['git', '-C', str(self.repo), 'status', '--porcelain'],
                                                     capture_output=True, text=True).stdout)
        self.publish(other, 'AGENTS.md', '# App guide\nMore upstream text.\n')
        self.publish(other, 'CLAUDE.md', '# Upstream Claude notes\n')
        result = self.cli('refresh', 'meavo-assembly')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('updated', result.stdout)
        self.assertEqual(workspace.git(self.repo, 'rev-parse', 'HEAD'), workspace.git(other, 'rev-parse', 'HEAD'))
        guide = (self.repo / 'AGENTS.md').read_text()
        self.assertIn('More upstream text.', guide)
        self.assertIn(workspace.MARKER, guide)
        self.assertIn('# Upstream Claude notes', (self.repo / 'CLAUDE.md').read_text())
        self.assertEqual(workspace.check(), [])
        self.assertIn('already level', self.cli('refresh').stdout)

    def test_refresh_leaves_checkout_untouched_when_local_work_conflicts(self):
        other = self.remote()
        self.publish(other, 'README.md', 'upstream\n')
        (self.repo / 'README.md').write_text('my local edit\n')
        before = workspace.git(self.repo, 'rev-parse', 'HEAD')
        dry = self.cli('refresh', '--dry-run')
        self.assertIn('would fast-forward 1 commit', dry.stdout)
        result = self.cli('refresh')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('left as it was', result.stdout)
        self.assertEqual(workspace.git(self.repo, 'rev-parse', 'HEAD'), before)
        self.assertEqual((self.repo / 'README.md').read_text(), 'my local edit\n')
        self.assertEqual(workspace.check(), [])

    def test_refresh_only_leaves_a_side_branch_when_its_pull_request_is_merged(self):
        other = self.remote()
        self.publish(other, 'README.md', 'upstream\n')
        workspace.git(self.repo, 'switch', '--quiet', '-c', 'feat/old-task')
        (self.repo / 'task.txt').write_text('task\n')
        workspace.git(self.repo, 'add', 'task.txt')
        workspace.git(self.repo, 'commit', '-m', 'Old task')
        self.assertIn('left: branch feat/old-task is not on GitHub', self.cli('refresh').stdout)
        self.assertEqual(workspace.git(self.repo, 'symbolic-ref', '--short', 'HEAD'), 'feat/old-task')
        original = workspace.merged_pull_request
        try:
            workspace.merged_pull_request = lambda path, branch: False
            self.assertIn('no merged pull request', workspace.refresh_checkout('meavo-assembly', self.repo, True))
            workspace.merged_pull_request = lambda path, branch: branch == 'feat/old-task'
            outcome = workspace.refresh_checkout('meavo-assembly', self.repo, True)
        finally:
            workspace.merged_pull_request = original
        self.assertIn('local branch feat/old-task is kept', outcome)
        self.assertEqual(workspace.git(self.repo, 'symbolic-ref', '--short', 'HEAD'), 'staging')
        self.assertEqual((self.repo / 'README.md').read_text(), 'upstream\n')
        self.assertIn('feat/old-task', workspace.git(self.repo, 'branch', '--list', 'feat/old-task'))
        self.assertEqual(workspace.check(), [])

    def test_local_edits_inside_managed_files_are_not_treated_as_installer_output(self):
        guide = self.repo / 'AGENTS.md'
        guide.write_text(guide.read_text() + '\nMy own unpublished rule.\n')
        managed, changed, untracked, ignored = workspace.local_state(self.repo)
        self.assertEqual(managed, [])
        self.assertEqual(changed, ['M AGENTS.md'])


if __name__ == '__main__':
    unittest.main()
