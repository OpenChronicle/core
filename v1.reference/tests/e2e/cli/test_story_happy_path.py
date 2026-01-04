# 🚫 DO NOT EDIT: guardrail test. Changes require CODEOWNERS approval.

import subprocess
import sys

import pytest


@pytest.mark.e2e
def test_cli_help_runs():
    proc = subprocess.run([sys.executable, "-m", "openchronicle", "--help"], capture_output=True)
    assert proc.returncode == 0
