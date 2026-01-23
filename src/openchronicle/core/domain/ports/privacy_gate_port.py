from __future__ import annotations

from abc import ABC, abstractmethod

from openchronicle.core.domain.models.privacy_report import PrivacyReport


class PrivacyGatePort(ABC):
    @abstractmethod
    def analyze_and_apply(
        self,
        *,
        text: str,
        mode: str,
        redact_style: str,
        categories: list[str],
    ) -> tuple[str, PrivacyReport]:
        raise NotImplementedError
