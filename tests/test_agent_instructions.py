"""Exercise real instruction installs while preserving repository-specific policy."""
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('agent_sync', ROOT / 'scripts/sync-agent-instructions.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
spec = importlib.util.spec_from_file_location('release_sync', ROOT / 'scripts/sync-release-policy.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class AgentInstructionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def sync(self, check=False):
        with contextlib.redirect_stdout(io.StringIO()):
            return tool.sync(self.root, check)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file() and not p.is_symlink()}

    def test_standalone_install_preserves_guidance_and_is_idempotent(self):
        (self.root / 'AGENTS.md').write_text('# App instructions\nKeep custom build steps.\n')
        (self.root / 'CLAUDE.md').write_text('Custom Claude instructions.\n')
        self.sync()
        self.assertIn('Keep custom build steps.', (self.root / 'AGENTS.md').read_text())
        self.assertIn('standalone or cloud clone', (self.root / 'AGENTS.md').read_text())
        self.assertTrue((self.root / 'CLAUDE.md').read_text().startswith('Custom Claude instructions.'))
        self.assertTrue(tool.has_import((self.root / 'CLAUDE.md').read_text()))
        before = self.snapshot()
        self.assertEqual(self.sync(check=True), 0)
        self.sync()
        self.assertEqual(self.snapshot(), before)

    def test_check_reports_drift_without_writes(self):
        self.assertEqual(self.sync(check=True), 1)
        self.assertEqual(self.snapshot(), {})
        self.sync()
        (self.root / 'CLAUDE.md').write_text('Only a fenced example:\n```md\n@AGENTS.md\n```\n')
        before = self.snapshot()
        self.assertEqual(self.sync(check=True), 1)
        self.assertEqual(before, self.snapshot())
        self.sync()
        self.assertTrue((self.root / 'CLAUDE.md').read_text().endswith('\n@AGENTS.md\n'))

    def test_existing_release_blocks_and_website_exception_survive(self):
        for repository in ['meavo-booths/app', 'meavo-booths/office-phone-booths-uk']:
            with self.subTest(repository=repository):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    with contextlib.redirect_stdout(io.StringIO()):
                        release.sync(root, repository=repository)
                    block = release.verifier().managed_block((root / 'AGENTS.md').read_text())
                    # Simulate the old local migration helper's prefix/import.
                    p = root / 'AGENTS.md'
                    p.write_text(tool.BEGIN + '\nOld ../../../ paths\n' + tool.END + '\n\n' + p.read_text())
                    p = root / 'CLAUDE.md'
                    p.write_text('@AGENTS.md\n\n' + p.read_text())
                    with contextlib.redirect_stdout(io.StringIO()):
                        tool.sync(root)
                    self.assertTrue((root / 'AGENTS.md').read_text().startswith(block))
                    self.assertNotIn('../../../', (root / 'AGENTS.md').read_text())
                    self.assertEqual(release.verifier().verify(root), [])
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(release.sync(root, check=True, repository=repository), 0)

    def test_malformed_workspace_block_is_rejected_without_partial_writes(self):
        for content in [tool.BEGIN, tool.END, tool.END + '\n' + tool.BEGIN,
                        tool.BEGIN + tool.END + tool.BEGIN + tool.END]:
            (self.root / 'AGENTS.md').write_text(content)
            before = self.snapshot()
            with self.assertRaises(ValueError):
                self.sync()
            self.assertEqual(before, self.snapshot())

    def test_destination_symlink_is_rejected_before_any_write(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / '.cursor').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                self.sync()
            self.assertEqual(self.snapshot(), {})
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_bootstrap_keeps_existing_claude_notes_and_release_verification(self):
        (self.root / 'CLAUDE.md').write_text('Keep custom Claude notes.\n')
        result = subprocess.run(['bash', str(ROOT / 'scripts/bootstrap-agent-docs.sh'), str(self.root)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Keep custom Claude notes.', (self.root / 'CLAUDE.md').read_text())
        self.assertEqual(self.sync(check=True), 0)
        self.assertEqual(release.verifier().verify(self.root), [])


class CanonicalInstallationTests(unittest.TestCase):
    def test_repository_matches_portable_agent_templates(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(tool.sync(ROOT, check=True), 0)

    def test_packaged_workspace_installer_and_templates_match(self):
        self.assertEqual((ROOT / 'scripts/sync-agent-instructions.py').read_bytes(),
                         (ROOT / 'workspace/tools/sync-agent-instructions.py').read_bytes())
        for name in ('AGENTS.workspace.md.template', 'AGENT_ENVIRONMENTS.md.template',
                     '.cursor/rules/workspace-layout.mdc.template'):
            self.assertEqual((ROOT / 'templates' / name).read_bytes(),
                             (ROOT / 'workspace/tools/instruction-templates' / name).read_bytes())


if __name__ == '__main__':
    unittest.main()
