# 🚫 DO NOT EDIT: guardrail test. Changes require CODEOWNERS approval.

import pytest


@pytest.mark.contract
class PersistencePortContract:
    def make_port(self):
        raise NotImplementedError

    def test_story_crud_roundtrip(self):
        port = self.make_port()
        sid = port.create_story({"title": "T", "status": "draft"})
        doc = port.get_story(sid)
        assert doc and doc.get("title") == "T"
        port.update_story(sid, {"title": "T2"})
        doc2 = port.get_story(sid)
        assert doc2.get("title") == "T2"
