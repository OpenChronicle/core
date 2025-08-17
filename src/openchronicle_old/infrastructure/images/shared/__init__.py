"""
Shared Image System Components for OpenChronicle

This package contains shared data models, configuration management, and utilities
used across the image generation and processing systems.
"""

from .config_manager import ImageConfigManager
from .image_models import (
    AutoGenerateConfig,
    ImageConfig,
    ImageGenerationRequest,
    ImageGenerationResult,
    ImageMetadata,
    ImageProvider,
    ImageSize,
    ImageStats,
    ImageType,
    NamingConfig,
)
from .validation_utils import ImageValidationError, ImageValidator

__all__ = [
    # Data models and enums
    "ImageProvider",
    "ImageSize",
    "ImageType",
    "ImageGenerationRequest",
    "ImageGenerationResult",
    "ImageMetadata",
    "ImageStats",
    "ImageConfig",
    "NamingConfig",
    "AutoGenerateConfig",
    # Configuration management
    "ImageConfigManager",
    # Validation
    "ImageValidator",
    "ImageValidationError",
]
