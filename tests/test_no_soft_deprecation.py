"""Test that prevents soft deprecation patterns and tech debt breadcrumbs.

This test ensures the codebase maintains a zero-tolerance policy for:
- Soft deprecation markers (deprecated, legacy, compatibility shims, etc.)
- Tech debt breadcrumbs (TODO, FIXME, HACK, XXX, TEMP, workaround)
- Dead code patterns (if False:, if 0:)
- Deprecated filenames (*_deprecated.py, *_legacy.py, etc.)

Hard exclusion: v1.reference/ is never scanned, regardless of symlinks or nesting.
"""

from __future__ import annotations

import re
from pathlib import Path

from helpers.repo_scan import scan_repository  # isort:skip


# Allowlist for patterns we explicitly accept.
# Maps relative file path (as string) to list of allowed strings/patterns.
# Keep this minimal; ideally empty.
#
# Example (if needed):
#   ALLOWLIST = {
#       "docs/examples/old_pattern.md": ["deprecated", "legacy"],
#   }
ALLOWLIST: dict[str, list[str]] = {
    # This test checks that LLMProviderError supports backward-compatible creation
    "tests/test_actionable_provider_errors.py": [
        r"backward compatible",
    ]
}


# Soft deprecation markers that indicate code should be deleted, not kept with a marker.
# Note: We focus on explicit deprecation language, not generic use of "legacy" or "temporary"
# which may describe legitimate fallback paths or test fixtures.
SOFT_DEPRECATION_PATTERNS = [
    r"\bdeprecated\b",  # deprecated (case-insensitive)
    r"\bdeprecate\b",  # deprecate
    r"backward[s]?\s+compatible",  # backward compatible, backwards compatible
    r"compatibility\s+shim",  # compatibility shim
    r"for\s+now",  # for now
    r"keep\s+for\s+now",  # keep for now
    r"remove\s+later",  # remove later
    r"will\s+be\s+removed",  # will be removed
    r"to\s+be\s+removed",  # to be removed
    r"left\s+here",  # left here
]

# Tech debt breadcrumbs - these should never appear
TECH_DEBT_PATTERNS = [
    r"^[^#]*\bTODO\b",  # TODO (case-sensitive)
    r"^[^#]*\bFIXME\b",  # FIXME (case-sensitive)
    r"^[^#]*\bHACK\b",  # HACK (case-sensitive)
    r"^[^#]*\bXXX\b",  # XXX (case-sensitive)
    r"^[^#]*\bTEMP\b",  # TEMP (case-sensitive)
    r"\bworkaround\b",  # workaround
]

# Dead code patterns
DEAD_CODE_PATTERNS = [
    r"^\s*if\s+False\s*:",  # if False: (Python dead code)
    r"^\s*if\s+0\s*:",  # if 0: (dead code)
    r"^\s*if\s+None\s*:",  # if None: (dead code)
    r"^\s*pass\s+#",  # pass # (comment after pass)
]

# Deprecated filename patterns
DEPRECATED_FILENAME_PATTERNS = [
    r"^.*_deprecated\.py$",
    r"^.*_legacy\.py$",
    r"^.*_old\.py$",
    r"^.*_bak\.py$",
    r"^.*_backup\.py$",
    r"^.*_tmp\.py$",
    r"^.*_temp\.py$",
]


def _is_allowed(file_path: Path, matched_text: str) -> bool:
    """Check if a specific match is in the allowlist for this file."""
    file_path_str = str(file_path).replace("\\", "/")  # Normalize path separators
    if file_path_str not in ALLOWLIST:
        return False

    allowed = ALLOWLIST[file_path_str]
    for pattern in allowed:
        if pattern == matched_text:  # Exact match
            return True
        # Also try as regex
        try:
            if re.search(pattern, matched_text, re.IGNORECASE):
                return True
        except re.error:
            pass

    return False


def _check_soft_deprecations(file_path: Path, content: str) -> list[tuple[int, str]]:
    """Check for soft deprecation patterns in file content."""
    violations = []

    for line_num, line in enumerate(content.split("\n"), start=1):
        # Skip comments-only lines for deprecation markers (but not tech debt)
        # We want to flag "this is deprecated" in comments, so check the whole line
        for pattern in SOFT_DEPRECATION_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                if not _is_allowed(file_path, line.strip()):
                    violations.append((line_num, line.strip()))
                break  # Only report once per line

    return violations


