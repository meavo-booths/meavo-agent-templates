#!/usr/bin/env python3
"""Run the packaged workspace tool's own offline tests with the rest of the suite."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('packaged_workspace_tests', ROOT / 'workspace/tools/test_workspace.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
WorkspaceTests = module.WorkspaceTests
