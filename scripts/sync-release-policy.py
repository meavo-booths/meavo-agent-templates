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
import sys
import tempfile
from pathlib import Path

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


def expected_files(target):
    policy = verifier()
    contents = {}
    manifest = {"version": 1, "files": {}, "blocks": {}}
    for name in policy.FILES:
        content = (TEMPLATES / (name + ".template")).read_bytes()
        contents[name] = content
        manifest["files"][name] = policy.digest(content)
    for name in policy.BLOCKS:
        source = TEMPLATES / (name.replace(".md", ".release-policy.md") + ".template")
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


def sync(target, check=False):
    expected = expected_files(target)
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
    args = parser.parse_args()
    try:
        target = args.target.resolve(strict=True)
        if not target.is_dir():
            raise ValueError("target must be a repository directory")
        return sync(target, args.check)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
