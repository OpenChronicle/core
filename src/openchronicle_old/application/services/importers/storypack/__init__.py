"""
OpenChronicle Storypack Import Package

Modular storypack import system with SOLID architecture principles.
Replaces the monolithic storypack_importer.py with focused, testable components.
"""

# Explicit imports to replace wildcard imports
from .generators import OutputFormatter, StorypackBuilder, TemplateEngine
from .interfaces import (
    ContentFile,
    IAIProcessor,
    IContentClassifier,
    IContentParser,
    IMetadataExtractor,
    ImportContext,
    ImportResult,
    IOutputFormatter,
    IStorypackBuilder,
    IStructureAnalyzer,
    ITemplateEngine,
    IValidationEngine,
)
from .orchestrator import StorypackOrchestrator
from .parsers import ContentParser, MetadataExtractor, StructureAnalyzer
from .processors import AIProcessor, ContentClassifier, ValidationEngine

__all__ = [
    "StorypackOrchestrator",
    # Interfaces
    "IContentParser",
    "IMetadataExtractor",
    "IStructureAnalyzer",
    "IAIProcessor",
    "IContentClassifier",
    "IValidationEngine",
    "IStorypackBuilder",
    "ITemplateEngine",
    "IOutputFormatter",
    "ContentFile",
    "ImportContext",
    "ImportResult",
    # Parsers
    "ContentParser",
    "MetadataExtractor",
    "StructureAnalyzer",
    # Processors
    "AIProcessor",
    "ContentClassifier",
    "ValidationEngine",
    # Generators
    "StorypackBuilder",
    "TemplateEngine",
    "OutputFormatter",
]
