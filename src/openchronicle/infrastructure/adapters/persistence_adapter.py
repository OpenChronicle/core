"""
Persistence adapter implementing dom            timeline_file = story_path / "timeline.json"
            if not timeline_file.exists():
                timeline_file.writ                scenes_file.write_text(json.dumps(scenes, indent=2), encoding='utf-8')
                return True

        except (OSError, IOError, PermissionError) as e:
            print(f"File system error updating scene {scene_id} for {story_id}: {e}")
            return False
        except json.JSONDecodeError as e:
            print(f"JSON decode error updating scene {scene_id} for {story_id}: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error updating scene {scene_id} for {story_id}: {e}")
            return False
        else:
            return Falseencoding='utf-8')

        except (OSError, IOError, PermissionError) as e:
            print(f"File system error initializing database for {story_id}: {e}")
            return False
        except (TypeError, ValueError) as e:
            print(f"Data validation error initializing database for {story_id}: {e}")
            return False
        else:
            return Trueence port.
Provides concrete implementation of persistence operations.
"""
import asyncio
import json
import os
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from openchronicle.domain.ports.persistence_port import IPersistencePort
from openchronicle.shared.exceptions import InfrastructureError


class PersistenceAdapter(IPersistencePort):
    """Concrete implementation of persistence operations."""

    def __init__(self, storage_path: Optional[str] = None):
        """Initialize persistence adapter."""
        self.storage_path = storage_path or "storage"
        self._ensure_storage_path()

    def _ensure_storage_path(self):
        """Ensure storage directory exists."""
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)

    async def init_database(self, story_id: str) -> bool:
        """Initialize database for story."""
        try:
            # Simple file-based storage initialization
            story_path = Path(self.storage_path) / "stories" / story_id
            story_path.mkdir(parents=True, exist_ok=True)

            # Create basic structure files if they don't exist
            scenes_file = story_path / "scenes.json"
            if not scenes_file.exists():
                scenes_file.write_text("[]", encoding='utf-8')

            timeline_file = story_path / "timeline.json"
            if not timeline_file.exists():
                timeline_file.write_text("[]", encoding='utf-8')

        except (OSError, IOError, PermissionError) as e:
            print(f"File system error initializing database for {story_id}: {e}")
            return False
        except (TypeError, ValueError) as e:
            print(f"JSON encoding error initializing database for {story_id}: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error initializing database for {story_id}: {e}")
            return False
        else:
            return True

    async def execute_query(self, story_id: str, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute a database query."""
        try:
            # For file-based storage, this is a simplified query handler
            # In a real implementation, this would parse the query and execute it

            story_path = Path(self.storage_path) / "stories" / story_id

            # Simple query routing based on query content
            if "scenes" in query.lower():
                return await self._query_scenes(story_path, params or {})
            elif "timeline" in query.lower():
                return await self._query_timeline(story_path, params or {})
            else:
                return []

        except (OSError, IOError, PermissionError) as e:
            print(f"File system error executing query for {story_id}: {e}")
            return []
        except (json.JSONDecodeError, TypeError) as e:
            print(f"JSON processing error executing query for {story_id}: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error executing query for {story_id}: {e}")
            return []

    async def execute_update(self, story_id: str, query: str, params: Optional[Dict] = None) -> bool:
        """Execute a database update."""
        try:
            story_path = Path(self.storage_path) / "stories" / story_id

            # Simple update routing
            if "scenes" in query.lower():
                return await self._update_scenes(story_path, params or {})
            elif "timeline" in query.lower():
                return await self._update_timeline(story_path, params or {})
            else:
                return True

        except (OSError, IOError, PermissionError) as e:
            print(f"File system error executing update for {story_id}: {e}")
            return False
        except (json.JSONDecodeError, TypeError) as e:
            print(f"JSON processing error executing update for {story_id}: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error executing update for {story_id}: {e}")
            return False

    async def get_scenes(self, story_id: str, limit: int = 5) -> List[Dict]:
        """Get scenes for navigation."""
        try:
            story_path = Path(self.storage_path) / "stories" / story_id
            scenes_file = story_path / "scenes.json"

            if scenes_file.exists():
                scenes = json.loads(scenes_file.read_text(encoding='utf-8'))
                return scenes[-limit:] if scenes else []

        except (OSError, IOError, PermissionError) as e:
            print(f"File system error getting scenes for {story_id}: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"JSON decode error getting scenes for {story_id}: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error getting scenes for {story_id}: {e}")
            return []
        else:
            return []

    async def get_scene_by_id(self, story_id: str, scene_id: str) -> Optional[Dict]:
        """Get a specific scene."""
        try:
            story_path = Path(self.storage_path) / "stories" / story_id
            scenes_file = story_path / "scenes.json"

            if scenes_file.exists():
                scenes = json.loads(scenes_file.read_text(encoding='utf-8'))
                for scene in scenes:
                    if scene.get('id') == scene_id:
                        return scene

        except (OSError, IOError, PermissionError) as e:
            print(f"File system error getting scene {scene_id} for {story_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON decode error getting scene {scene_id} for {story_id}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error getting scene {scene_id} for {story_id}: {e}")
            return None
        else:
            return None

    async def update_scene_state(self, story_id: str, scene_id: str, state_data: Dict) -> bool:
        """Update scene state."""
        try:
            story_path = Path(self.storage_path) / "stories" / story_id
            scenes_file = story_path / "scenes.json"

            if scenes_file.exists():
                scenes = json.loads(scenes_file.read_text(encoding='utf-8'))

                for scene in scenes:
                    if scene.get('id') == scene_id:
                        scene.update(state_data)
                        break

                scenes_file.write_text(json.dumps(scenes, indent=2), encoding='utf-8')
                return True

        except (OSError, IOError, PermissionError) as e:
            print(f"File system error updating scene {scene_id} for {story_id}: {e}")
            return False
        except json.JSONDecodeError as e:
            print(f"JSON decode error updating scene {scene_id} for {story_id}: {e}")
            return False
        except (TypeError, ValueError) as e:
            print(f"JSON encode error updating scene {scene_id} for {story_id}: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error updating scene {scene_id} for {story_id}: {e}")
            return False
        else:
            return False

    async def _query_scenes(self, story_path: Path, params: Dict) -> List[Dict]:
        """Query scenes data."""
        try:
            scenes_file = story_path / "scenes.json"
            if scenes_file.exists():
                return json.loads(scenes_file.read_text(encoding='utf-8'))

        except (OSError, IOError, PermissionError) as e:
            print(f"File system error querying scenes: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"JSON decode error querying scenes: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error querying scenes: {e}")
            return []
        else:
            return []

    async def _query_timeline(self, story_path: Path, params: Dict) -> List[Dict]:
        """Query timeline data."""
        try:
            timeline_file = story_path / "timeline.json"
            if timeline_file.exists():
                return json.loads(timeline_file.read_text(encoding='utf-8'))

        except (OSError, IOError, PermissionError) as e:
            print(f"File system error querying timeline: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"JSON decode error querying timeline: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error querying timeline: {e}")
            return []
        else:
            return []

    async def _update_scenes(self, story_path: Path, params: Dict) -> bool:
        """Update scenes data."""
        # Implementation depends on the specific update needed
        return True

    async def _update_timeline(self, story_path: Path, params: Dict) -> bool:
        """Update timeline data."""
        # Implementation depends on the specific update needed
        return True
