"""
Content Analysis System

A comprehensive content analysis system for extracting and analyzing story content.

Components:
- Detection: Content classification and type detection
- Extraction: Structured data extraction from content
- Routing: Model selection and routing recommendations
- Orchestrator: Main coordination interface

Usage:
    The orchestrator is now provided by plugins through domain ports; use ports.
"""

# Component modules
from . import detection, extraction, routing, shared

# Main components for direct access
from .detection import ContentClassifier, KeywordDetector, TransformerAnalyzer
from .extraction import CharacterExtractor, LocationExtractor, LoreExtractor
from .routing import ContentRouter, ModelSelector, RecommendationEngine

__version__ = "5.0.0"
__all__ = [
    # Component modules
    "detection",
    "extraction",
    "routing",
    "shared",
    # Individual components
    "ContentClassifier",
    "KeywordDetector",
    "TransformerAnalyzer",
    "CharacterExtractor",
    "LocationExtractor",
    "LoreExtractor",
    "ModelSelector",
    "ContentRouter",
    "RecommendationEngine",
]
