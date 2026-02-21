"""Git commit domain models for onboarding."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class GitCommit:
    """A single parsed git commit."""

    hash: str
    author: str
    date: datetime
    subject: str
    body: str = ""
    files_changed: list[str] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0


@dataclass
class CommitCluster:
    """A group of related commits identified by temporal proximity and file overlap."""

    commits: list[GitCommit]
    label: str = ""
    time_span_days: float = 0.0