def _check_tech_debt(file_path: Path, content: str) -> list[tuple[int, str]]:
    """Check for tech debt breadcrumbs (TODO, FIXME, HACK, etc.)."""
    violations = []

    for line_num, line in enumerate(content.split("\n"), start=1):
        for pattern in TECH_DEBT_PATTERNS:
            if re.search(pattern, line):
                if not _is_allowed(file_path, line.strip()):
                    violations.append((line_num, line.strip()))
                break  # Only report once per line

    return violations


def _check_dead_code(file_path: Path, content: str) -> list[tuple[int, str]]:
    """Check for dead code patterns."""
    violations = []

    for line_num, line in enumerate(content.split("\n"), start=1):
        for pattern in DEAD_CODE_PATTERNS:
            if re.search(pattern, line):
                if not _is_allowed(file_path, line.strip()):
                    violations.append((line_num, line.strip()))
                break  # Only report once per line

    return violations


def _check_deprecated_filenames(file_path: Path) -> bool:
    """Check if filename matches a deprecated naming pattern."""
    file_name = file_path.name
    for pattern in DEPRECATED_FILENAME_PATTERNS:
        if re.match(pattern, file_name):
            return True
    return False


def test_no_soft_deprecation_patterns() -> None:
    """Fail the build if soft deprecation patterns exist in the codebase."""
    all_violations: list[tuple[Path, str, list[tuple[int, str]]]] = []

    # Scan repository, excluding the test file itself
    scanned_files = scan_repository()
    scanned_files = [(path, content) for path, content in scanned_files if path.name != "test_no_soft_deprecation.py"]

    for file_path, content in scanned_files:
        violations = _check_soft_deprecations(file_path, content)
        if violations:
            all_violations.append((file_path, "soft deprecation", violations))

    if all_violations:
        msg = _format_violations_message(all_violations)
        raise AssertionError(msg)


def test_no_tech_debt_breadcrumbs() -> None:
    """Fail the build if tech debt breadcrumbs exist in the codebase."""
    all_violations: list[tuple[Path, str, list[tuple[int, str]]]] = []

    scanned_files = scan_repository()
    # Exclude the test file itself from scanning
    scanned_files = [(path, content) for path, content in scanned_files if path.name != "test_no_soft_deprecation.py"]

    for file_path, content in scanned_files:
        violations = _check_tech_debt(file_path, content)
        if violations:
            all_violations.append((file_path, "tech debt marker", violations))

    if all_violations:
        msg = _format_violations_message(all_violations)
        raise AssertionError(msg)


def test_no_dead_code_patterns() -> None:
    """Fail the build if dead code patterns exist in the codebase."""
    all_violations: list[tuple[Path, str, list[tuple[int, str]]]] = []

    scanned_files = scan_repository()
    # Exclude the test file itself
    scanned_files = [(path, content) for path, content in scanned_files if path.name != "test_no_soft_deprecation.py"]

    for file_path, content in scanned_files:
        violations = _check_dead_code(file_path, content)
        if violations:
            all_violations.append((file_path, "dead code", violations))

    if all_violations:
        msg = _format_violations_message(all_violations)
        raise AssertionError(msg)


def test_no_deprecated_filenames() -> None:
    """Fail the build if deprecated filename patterns exist in the codebase."""
    violations: list[Path] = []

    scanned_files = scan_repository()
    # Exclude the test file itself
    scanned_files = [(path, _) for path, _ in scanned_files if path.name != "test_no_soft_deprecation.py"]

    for file_path, _ in scanned_files:
        if _check_deprecated_filenames(file_path):
            violations.append(file_path)

    if violations:
        msg = "Found files with deprecated naming patterns (e.g., *_deprecated.py, *_legacy.py):\n"
        for file_path in violations:
            msg += f"  {file_path}\n"
        raise AssertionError(msg)


def _format_violations_message(violations: list[tuple[Path, str, list[tuple[int, str]]]]) -> str:
    """Format a detailed violation message."""
    msg = "Found tech debt patterns in codebase:\n\n"

    for file_path, violation_type, lines in violations:
        msg += f"{file_path} ({violation_type}):\n"
        for line_num, line_content in lines:
            # Truncate long lines
            if len(line_content) > 100:
                line_content = line_content[:97] + "..."
            msg += f"  Line {line_num}: {line_content}\n"
        msg += "\n"

    msg += (
        "IMPORTANT: This codebase enforces zero-tolerance for tech debt patterns.\n"
        "- Do NOT add TODO/FIXME/HACK comments as placeholders.\n"
        "- Do NOT use soft deprecation markers (deprecated, legacy, shim, etc.).\n"
        "- DO DELETE dead code completely instead of marking it.\n"
        "If you need an exception, add an entry to ALLOWLIST in test_no_soft_deprecation.py\n"
    )

    return msg
