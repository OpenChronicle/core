from __future__ import annotations

import re
from pathlib import Path

from openchronicle.core.domain.errors import error_codes

ERROR_CODE_LITERAL_RE = re.compile(
    r"error_code\s*=\s*['\"]([A-Za-z0-9_]+)['\"]|['\"]error_code['\"]\s*:\s*['\"]([A-Za-z0-9_]+)['\"]"
)


def test_error_code_constants_are_exported_and_unique() -> None:
    constants = {name: value for name, value in vars(error_codes).items() if name.isupper() and isinstance(value, str)}

    assert set(error_codes.__all__) == set(constants)
    values = list(constants.values())
    assert len(values) == len(set(values))


def test_no_error_code_string_literals_in_runtime() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "openchronicle"
    exclusions = {
        root / "core" / "domain" / "errors" / "error_codes.py",
        root / "core" / "domain" / "errors" / "__init__.py",
        root / "core" / "domain" / "error_codes.py",
    }

    matches: list[tuple[Path, str]] = []
    for path in root.rglob("*.py"):
        if path in exclusions:
            continue
        text = path.read_text(encoding="utf-8")
        for match in ERROR_CODE_LITERAL_RE.finditer(text):
            literal = match.group(1) or match.group(2)
            matches.append((path, literal))

    assert matches == []
