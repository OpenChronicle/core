# 🚫 DO NOT EDIT: guardrail test. Changes require CODEOWNERS approval.

import re
from pathlib import Path, PurePosixPath

SRC = Path("src/openchronicle")

FORBIDDEN_INFRA = re.compile(r"^(from|import)\s+openchronicle\.infrastructure", re.M)
PLUGIN_IN_CORE = re.compile(r"^(from|import)\s+openchronicle\.plugins", re.M)
ALLOWED_SHIMS = {
    "domain/services/narrative/__init__.py",
    "domain/services/scenes/__init__.py",
    "domain/services/timeline/__init__.py",
    "domain/services/characters/__init__.py",
    "domain/services/story_loader.py",
}


def scan(pattern, roots):
    hits = []
    for r in roots:
        base = SRC / r
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            t = p.read_text(encoding="utf-8", errors="ignore")
            if pattern.search(t):
                hits.append(str(PurePosixPath(p.relative_to(SRC))))
    return hits


def test_no_infra_in_domain_or_app():
    assert scan(FORBIDDEN_INFRA, ["domain", "application"]) == []


def test_no_plugin_in_core_layers_except_shims():
    hits = scan(PLUGIN_IN_CORE, ["domain", "application", "infrastructure", "interfaces"])
    assert [h for h in hits if h not in ALLOWED_SHIMS] == []
