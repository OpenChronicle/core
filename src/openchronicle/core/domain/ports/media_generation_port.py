"""Port for generating media (images, video) from text prompts."""

from __future__ import annotations

from abc import ABC, abstractmethod

from openchronicle.core.domain.models.media import MediaRequest, MediaResult


class MediaGenerationPort(ABC):
    """Abstract interface for media generation providers."""

    @abstractmethod
    def generate(self, request: MediaRequest) -> MediaResult:
        """Generate media from a text prompt."""

    @abstractmethod
    def supported_media_types(self) -> list[str]:
        """Return supported media types (e.g. ['image'], ['image', 'video'])."""

    @abstractmethod
    def model_name(self) -> str:
        """Return the name of the generation model."""
