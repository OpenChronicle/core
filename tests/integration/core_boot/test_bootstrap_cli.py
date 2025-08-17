# 🚫 DO NOT EDIT: guardrail test. Changes require CODEOWNERS approval.

import importlib


def test_package_imports():
    m = importlib.import_module("openchronicle")
    assert m


def test_cli_entry_defined():
    cli = importlib.import_module("openchronicle.interfaces.cli.main")
    assert hasattr(cli, "app")


def test_bootstrap_imports():
    b = importlib.import_module("openchronicle.infrastructure.bootstrap")
    assert b
