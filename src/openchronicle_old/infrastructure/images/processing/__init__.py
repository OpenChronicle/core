"""
Image Processing Components for OpenChronicle

This package contains components for image processing, storage, and format conversion.
Extracted and modularized from core/image_adapter.py and related functionality.
"""

from .format_converter import ImageFormat, ImageFormatConverter, ImageQuality
from .image_adapter import (
    ImageAdapter,
    ImageAdapterRegistry,
    MockImageAdapter,
    OpenAIImageAdapter,
    StabilityImageAdapter,
    create_image_registry,
)
from .storage_manager import ImageStorageManager

__all__ = [
    # Adapters
    "ImageAdapter",
    "OpenAIImageAdapter",
    "StabilityImageAdapter",
    "MockImageAdapter",
    "ImageAdapterRegistry",
    "create_image_registry",
    # Storage
    "ImageStorageManager",
    # Format conversion
    "ImageFormatConverter",
    "ImageFormat",
    "ImageQuality",
]
