from typing import Any, Optional
import asyncio

from openchronicle.domain.ports.persistence_port import IPersistencePort
from openchronicle.domain.services.timeline.shared.fallback_timeline import FallbackTimelineManager


class _FakePersistence(IPersistencePort):
    def __init__(self, rows):
        self._rows = rows

    def execute_query(self, story_id: str, query: str, params: Optional[dict[str, Any]] = None):
        return list(self._rows)

    def execute_update(self, story_id: str, query: str, params: Optional[dict[str, Any]] = None) -> bool:
        return True

    def init_database(self, story_id: str) -> bool:
        return True

    def backup_database(self, story_id: str, backup_name: str) -> bool:
        return True

    def restore_database(self, story_id: str, backup_name: str) -> bool:
        return True


def test_build_full_timeline_basic():
    rows = [
        {"scene_id": "a", "timestamp": "2025-08-10T12:00:00Z", "input": "i" * 250, "output": "o" * 250},
    ]
    mgr = FallbackTimelineManager("s-1", persistence_port=_FakePersistence(rows))

    timeline = asyncio.run(mgr.build_full_timeline())
    # Ensure truncation to 200 chars
    assert len(timeline["entries"][0]["input"]) == 200
    assert timeline["entries"][0]["fallback_mode"] is True
