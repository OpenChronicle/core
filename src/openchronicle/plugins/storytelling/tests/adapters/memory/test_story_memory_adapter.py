import pytest

from tests.contracts.ports.test_memory_port_contract import MemoryPortContract


@pytest.mark.contract
class TestStoryMemoryAdapter_Local(MemoryPortContract):
    def make_port(self):
        try:
            from openchronicle.plugins.storytelling.infrastructure.adapters.story_memory_adapter import (
                StoryMemoryAdapter,
            )
        except Exception:
            pytest.skip("story_memory_adapter not present")
        return StoryMemoryAdapter(backing_store=":memory:")
