from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PrivacyOutboundSettings:
    mode: str = "off"
    external_only: bool = True
    categories: list[str] = field(default_factory=lambda: ["email", "phone", "ip", "ssn", "cc", "api_key"])
    redact_style: str = "mask"
    log_events: bool = True


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_categories(value: str | None) -> list[str]:
    if value is None:
        return ["email", "phone", "ip", "ssn", "cc", "api_key"]
    return [item.strip() for item in value.split(",") if item.strip()]


def load_privacy_outbound_settings() -> PrivacyOutboundSettings:
    return PrivacyOutboundSettings(
        mode=os.getenv("OC_PRIVACY_OUTBOUND_MODE", "off"),
        external_only=_parse_bool(os.getenv("OC_PRIVACY_OUTBOUND_EXTERNAL_ONLY"), default=True),
        categories=_parse_categories(os.getenv("OC_PRIVACY_OUTBOUND_CATEGORIES")),
        redact_style=os.getenv("OC_PRIVACY_OUTBOUND_REDACT_STYLE", "mask"),
        log_events=_parse_bool(os.getenv("OC_PRIVACY_OUTBOUND_LOG"), default=True),
    )
