"""Docs regression test: plugin invocation contract consistency.

Ensures plugin documentation does NOT drift back to obsolete guidance:
- Task handlers MUST be invoked via task_type "plugin.invoke".
- Dotted task_type strings (e.g. "hello.echo") MUST be described as
  invalid / INVALID_TASK_TYPE, never as the normal execution path.
"""

from __future__ import annotations

import re
from pathlib import Path

# Docs that define or demonstrate the plugin invocation contract.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DOC_FILES: list[Path] = [
    _REPO_ROOT / "docs" / "plugins" / "plugin_contract.md",
    _REPO_ROOT / "docs" / "plugins" / "plugin_quickstart.md",
    _REPO_ROOT / "docs" / "architecture" / "PLUGINS.md",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Matches task_type values inside JSON-ish or CLI examples.
# Captures the value after "task_type" in patterns like:
#   "task_type": "something"        (JSON)
#   task_type = something           (prose / shell)
#   "task_type":"something"         (compact JSON)
_TASK_TYPE_RE = re.compile(
    r"""
    ["\']?task_type["\']?      # key (optionally quoted)
    \s*[:=]\s*                 # separator (colon or equals)
    ["\']?                     # opening quote (optional)
    ([\w.]+)                   # captured value
    """,
    re.VERBOSE,
)


def _extract_task_type_values(text: str) -> list[str]:
    """Return all concrete task_type values found in *text*."""
    return _TASK_TYPE_RE.findall(text)


def _is_dotted_task_type(value: str) -> bool:
    """True when *value* looks like a dotted handler name (e.g. hello.echo).

    ``plugin.invoke`` is the canonical task_type and is NOT considered
    a 'dotted handler name' for the purpose of this check.
    """
    return "." in value and value != "plugin.invoke"


# Regex for a dotted task_type that appears *only* to be called out as
# invalid / rejected.  We look for surrounding context that makes this
# clear (case-insensitive).
_INVALID_CONTEXT_RE = re.compile(
    r"(invalid|rejected|INVALID_TASK_TYPE|not\s+supported|error|fail)",
    re.IGNORECASE,
)


def _dotted_usage_is_invalid_context(text: str, match: re.Match[str]) -> bool:
    """Return True when the dotted task_type near *match* is presented as invalid."""
    start = max(0, match.start() - 200)
    end = min(len(text), match.end() + 200)
    surrounding = text[start:end]
    return bool(_INVALID_CONTEXT_RE.search(surrounding))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPluginInvokeDocumented:
    """Every checked doc must mention plugin.invoke as the execution path."""

    def test_files_exist(self) -> None:
        for path in _DOC_FILES:
            assert path.exists(), f"Expected doc file is missing: {path}"

    def test_plugin_invoke_mentioned(self) -> None:
        for path in _DOC_FILES:
            text = _read(path)
            assert "plugin.invoke" in text, (
                f"{path.name} does not mention 'plugin.invoke' — "
                "plugin docs must document the canonical invocation path"
            )


class TestNoDottedTaskTypeAsNormal:
    """Dotted task_type values must only appear as *invalid* examples."""

    def test_no_dotted_task_type_presented_as_valid(self) -> None:
        for path in _DOC_FILES:
            text = _read(path)
            for m in _TASK_TYPE_RE.finditer(text):
                value = m.group(1)
                if not _is_dotted_task_type(value):
                    continue
                # This is a dotted task_type — it must appear in an
                # "invalid" context, not as a normal invocation example.
                assert _dotted_usage_is_invalid_context(text, m), (
                    f"{path.name} presents dotted task_type '{value}' "
                    "as a normal invocation path. Dotted task_type values "
                    "must only appear as invalid / INVALID_TASK_TYPE "
                    "examples."
                )


class TestExampleBlocksUsePluginInvoke:
    """JSON / CLI example blocks that submit tasks must use plugin.invoke."""

    def test_task_submit_examples_use_plugin_invoke(self) -> None:
        for path in _DOC_FILES:
            text = _read(path)
            # Extract fenced code blocks (``` … ```)
            blocks = re.findall(r"```[^\n]*\n(.*?)```", text, re.DOTALL)
            for block in blocks:
                task_types = _extract_task_type_values(block)
                for tt in task_types:
                    if _is_dotted_task_type(tt):
                        raise AssertionError(
                            f"{path.name}: code example uses "
                            f"task_type '{tt}' instead of 'plugin.invoke'. "
                            "All invocation examples must route through "
                            "'plugin.invoke'."
                        )
