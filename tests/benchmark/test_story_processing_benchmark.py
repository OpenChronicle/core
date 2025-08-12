import asyncio
import pytest
from time import perf_counter

pytestmark = pytest.mark.benchmark

# Minimal smoke benchmark establishing a baseline for story processing latency.
# This uses a lightweight fake service graph; replace with real fixtures later.

class FakeLoggingService:
    async def log_info(self, *_, **__):
        return None
    async def log_error(self, *_, **__):
        return None

@pytest.mark.asyncio
async def test_story_processing_latency_baseline(benchmark):
    from openchronicle.application.services.story_processing_service import StoryProcessingService, StoryProcessingConfig

    class Dummy:
        async def get_story(self, story_id):
            class S:  # minimal stub
                def to_dict(self):
                    return {"id": story_id, "characters": []}
            return S()
        async def add_recent_event(self, *_, **__):
            return None

    service = StoryProcessingService(
        story_service=Dummy(),
        character_service=Dummy(),
        scene_service=Dummy(),
        memory_service=Dummy(),
        logging_service=FakeLoggingService(),
        cache_service=None,
        config=StoryProcessingConfig(enable_scene_logging=False, enable_content_flags=False),
    )

    async def run_once():
        return await service.process_story_input("story-1", "Hello world")

    start = perf_counter()
    result = await run_once()  # warm-up
    assert "ai_response" in result

    def sync_wrapper():
        return asyncio.get_event_loop().run_until_complete(run_once())

    benchmark(sync_wrapper)
    elapsed = perf_counter() - start
    print(f"Baseline story processing warm-up elapsed={elapsed:.4f}s")
