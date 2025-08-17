# 🚫 DO NOT EDIT: guardrail test. Changes require CODEOWNERS approval.

from .fakes.fake_memory_port import FakeMemoryPort


def test_fake_memory_roundtrip():
    port = FakeMemoryPort()
    sid = "s1"
    state = {"facts": [{"k": "mood", "v": "ok"}]}
    port.save_memory(sid, state)
    assert port.get_session_memory(sid)["facts"][0]["k"] == "mood"
