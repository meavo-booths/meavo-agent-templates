#!/usr/bin/env python3
"""Safely install canonical release rules, or check a repository against them.

Only dedicated policy files and marked blocks are managed. Existing project
instructions outside the blocks are retained byte for byte. A missing, duplicate,
or malformed marker fails before any files are written.
"""

import argparse
import importlib.machinery
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"


def verifier():
    path = TEMPLATES / "scripts/verify-release-policy.py.template"
    loader = importlib.machinery.SourceFileLoader("release_policy_verifier", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    # Reading a template must not create cache files in the template repository.
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def update_document(existing, block, policy):
    if policy.BEGIN not in existing and policy.END not in existing:
        return block + "\n\n" + existing if existing else block + "\n"
    current = policy.managed_block(existing)
    if not existing.startswith(policy.BEGIN):
        raise ValueError("existing managed block must be first; move it to the top before syncing")
    return block + existing[len(current):]


def normalize_repository(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise ValueError("repository must be an owner/name GitHub identifier")
    owner, name = value.split("/")
    if owner in (".", "..") or name in (".", ".."):
        raise ValueError("invalid repository identifier")
    return value.lower()


def repository_from_remote(remote):
    """Recognize GitHub SSH/HTTPS origins, never a matching path on another host."""
    if remote.startswith("git@github.com:"):
        path = remote[len("git@github.com:"):]
    else:
        try:
            parsed = urlsplit(remote)
            port = parsed.port
        except ValueError:
            return None
        if (parsed.scheme not in ("https", "ssh") or parsed.hostname != "github.com"
                or parsed.query or parsed.fragment or port is not None
                or (parsed.scheme == "https" and parsed.username is not None)
                or (parsed.scheme == "ssh" and parsed.username != "git")):
            return None
        path = parsed.path.removeprefix("/")
    path = path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    try:
        return normalize_repository(path)
    except ValueError:
        return None


def target_repository(target, explicit=None):
    requested = normalize_repository(explicit) if explicit is not None else None
    remote = None
    # Do not accidentally inherit the origin of a parent repository for an archive.
    if (target / ".git").exists():
        result = subprocess.run(["git", "-C", str(target), "config", "--local", "--get",
                                 "remote.origin.url"], capture_output=True, text=True)
        if result.returncode not in (0, 1):
            raise ValueError("cannot inspect the target repository's origin")
        remote = result.stdout.strip() or None
    actual = repository_from_remote(remote) if remote else None
    if requested is not None and remote is not None and requested != actual:
        raise ValueError("--repository does not match the target's GitHub origin")
    return actual or requested


def installed_exception(target, policy):
    """Protect registered profiles and the website's original September exception."""
    manifest_path = policy.checked_path(target, policy.MANIFEST)
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
        except (ValueError, OSError):
            manifest = {}
        if isinstance(manifest, dict) and ("repository" in manifest or "profile" in manifest):
            if (manifest.get("repository"), manifest.get("profile")) != (
                    policy.DIRECT_MAIN_REPOSITORY, "direct-main"):
                raise ValueError("unrecognized installed repository release profile")
            return policy.DIRECT_MAIN_REPOSITORY
    policy_path = policy.checked_path(target, "RELEASE_POLICY.md")
    if policy_path.exists():
        text = policy_path.read_text()
        legacy = re.search(r"^Policy version:.*\(office-phone-booths-uk: direct-to-main releases\)",
                           text, re.MULTILINE)
        registered = f"Applies only to `{policy.DIRECT_MAIN_REPOSITORY}`" in text
        if legacy or registered:
            return policy.DIRECT_MAIN_REPOSITORY
    return None


def expected_files(target, repository=None):
    policy = verifier()
    repository = target_repository(target, repository)
    installed = installed_exception(target, policy)
    if installed and repository != installed:
        raise ValueError("installed website exception needs its matching GitHub origin or --repository")
    overrides = (TEMPLATES / "repositories" / policy.DIRECT_MAIN_REPOSITORY
                 if repository == policy.DIRECT_MAIN_REPOSITORY else None)

    if overrides is not None:
        required = ["RELEASE_POLICY.md.template", ".cursor/rules/release-process.mdc.template",
                    *(name.replace(".md", ".release-policy.md") + ".template" for name in policy.BLOCKS)]
        if any(not (overrides / name).is_file() for name in required):
            raise ValueError("website release profile templates are incomplete; refusing the staging fallback")

    def template(name):
        if overrides is not None and (overrides / name).is_file():
            return overrides / name
        return TEMPLATES / name

    contents = {}
    manifest = {"version": 1, "files": {}, "blocks": {}}
    if repository == policy.DIRECT_MAIN_REPOSITORY:
        manifest.update(repository=repository, profile="direct-main")
    for name in policy.FILES:
        content = template(name + ".template").read_bytes()
        contents[name] = content
        manifest["files"][name] = policy.digest(content)
    for name in policy.BLOCKS:
        source = template(name.replace(".md", ".release-policy.md") + ".template")
        block = policy.managed_block(source.read_bytes().decode("utf-8"))
        path = policy.checked_path(target, name)
        existing = path.read_bytes().decode("utf-8") if path.exists() else ""
        contents[name] = update_document(existing, block, policy).encode("utf-8")
        manifest["blocks"][name] = policy.digest(block.encode("utf-8"))
    contents[policy.MANIFEST] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    # Validate all destinations before mutating any; avoid partial changes on bad docs/symlinks.
    for name in contents:
        path = policy.checked_path(target, name)
        if path.exists() and not path.is_file():
            raise ValueError(f"managed path is not a regular file: {name}")
    return contents


def sync(target, check=False, repository=None):
    expected = expected_files(target, repository)
    changed = []
    for name, content in expected.items():
        path = target / name
        if path.exists() and path.read_bytes() == content:
            continue
        changed.append(name)
        if check:
            print(f"OUT OF DATE: {name}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(content)
            temporary.chmod(mode)
            os.replace(temporary, path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        print(f"UPDATED: {name}")
    if not changed:
        print("Release policy matches canonical templates.")
    return 1 if check and changed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="existing repository root")
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    parser.add_argument("--repository", help="owner/name for archives without an origin; must match an existing origin")
    args = parser.parse_args()
    try:
        target = args.target.resolve(strict=True)
        if not target.is_dir():
            raise ValueError("target must be a repository directory")
        return sync(target, args.check, args.repository)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
