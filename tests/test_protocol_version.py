from __future__ import annotations

from pathlib import Path

from openchronicle.interfaces.cli.stdio import STDIO_RPC_PROTOCOL_VERSION


def test_stdio_rpc_protocol_version_matches_doc() -> None:
    doc_path = Path("docs/protocol/stdio_rpc_v1.md")
    doc_text = doc_path.read_text(encoding="utf-8")
    assert 'protocol_version: "1"' in doc_text
    assert STDIO_RPC_PROTOCOL_VERSION == "1"
