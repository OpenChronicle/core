"""Test that application/policies layer remains pure (no infrastructure dependencies)."""

from __future__ import annotations

from pathlib import Path


def test_policies_layer_has_no_infrastructure_imports() -> None:
    """
    Application policies must not import infrastructure adapters.

    This prevents the policies layer from becoming "infrastructure-lite".
    Policies should be generic and reusable, not coupled to specific adapters.

    Forbidden imports:
    - openai, httpx, requests (HTTP clients)
    - sqlite3 (database)
    - ollama (specific LLM provider)
    """
    policies_path = Path(__file__).parent.parent / "src" / "openchronicle" / "core" / "application" / "policies"

    if not policies_path.exists():
        # Policies directory doesn't exist yet, skip test
        return

    violations = []
    forbidden_imports = ["openai", "httpx", "requests", "sqlite3", "ollama"]

    for py_file in policies_path.rglob("*.py"):
        # Skip __pycache__ and other non-source files
        if "__pycache__" in str(py_file):
            continue

        content = py_file.read_text(encoding="utf-8")

        for forbidden in forbidden_imports:
            # Check for direct imports
            if f"import {forbidden}" in content:
                violations.append(f"{py_file.name}: imports {forbidden}")
            # Check for from imports
            if f"from {forbidden}" in content:
                violations.append(f"{py_file.name}: imports from {forbidden}")

    if violations:
        msg = "Application policies have forbidden infrastructure imports:\n" + "\n".join(
            f"  - {v}" for v in violations
        )
        raise AssertionError(msg)
