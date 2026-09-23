"""Dependency-free regression checks for safe propagation and release gates."""

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sync_release_policy", ROOT / "scripts/sync-release-policy.py")
sync_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_tool)
policy = sync_tool.verifier()


class ReleasePolicyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def sync(self, check=False):
        with contextlib.redirect_stdout(io.StringIO()):
            return sync_tool.sync(self.root, check)

    def snapshot(self):
        return {str(path.relative_to(self.root)): path.read_bytes()
                for path in self.root.rglob("*") if path.is_file()}

    def event(self, event, name="pull_request"):
        path = self.root / "event.json"
        path.write_text(json.dumps(event))
        return policy.verify_event(path, name)

    def pull_request(self, base="main", head="staging", repository="meavo-booths/app"):
        return {"repository": {"full_name": "meavo-booths/app"}, "pull_request": {
            "base": {"ref": base, "repo": {"full_name": "meavo-booths/app"}},
            "head": {"ref": head, "repo": {"full_name": repository}},
        }}

    def test_sync_preserves_project_docs_and_is_idempotent(self):
        originals = {
            "AGENTS.md": b"# Project rules\r\n\r\nKeep the custom build steps.\r\n",
            "CLAUDE.md": b"@AGENTS.md\n\nCustom Claude instructions.\n",
            "CONTRIBUTING.md": b"# Contributing\n\nRun the app-specific tests.\n",
        }
        for name, content in originals.items():
            (self.root / name).write_bytes(content)
        self.assertEqual(self.sync(), 0)
        for name, content in originals.items():
            installed = (self.root / name).read_bytes()
            self.assertTrue(installed.startswith(policy.BEGIN.encode()))
            self.assertTrue(installed.endswith(content))
        first = self.snapshot()
        self.assertEqual(self.sync(), 0)
        self.assertEqual(self.snapshot(), first)
        self.assertEqual(self.sync(check=True), 0)
        self.assertEqual(policy.verify(self.root), [])

    def test_missing_installation_check_fails_without_writing(self):
        self.assertEqual(self.sync(check=True), 1)
        self.assertEqual(self.snapshot(), {})
        self.assertTrue(policy.verify(self.root))

    def test_sync_repairs_policy_and_managed_blocks_only(self):
        self.sync()
        path = self.root / "AGENTS.md"
        path.write_text(path.read_text().replace("\n", "\nLOCAL DRIFT\n", 1) + "\nKeep this project appendix.\n")
        (self.root / "RELEASE_POLICY.md").write_text("Outdated rules\n")
        before = self.snapshot()
        self.assertEqual(self.sync(check=True), 1)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(policy.verify(self.root))
        self.assertEqual(self.sync(), 0)
        self.assertEqual(policy.verify(self.root), [])
        self.assertTrue(path.read_text().endswith("\nKeep this project appendix.\n"))

    def test_each_required_file_and_pointer_is_enforced(self):
        self.sync()
        for name in (*policy.FILES, *policy.BLOCKS):
            with self.subTest(name=name):
                path = self.root / name
                original = path.read_bytes()
                path.unlink()
                self.assertTrue(policy.verify(self.root))
                path.write_bytes(original)
        manifest_path = self.root / policy.MANIFEST
        manifest = json.loads(manifest_path.read_text())
        del manifest["files"]["RELEASE_POLICY.md"]
        manifest_path.write_text(json.dumps(manifest))
        self.assertTrue(policy.verify(self.root), "removing a required manifest entry must not disable its check")

    def test_duplicate_or_partial_block_fails_before_mutation(self):
        for content in (policy.BEGIN, policy.END,
                        f"{policy.BEGIN}\nold\n{policy.END}\n{policy.BEGIN}\nold\n{policy.END}"):
            with self.subTest(content=content):
                (self.root / "AGENTS.md").write_text(content)
                original = self.snapshot()
                with self.assertRaises(ValueError):
                    self.sync()
                self.assertEqual(self.snapshot(), original)

    def test_block_cannot_be_buried_below_conflicting_instructions(self):
        self.sync()
        path = self.root / "AGENTS.md"
        path.write_text("Custom preamble\n\n" + path.read_text())
        self.assertTrue(policy.verify(self.root))
        with self.assertRaises(ValueError):
            self.sync()

    def test_managed_symlink_rejected_without_touching_target(self):
        outside = self.root / "custom.md"
        outside.write_text("Leave me unchanged.\n")
        (self.root / "AGENTS.md").symlink_to(outside)
        with self.assertRaises(ValueError):
            self.sync()
        self.assertEqual(outside.read_text(), "Leave me unchanged.\n")

    def test_main_accepts_only_same_repository_staging(self):
        self.assertEqual(self.event(self.pull_request()), [])
        for head, repository in (("feat/example", "meavo-booths/app"),
                                 ("staging", "someone-else/app"),
                                 ("$(touch should-not-exist)", "meavo-booths/app")):
            with self.subTest(head=head, repository=repository):
                self.assertTrue(self.event(self.pull_request(head=head, repository=repository)))
        self.assertEqual(self.event(self.pull_request(base="staging", head="feat/example")), [])
        self.assertEqual(self.event(self.pull_request(base="feat/example", head="fix/example")), [])

    def test_malformed_events_fail_closed(self):
        for event in ({}, [], {"pull_request": {}}, {"pull_request": {"base": {"ref": "main"}}}):
            with self.subTest(event=event):
                self.assertTrue(self.event(event))
        event = self.pull_request()
        event["pull_request"]["head"]["repo"] = None
        self.assertTrue(self.event(event))
        self.assertTrue(self.event(self.pull_request(), "pull_request_target"))
        self.assertTrue(policy.verify_event(self.root / "missing.json", "pull_request"))

    def test_push_and_cli_exit_status(self):
        self.assertEqual(self.event({"ref": "refs/heads/main"}, "push"), [])
        self.assertEqual(self.event({"ref": "refs/heads/staging"}, "push"), [])
        self.assertTrue(self.event({"ref": "refs/heads/main$(bad)"}, "push"))
        self.sync()
        command = [sys.executable, str(self.root / "scripts/verify-release-policy.py")]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.assertNotEqual(subprocess.run(command + ["--event", "missing.json"], capture_output=True).returncode, 0)
        (self.root / "RELEASE_POLICY.md").unlink()
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
