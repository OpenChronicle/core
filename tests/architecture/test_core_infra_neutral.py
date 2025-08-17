# 🚫 DO NOT EDIT: guardrail test. Changes require CODEOWNERS approval.

import re
from pathlib import Path

SRC = Path("src/openchronicle")
STORY = re.compile(r"\b(story|scene|character|timeline|lore|narrative)\b", re.I | re.M)


def test_core_infrastructure_is_neutral():
    base = SRC / "infrastructure"
    if not base.exists():
        return
    offenders = []
    for p in base.rglob("*.py"):
        t = p.read_text(encoding="utf-8", errors="ignore")
        if STORY.search(t):
            offenders.append(str(p.relative_to(SRC)))
    assert offenders == [], "Story-specific terms remain in core infra:\n" + "\n".join(offenders)
