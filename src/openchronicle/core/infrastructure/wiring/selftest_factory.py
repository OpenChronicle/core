"""Selftest container factory — builds a CoreContainer with a StubLLMAdapter."""

from __future__ import annotations

from openchronicle.core.infrastructure.llm.stub_adapter import StubLLMAdapter
from openchronicle.core.infrastructure.wiring.container import CoreContainer


def create_selftest_container(
    *,
    db_path: str,
    config_dir: str,
    plugin_dir: str,
    output_dir: str,
) -> CoreContainer:
    """Build a container wired with a stub LLM for selftest scenarios."""
    return CoreContainer(
        db_path=db_path,
        config_dir=config_dir,
        plugin_dir=plugin_dir,
        output_dir=output_dir,
        llm=StubLLMAdapter(),
    )
