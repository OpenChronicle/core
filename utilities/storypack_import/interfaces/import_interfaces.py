#!/usr/bin/env python3
"""
OpenChronicle Storypack Import Interfaces

This module defines the interfaces for the modular storypack import system,
following SOLID principles with focused, segregated interfaces.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ContentFile:
    """Represents a discovered content file."""
    path: Path
    category: str
    size: int
    encoding: str = 'utf-8'
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ImportContext:
    """Context information for import operations."""
    source_path: Path
    storypack_name: str
    import_mode: str  # 'basic' or 'ai'
    target_path: Path
    templates_available: List[str]
    ai_available: bool = False


@dataclass
class ImportResult:
    """Result of an import operation."""
    success: bool
    storypack_name: str
    storypack_path: Optional[Path]
    files_processed: int
    generated_files: List[Path]
    processing_time: float
    created_at: str
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class IContentParser(ABC):
    """Interface for content parsing operations."""
    
    @abstractmethod
    def discover_files(self, source_path: Path) -> Dict[str, List[ContentFile]]:
        """Discover and categorize files in the source directory."""
        pass
    
    @abstractmethod
    def categorize_file(self, file_path: Path) -> str:
        """Categorize a single file based on its path and name."""
        pass
    
    @abstractmethod
    def read_file_content(self, file_path: Path) -> Tuple[str, str]:
        """Read file content and detect encoding."""
        pass
    
    @abstractmethod
    def validate_file_format(self, file_path: Path) -> bool:
        """Validate that a file format is supported."""
        pass


class IMetadataExtractor(ABC):
    """Interface for metadata extraction from content."""
    
    @abstractmethod
    def extract_basic_metadata(self, content: str, file_path: Path) -> Dict[str, Any]:
        """Extract basic metadata from content."""
        pass
    
    @abstractmethod
    def detect_content_structure(self, content: str) -> Dict[str, Any]:
        """Analyze content structure and organization."""
        pass
    
    @abstractmethod
    def extract_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract filesystem metadata."""
        pass


class IStructureAnalyzer(ABC):
    """Interface for analyzing directory structures."""
    
    @abstractmethod
    def analyze_directory_structure(self, source_path: Path) -> Dict[str, Any]:
        """Analyze the overall directory structure."""
        pass
    
    @abstractmethod
    def suggest_organization(self, discovered_files: Dict[str, List[ContentFile]]) -> Dict[str, str]:
        """Suggest how to organize content in the storypack."""
        pass
    
    @abstractmethod
    def validate_source_structure(self, source_path: Path) -> Tuple[bool, List[str]]:
        """Validate source directory structure."""
        pass


class IAIProcessor(ABC):
    """Interface for AI-powered content processing."""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize AI capabilities."""
        pass
    
    @abstractmethod
    async def analyze_content(self, content: str, file_path: Path, context: ImportContext) -> Dict[str, Any]:
        """Analyze content using AI capabilities."""
        pass
    
    @abstractmethod
    async def extract_entities(self, content: str, entity_type: str) -> List[Dict[str, Any]]:
        """Extract specific entities (characters, locations, etc.) from content."""
        pass
    
    @abstractmethod
    async def classify_content_type(self, content: str) -> Dict[str, Any]:
        """Classify content type and determine processing approach."""
        pass
    
    @abstractmethod
    async def test_capabilities(self) -> Tuple[bool, List[str]]:
        """Test AI capabilities and return status."""
        pass


class IContentClassifier(ABC):
    """Interface for content classification."""
    
    @abstractmethod
    def classify_by_content(self, content: str) -> str:
        """Classify content based on its actual content."""
        pass
    
    @abstractmethod
    def classify_by_structure(self, content: str) -> Dict[str, Any]:
        """Analyze content structure patterns."""
        pass
    
    @abstractmethod
    def get_confidence_score(self, content: str, category: str) -> float:
        """Get confidence score for content categorization."""
        pass


class IValidationEngine(ABC):
    """Interface for content validation."""
    
    @abstractmethod
    def validate_content_format(self, content: str, expected_type: str) -> Tuple[bool, List[str]]:
        """Validate content format against expected type."""
        pass
    
    @abstractmethod
    def validate_import_readiness(self, context: ImportContext) -> Tuple[bool, List[str]]:
        """Validate that system is ready for import."""
        pass
    
    @abstractmethod
    def validate_storypack_structure(self, storypack_path: Path) -> Tuple[bool, List[str]]:
        """Validate generated storypack structure."""
        pass


class IStorypackBuilder(ABC):
    """Interface for storypack structure building."""
    
    @abstractmethod
    def create_storypack_structure(self, context: ImportContext) -> Path:
        """Create the directory structure for a new storypack."""
        pass
    
    @abstractmethod
    def generate_metadata_file(self, context: ImportContext, content_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the meta.json file for the storypack."""
        pass
    
    @abstractmethod
    def organize_content_files(self, discovered_files: Dict[str, List[ContentFile]], 
                              target_path: Path) -> Dict[str, List[Path]]:
        """Organize and copy content files to storypack structure."""
        pass


class ITemplateEngine(ABC):
    """Interface for template processing."""
    
    @abstractmethod
    def load_templates(self, templates_dir: Path) -> Dict[str, Dict[str, Any]]:
        """Load all available templates."""
        pass
    
    @abstractmethod
    def select_template(self, content_analysis: Dict[str, Any]) -> Optional[str]:
        """Select appropriate template based on content analysis."""
        pass
    
    @abstractmethod
    def process_template(self, template_name: str, context: ImportContext) -> Dict[str, Any]:
        """Process template with given context."""
        pass


class IOutputFormatter(ABC):
    """Interface for output formatting."""
    
    @abstractmethod
    def format_import_result(self, result: ImportResult, format_type: str = 'summary') -> str:
        """Format import result for display."""
        pass
    
    @abstractmethod
    def generate_report(self, result: ImportResult, report_type: str = 'standard') -> Dict[str, Any]:
        """Generate comprehensive import report."""
        pass
    
    @abstractmethod
    def save_report(self, report: Dict[str, Any], output_path: Path, format_type: str = 'json') -> bool:
        """Save report to file."""
        pass
    
    @abstractmethod
    def format_import_summary(self, result: ImportResult) -> str:
        """Format import results for display."""
        pass
    
    @abstractmethod
    def generate_readme(self, context: ImportContext, content_summary: Dict[str, Any]) -> str:
        """Generate README content for the storypack."""
        pass
    
    @abstractmethod
    def format_error_report(self, errors: List[str], warnings: List[str]) -> str:
        """Format error and warning messages."""
        pass
