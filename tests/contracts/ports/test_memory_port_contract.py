# 🚫 DO NOT EDIT: guardrail test. Changes require CODEOWNERS approval.

import pytest


@pytest.mark.contract
class MemoryPortContract:
    def make_port(self):  # implemented by adapter tests
        raise NotImplementedError

    def test_load_then_save_roundtrip(self):
        port = self.make_port()
        sid = "test-session-1"
        state = {"facts": [{"k": "mood", "v": "curious"}]}
        try:
            _ = port.get_session_memory(sid)
        except Exception:
            pass
        port.save_memory(sid, state)
        got = port.get_session_memory(sid)
        assert got and got.get("facts") and got["facts"][0]["k"] == "mood"
