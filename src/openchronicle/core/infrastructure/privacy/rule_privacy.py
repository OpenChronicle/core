from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from openchronicle.core.domain.models.privacy_report import PrivacyReport
from openchronicle.core.domain.ports.privacy_gate_port import PrivacyGatePort

_LOCAL_PROVIDERS = {"ollama", "stub"}


def is_external_provider(provider: str) -> bool:
    return provider.strip().lower() not in _LOCAL_PROVIDERS


_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){1}\d{3}[-.\s]?\d{4}\b")
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CC_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
_API_KEY_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
]


def _luhn_check(number: str) -> bool:
    total = 0
    reverse_digits = number[::-1]
    for idx, ch in enumerate(reverse_digits):
        digit = ord(ch) - 48
        if idx % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _valid_ip(candidate: str) -> bool:
    parts = candidate.split(".")
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit():
            return False
        value = int(part)
        if value < 0 or value > 255:
            return False
    return True


@dataclass(frozen=True)
class _CategoryResult:
    count: int
    redacted_text: str


class RulePrivacyGate(PrivacyGatePort):
    def analyze_and_apply(
        self,
        *,
        text: str,
        mode: str,
        redact_style: str,
        categories: list[str],
    ) -> tuple[str, PrivacyReport]:
        action = mode if mode in {"off", "warn", "redact", "block"} else "off"
        active_categories = [cat for cat in categories if cat in self._handlers()]

        if action == "off":
            return text, PrivacyReport(
                categories=[],
                counts={},
                action="off",
                redactions_applied=False,
                summary="Privacy gate off.",
            )

        working_text = text
        counts: dict[str, int] = {}
        for category in active_categories:
            result = self._handlers()[category](working_text, redact_style if action == "redact" else None)
            counts[category] = result.count
            working_text = result.redacted_text

        detected = [cat for cat in active_categories if counts.get(cat, 0) > 0]
        summary = "No PII detected."
        if detected:
            parts = [f"{cat}({counts[cat]})" for cat in detected]
            summary = "Detected: " + ", ".join(parts) + "."

        redactions_applied = action == "redact" and any(counts.values())
        report = PrivacyReport(
            categories=detected,
            counts={cat: counts[cat] for cat in detected},
            action=action,
            redactions_applied=redactions_applied,
            summary=summary,
        )

        return working_text, report

    def _handlers(self) -> dict[str, Callable[[str, str | None], _CategoryResult]]:
        return {
            "email": self._handle_email,
            "phone": self._handle_phone,
            "ip": self._handle_ip,
            "ssn": self._handle_ssn,
            "cc": self._handle_cc,
            "api_key": self._handle_api_key,
        }

    def _handle_email(self, text: str, redact_style: str | None) -> _CategoryResult:
        matches = list(_EMAIL_RE.finditer(text))
        count = len(matches)
        redacted = text
        if redact_style == "mask" and count:
            redacted = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
        return _CategoryResult(count=count, redacted_text=redacted)

    def _handle_phone(self, text: str, redact_style: str | None) -> _CategoryResult:
        matches = list(_PHONE_RE.finditer(text))
        count = len(matches)
        redacted = text
        if redact_style == "mask" and count:
            redacted = _PHONE_RE.sub("[REDACTED_PHONE]", text)
        return _CategoryResult(count=count, redacted_text=redacted)

    def _handle_ip(self, text: str, redact_style: str | None) -> _CategoryResult:
        matches = [m for m in _IP_RE.finditer(text) if _valid_ip(m.group(0))]
        count = len(matches)
        redacted = text
        if redact_style == "mask" and count:
            redacted = _replace_matches(text, matches, "[REDACTED_IP]")
        return _CategoryResult(count=count, redacted_text=redacted)

    def _handle_ssn(self, text: str, redact_style: str | None) -> _CategoryResult:
        matches = list(_SSN_RE.finditer(text))
        count = len(matches)
        redacted = text
        if redact_style == "mask" and count:
            redacted = _SSN_RE.sub("[REDACTED_SSN]", text)
        return _CategoryResult(count=count, redacted_text=redacted)

    def _handle_cc(self, text: str, redact_style: str | None) -> _CategoryResult:
        matches = []
        for match in _CC_RE.finditer(text):
            digits = re.sub(r"\D", "", match.group(0))
            if 13 <= len(digits) <= 19 and _luhn_check(digits):
                matches.append(match)
        count = len(matches)
        redacted = text
        if redact_style == "mask" and count:
            redacted = _replace_matches(text, matches, "[REDACTED_CC]")
        return _CategoryResult(count=count, redacted_text=redacted)

    def _handle_api_key(self, text: str, redact_style: str | None) -> _CategoryResult:
        matches: list[re.Match[str]] = []
        for pattern in _API_KEY_PATTERNS:
            matches.extend(pattern.finditer(text))
        count = len(matches)
        redacted = text
        if redact_style == "mask" and count:
            redacted = _replace_matches(text, matches, "[REDACTED_API_KEY]")
        return _CategoryResult(count=count, redacted_text=redacted)


def _replace_matches(text: str, matches: list[re.Match[str]], token: str) -> str:
    if not matches:
        return text
    segments = []
    last_index = 0
    for match in sorted(matches, key=lambda m: m.start()):
        segments.append(text[last_index : match.start()])
        segments.append(token)
        last_index = match.end()
    segments.append(text[last_index:])
    return "".join(segments)
