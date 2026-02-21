"""System tools — health check."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from mcp.server.fastmcp import FastMCP

from openchronicle.core.application.use_cases import diagnose_runtime


def register(mcp: FastMCP) -> None:
    """Register system tools on the MCP server."""

    @mcp.tool()
    def health() -> dict[str, Any]:
        """Health check: database status, configuration, and provider environment summary.

        Returns diagnostics about the OC runtime including database reachability,
        config directory status, installed providers, and model config summary.
        """
        report = diagnose_runtime.execute()
        data = asdict(report)
        # Convert datetime to ISO string for JSON serialization
        if data.get("timestamp_utc"):
            data["timestamp_utc"] = data["timestamp_utc"].isoformat()
        if data.get("db_modified_utc"):
            data["db_modified_utc"] = data["db_modified_utc"].isoformat()
        return data
