# 🚫 DO NOT EDIT: guardrail test. Changes require CODEOWNERS approval.

import pytest


@pytest.mark.contract
class ContentAnalysisPortContract:
    def make_port(self):
        raise NotImplementedError

    def test_basic_analyze(self):
        port = self.make_port()
        out = port.analyze_text("Alice meets Bob in Paris.")
        assert isinstance(out, dict)
