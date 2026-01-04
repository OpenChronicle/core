# 🚫 DO NOT EDIT: guardrail test. Changes require CODEOWNERS approval.

import asyncio
import importlib

import pytest


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.mark.integration
def test_story_facade_smoke():
    try:
        b = importlib.import_module("openchronicle.infrastructure.bootstrap")
    except Exception:
        pytest.skip("bootstrap missing")
    get_facade = getattr(b, "get_facade", None)
    if not callable(get_facade):
        pytest.skip("facade getter not available")
    story = get_facade("story")
    if story is None:
        pytest.skip("story plugin not registered")
    # Adjust names if your facade differs
    sid = run(story.start_session(None))
    res = run(story.process_turn(sid, "hello"))
    assert sid
    assert res is not None
