# 🚫 DO NOT EDIT: guardrail test. Changes require CODEOWNERS approval.

import importlib


def test_core_boots_without_plugins():
    # Importing bootstrap + CLI shouldn't require any plugin to be present
    importlib.import_module("openchronicle.infrastructure.bootstrap")
    cli = importlib.import_module("openchronicle.interfaces.cli.main")
    assert hasattr(cli, "app")
