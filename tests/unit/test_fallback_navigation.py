from typing import Any, Optional
import asyncio

from openchronicle.domain.ports.persistence_port import IPersistencePort
from openchronicle.domain.services.timeline.shared.fallback_navigation import FallbackNavigationManager


class _FakePersistence(IPersistencePort):
    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows

    def execute_query(self, story_id: str, query: str, params: Optional[dict[str, Any]] = None):
        # Return the stub rows regardless of query for this simple test
        return list(self._rows)

    def execute_update(self, story_id: str, query: str, params: Optional[dict[str, Any]] = None) -> bool:
        return True

    def init_database(self, story_id: str) -> bool:
        return True

    def backup_database(self, story_id: str, backup_name: str) -> bool:
        return True

    def restore_database(self, story_id: str, backup_name: str) -> bool:
        return True


def test_get_navigation_history_basic():
    rows = [
        {"scene_id": "a", "scene_title": "Title A", "timestamp": "2025-08-10T12:00:00Z"},
        {"scene_id": "b", "scene_title": None, "timestamp": "2025-08-10T12:01:00Z"},
    ]
    nav = FallbackNavigationManager("s-1", persistence_port=_FakePersistence(rows))

    history = asyncio.run(nav.get_navigation_history())
    assert len(history) == 2
    assert history[0]["scene_id"] == "a"
    assert history[1]["title"] == "Untitled Scene"
