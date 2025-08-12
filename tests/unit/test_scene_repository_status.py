from typing import Any, Optional

from openchronicle.domain.ports.persistence_port import IPersistencePort
from openchronicle.domain.services.scenes.persistence.scene_repository import SceneRepository


class _FakePersistence(IPersistencePort):
    def __init__(self, count: int = 0, raise_on_count: bool = False):
        self._count = count
        self._raise_on_count = raise_on_count

    def execute_query(self, story_id: str, query: str, params: Optional[dict[str, Any]] = None):
        if "COUNT(*)" in query:
            if self._raise_on_count:
                # Simulate low-level error to be mapped by SceneRepository
                raise RuntimeError("boom")
            return [{"count": self._count}]
        return []

    def execute_update(self, story_id: str, query: str, params: Optional[dict[str, Any]] = None) -> bool:
        return True

    def init_database(self, story_id: str) -> bool:
        return True

    def backup_database(self, story_id: str, backup_name: str) -> bool:
        return True

    def restore_database(self, story_id: str, backup_name: str) -> bool:
        return True


def test_get_status_active():
    repo = SceneRepository("s-1", persistence_port=_FakePersistence(count=3))
    assert repo.get_status().startswith("active (")


def test_get_status_error_on_exception():
    repo = SceneRepository("s-1", persistence_port=_FakePersistence(raise_on_count=True))
    assert repo.get_status() == "error"
