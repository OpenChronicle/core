"""Canonical error code constants for LLM/provider-related failures."""

from __future__ import annotations

# Provider selection / configuration
PROVIDER_REQUIRED = "provider_required"
PROVIDER_NOT_CONFIGURED = "provider_not_configured"
INVALID_PROVIDER = "invalid_provider"
MISSING_API_KEY = "missing_api_key"
MISSING_PACKAGE = "missing_package"

# Transport/runtime
TIMEOUT = "timeout"
CONNECTION_ERROR = "connection_error"
UNKNOWN_ERROR = "unknown"
