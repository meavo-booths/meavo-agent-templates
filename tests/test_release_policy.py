"""Dependency-free regression checks for safe propagation and release gates."""

import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
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


    def origin(self, remote):
        subprocess.run(["git", "init", "--quiet", str(self.root)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "config", "remote.origin.url", remote],
                       check=True, capture_output=True)

    def website_templates(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        templates = Path(temporary.name) / "templates"
        shutil.copytree(ROOT / "templates", templates)
        overrides = templates / "repositories" / policy.DIRECT_MAIN_REPOSITORY
        names = ["RELEASE_POLICY.md.template", ".cursor/rules/release-process.mdc.template",
                 *(name.replace(".md", ".release-policy.md") + ".template" for name in policy.BLOCKS)]
        for name in names:
            content = (templates / name).read_text()
            if policy.BEGIN in content:
                content = content.replace(policy.BEGIN + "\n", policy.BEGIN + "\nWebsite profile fixture.\n")
            else:
                content += "\nWebsite profile fixture.\n"
            path = overrides / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        patch = mock.patch.object(sync_tool, "TEMPLATES", templates)
        patch.start()
        self.addCleanup(patch.stop)
        return overrides

    def website_event(self, head="feat/example", repository=None):
        repository = repository or policy.DIRECT_MAIN_REPOSITORY
        event = self.pull_request(head=head, repository=repository)
        event["repository"]["full_name"] = repository
        event["pull_request"]["base"]["repo"]["full_name"] = repository
        return event

    def test_only_exact_website_gets_direct_main(self):
        for head in ("feat/example", "fix/example", "chore/example", "docs/example", "staging"):
            self.assertEqual(self.event(self.website_event(head)), [])
        for head in ("main", "", "  ", None, [], {}):
            with self.subTest(head=head):
                self.assertTrue(self.event(self.website_event(head)))
        for repository in ("other/office-phone-booths-uk", "meavo-booths/office-phone-booths-uk-copy",
                           "meavo-booths/sales", "meavo-booths/app"):
            with self.subTest(repository=repository):
                self.assertTrue(self.event(self.website_event(repository=repository)))
                self.assertEqual(self.event(self.website_event("staging", repository)), [])

    def test_website_forks_and_mismatched_event_identity_fail(self):
        for section in ("head", "base"):
            event = self.website_event()
            event["pull_request"][section]["repo"]["full_name"] = "someone-else/office-phone-booths-uk"
            self.assertTrue(self.event(event))
        event = self.website_event()
        event["repository"]["full_name"] = "meavo-booths/sales"
        self.assertTrue(self.event(event))
        event = self.website_event()
        event["pull_request"]["head"]["repo"] = None
        self.assertTrue(self.event(event))
        self.assertTrue(self.event(self.website_event(), "pull_request_target"))

    def test_remote_identity_recognizes_only_github_ssh_and_https(self):
        for url in ("https://github.com/meavo-booths/office-phone-booths-uk.git",
                    "git@github.com:meavo-booths/office-phone-booths-uk.git",
                    "ssh://git@github.com/meavo-booths/office-phone-booths-uk.git",
                    "https://github.com/MEAVO-BOOTHS/office-phone-booths-uk/"):
            self.assertEqual(sync_tool.repository_from_remote(url), policy.DIRECT_MAIN_REPOSITORY)
        for url in ("https://example.com/meavo-booths/office-phone-booths-uk.git",
                    "https://github.com.evil.test/meavo-booths/office-phone-booths-uk.git",
                    "https://github.com@evil.test/meavo-booths/office-phone-booths-uk.git",
                    "https://github.com/meavo-booths/office-phone-booths-uk?profile=direct-main",
                    "https://github.com:invalid/meavo-booths/office-phone-booths-uk",
                    "git@github.com:meavo-booths/office-phone-booths-uk/../../sales",
                    "file:///meavo-booths/office-phone-booths-uk", "https://[invalid"):
            self.assertIsNone(sync_tool.repository_from_remote(url), url)

    def test_website_sync_selects_overrides_and_survives_resync(self):
        overrides = self.website_templates()
        self.origin("git@github.com:meavo-booths/office-phone-booths-uk.git")
        (self.root / "AGENTS.md").write_text("Custom website build instructions.\n")
        self.assertEqual(self.sync(), 0)
        self.assertEqual((self.root / "RELEASE_POLICY.md").read_bytes(),
                         (overrides / "RELEASE_POLICY.md.template").read_bytes())
        self.assertTrue((self.root / "AGENTS.md").read_text().endswith("Custom website build instructions.\n"))
        manifest = json.loads((self.root / policy.MANIFEST).read_text())
        self.assertEqual(manifest["repository"], policy.DIRECT_MAIN_REPOSITORY)
        self.assertEqual(manifest["profile"], "direct-main")
        self.assertEqual(policy.verify(self.root), [])
        before = self.snapshot()
        self.assertEqual(self.sync(), 0)
        self.assertEqual(self.sync(check=True), 0)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((self.root / ".github/workflows/release-policy.yml").read_bytes(),
                         (sync_tool.TEMPLATES / ".github/workflows/release-policy.yml.template").read_bytes())

    def test_bootstrap_preserves_website_profile_including_force(self):
        self.origin("https://github.com/meavo-booths/office-phone-booths-uk.git")
        custom = b"# Custom website instructions\r\nKeep these project details.\r\n"
        (self.root / "AGENTS.md").write_bytes(custom)
        command = ["bash", str(ROOT / "scripts/bootstrap-agent-docs.sh"), str(self.root)]
        subprocess.run(command, check=True, capture_output=True)
        self.assertTrue((self.root / "AGENTS.md").read_bytes().endswith(custom))
        expected = (ROOT / "templates/repositories" / policy.DIRECT_MAIN_REPOSITORY
                    / "RELEASE_POLICY.md.template").read_bytes()
        self.assertEqual((self.root / "RELEASE_POLICY.md").read_bytes(), expected)
        self.assertEqual(policy.verify(self.root), [])
        # --force deliberately replaces custom skeleton content, but must retain the exception.
        subprocess.run(command + ["--force"], check=True, capture_output=True)
        self.assertEqual((self.root / "RELEASE_POLICY.md").read_bytes(), expected)
        self.assertEqual(json.loads((self.root / policy.MANIFEST).read_text())["profile"], "direct-main")
        self.assertEqual(policy.verify(self.root), [])
        self.assertEqual(self.sync(check=True), 0)

    def test_other_repo_and_unknown_identity_keep_default_policy(self):
        self.website_templates()
        for identity in (None, "meavo-booths/sales", "meavo-booths/office-phone-booths-uk-copy",
                         "other/office-phone-booths-uk"):
            expected = sync_tool.expected_files(self.root, identity)
            self.assertEqual(expected["RELEASE_POLICY.md"],
                             (sync_tool.TEMPLATES / "RELEASE_POLICY.md.template").read_bytes())
            self.assertEqual(set(json.loads(expected[policy.MANIFEST])), {"version", "files", "blocks"})

    def test_explicit_repository_cannot_override_an_origin(self):
        for remote in ("https://github.com/meavo-booths/sales.git",
                       "https://evil.test/meavo-booths/office-phone-booths-uk.git"):
            self.origin(remote)
            before = self.snapshot()
            with self.assertRaises(ValueError):
                sync_tool.sync(self.root, repository=policy.DIRECT_MAIN_REPOSITORY)
            self.assertEqual(self.snapshot(), before)
        self.origin("https://github.com/meavo-booths/office-phone-booths-uk.git")
        self.assertEqual(sync_tool.target_repository(self.root, policy.DIRECT_MAIN_REPOSITORY),
                         policy.DIRECT_MAIN_REPOSITORY)

    def test_website_archive_requires_identity_before_resync(self):
        self.website_templates()
        with contextlib.redirect_stdout(io.StringIO()):
            sync_tool.sync(self.root, repository=policy.DIRECT_MAIN_REPOSITORY)
        before = self.snapshot()
        for identity in (None, "meavo-booths/sales"):
            with self.assertRaises(ValueError):
                sync_tool.sync(self.root, repository=identity)
            self.assertEqual(self.snapshot(), before)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sync_tool.sync(self.root, check=True,
                                           repository=policy.DIRECT_MAIN_REPOSITORY), 0)

    def test_legacy_website_exception_is_not_silently_overwritten(self):
        (self.root / "RELEASE_POLICY.md").write_text(
            "# MEAVO release policy\n\nPolicy version: 2026-09-28.1 (office-phone-booths-uk: direct-to-main releases)\n")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.sync()
        self.assertEqual(self.snapshot(), before)
        (self.root / "RELEASE_POLICY.md").write_text(
            f"# MEAVO release policy\nApplies only to `{policy.DIRECT_MAIN_REPOSITORY}`\n")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.sync()
        self.assertEqual(self.snapshot(), before)

    def test_incomplete_profile_never_falls_back_to_staging_instructions(self):
        overrides = self.website_templates()
        (overrides / "AGENTS.release-policy.md.template").unlink()
        before = self.snapshot()
        with self.assertRaises(ValueError):
            sync_tool.sync(self.root, repository=policy.DIRECT_MAIN_REPOSITORY)
        self.assertEqual(self.snapshot(), before)

    def test_profile_manifest_is_bound_to_the_website_and_event(self):
        self.website_templates()
        with contextlib.redirect_stdout(io.StringIO()):
            sync_tool.sync(self.root, repository=policy.DIRECT_MAIN_REPOSITORY)
        path = self.root / policy.MANIFEST
        manifest = json.loads(path.read_text())
        for bad in ({**manifest, "repository": "meavo-booths/sales"},
                    {**manifest, "profile": "anything"},
                    {key: value for key, value in manifest.items() if key != "repository"}):
            path.write_text(json.dumps(bad))
            self.assertTrue(policy.verify(self.root))
        path.write_text(json.dumps(manifest))
        event_path = self.root / "event.json"
        event_path.write_text(json.dumps(self.website_event()))
        command = [sys.executable, str(self.root / "scripts/verify-release-policy.py"),
                   "--event", str(event_path), "--event-name", "pull_request"]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        event_path.write_text(json.dumps(self.pull_request()))
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.assertTrue(policy.verify_event(event_path, "push", policy.DIRECT_MAIN_REPOSITORY))

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
