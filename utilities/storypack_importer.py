#!/usr/bin/env python3
"""
OpenChronicle Storypack Import Engine

This module provides the core functionality for importing raw source material
and converting it into structured OpenChronicle storypacks using AI analysis
and template processing.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, UTC

# Import OpenChronicle infrastructure
from utilities.logging_system import get_logger, log_system_event, log_error, log_info, log_warning
from core.model_adapter import ModelManager
from core.content_analyzer import ContentAnalyzer


class StorypackImporter:
    """
    Main orchestration class for importing and processing source material
    into OpenChronicle storypacks.
    """
    
    def __init__(self, source_dir: Optional[Path] = None, output_dir: Optional[Path] = None):
        """Initialize the importer with source and output directories."""
        self.logger = get_logger()
        self.root_dir = Path(__file__).parent.parent
        
        # Set default directories
        self.source_dir = source_dir or self.root_dir / "analysis" / "import_staging"
        self.output_dir = output_dir or self.root_dir / "storage" / "storypacks"
        self.templates_dir = self.root_dir / "templates"
        
        # Initialize ModelManager for AI processing
        self.model_manager = None
        self.content_analyzer = None
        self.ai_available = False
        
        # Supported file types
        self.supported_extensions = {'.txt', '.md', '.json'}
        
        # Content type mappings
        self.content_categories = {
            'characters': ['characters', 'people', 'npcs', 'char'],
            'locations': ['locations', 'places', 'settings', 'loc'],
            'lore': ['lore', 'history', 'background', 'world', 'canon'],
            'narrative': ['story', 'plot', 'scenes', 'narrative', 'chapters']
        }
        
        log_system_event("storypack_importer", "Import engine initialized", {
            "source_dir": str(self.source_dir),
            "output_dir": str(self.output_dir),
            "templates_dir": str(self.templates_dir)
        })
    
    def initialize_ai(self) -> bool:
        """Initialize AI capabilities if available."""
        try:
            self.model_manager = ModelManager()
            available_adapters = self.model_manager.get_available_adapters()
            
            if available_adapters:
                # Initialize content analyzer with model manager
                self.content_analyzer = ContentAnalyzer(self.model_manager)
                self.ai_available = True
                log_system_event("storypack_importer", "AI capabilities initialized", {
                    "available_adapters": available_adapters,
                    "ai_enabled": True,
                    "content_analyzer": True
                })
                return True
            else:
                self.logger.warning("No LLM adapters available - falling back to manual processing")
                log_system_event("storypack_importer", "AI unavailable", {
                    "ai_enabled": False,
                    "fallback_mode": "manual"
                })
                return False
        except Exception as e:
            self.logger.error(f"Failed to initialize AI capabilities: {e}")
            log_system_event("storypack_importer", "AI initialization failed", {
                "error": str(e),
                "ai_enabled": False
            })
            return False

    async def test_ai_capabilities(self):
        """Test AI models and their capabilities for import operations."""
        log_info("Testing AI model capabilities for storypack import...")
        
        # Find working models for analysis
        working_models = await self.content_analyzer.find_working_analysis_models()
        
        if not working_models:
            log_warning("No working AI models found! Import will use basic text processing only.")
            print("\n>>> WARNING: No AI models available for enhanced import processing!")
            print("    The import will proceed with basic functionality only.")
            return False
        
        print(f"\n>>> AI Model Discovery Results:")
        print(f"    Found {len(working_models)} working model(s) for analysis")
        
        # Show the top models with their scores
        for i, model in enumerate(working_models[:3], 1):
            status = "[SELECTED]" if i == 1 else "[BACKUP]"
            print(f"    {i}. {model['name']} {status}")
            print(f"       Score: {model['suitability_score']:.1f}/100")
            print(f"       Response time: {model.get('response_time', 0):.2f}s")
            if model.get('suitability_reason'):
                print(f"       Suitability: {model['suitability_reason']}")
            print()
        
        # Test the top model with a sample analysis
        best_model = working_models[0]['name']
        log_info(f"Testing advanced capabilities with model: {best_model}")
        
        test_content = """
        # Chapter 1: The Beginning
        
        Sarah walked through the misty forest, her heart pounding with anticipation. 
        The ancient trees seemed to whisper secrets of the past, and she knew her 
        adventure was just beginning.
        
        **Characters:**
        - Sarah: A young explorer with a brave heart
        - The Forest Spirit: An ancient guardian of the woods
        """
        
        try:
            analysis = await self.content_analyzer.analyze_imported_content(
                test_content, "Chapter 1", "test_analysis"
            )
            
            if analysis and analysis.get('characters'):
                print(f">>> AI Analysis Test: SUCCESS")
                print(f"    Model '{best_model}' successfully analyzed test content")
                print(f"    Detected {len(analysis['characters'])} character(s)")
                print(f"    Analysis depth: {analysis.get('complexity', 'Unknown')}")
                log_info("AI capabilities test passed - enhanced import available")
                return True
            else:
                print(f">>> AI Analysis Test: LIMITED")
                print(f"    Model responded but analysis was incomplete")
                log_warning("AI model available but analysis capabilities limited")
                return True  # Still usable, just limited
                
        except Exception as e:
            print(f">>> AI Analysis Test: FAILED")
            print(f"    Error: {str(e)[:100]}...")
            log_error(f"AI analysis test failed: {e}")
            return False
    
    def discover_source_files(self) -> Dict[str, List[Path]]:
        """
        Discover and categorize source files in the staging directory.
        
        Returns:
            Dictionary mapping content categories to lists of file paths
        """
        discovered_files = {category: [] for category in self.content_categories.keys()}
        discovered_files['uncategorized'] = []
        
        if not self.source_dir.exists():
            self.logger.warning(f"Source directory does not exist: {self.source_dir}")
            return discovered_files
        
        # Scan for files
        for file_path in self.source_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                category = self._categorize_file(file_path)
                discovered_files[category].append(file_path)
        
        # Log discovery results
        total_files = sum(len(files) for files in discovered_files.values())
        log_system_event("storypack_importer", "File discovery completed", {
            "total_files": total_files,
            "categories": {cat: len(files) for cat, files in discovered_files.items()},
            "source_directory": str(self.source_dir)
        })
        
        return discovered_files
    
    def _categorize_file(self, file_path: Path) -> str:
        """
        Categorize a file based on its path and name.
        
        Args:
            file_path: Path to the file to categorize
            
        Returns:
            Category name or 'uncategorized'
        """
        # Check parent directory name
        parent_name = file_path.parent.name.lower()
        for category, keywords in self.content_categories.items():
            if any(keyword in parent_name for keyword in keywords):
                return category
        
        # Check filename
        filename = file_path.stem.lower()
        for category, keywords in self.content_categories.items():
            if any(keyword in filename for keyword in keywords):
                return category
        
        return 'uncategorized'
    
    def load_templates(self) -> Dict[str, Dict]:
        """
        Load all available templates from the templates directory.
        
        Returns:
            Dictionary mapping template names to template data
        """
        templates = {}
        
        if not self.templates_dir.exists():
            self.logger.error(f"Templates directory does not exist: {self.templates_dir}")
            return templates
        
        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                    templates[template_file.stem] = template_data
                    self.logger.info(f"Loaded template: {template_file.stem}")
            except Exception as e:
                self.logger.error(f"Failed to load template {template_file}: {e}")
        
        log_system_event("storypack_importer", "Templates loaded", {
            "template_count": len(templates),
            "templates": list(templates.keys())
        })
        
        return templates
    
    def validate_import_readiness(self) -> Tuple[bool, List[str]]:
        """
        Validate that the system is ready for import operations.
        
        Returns:
            Tuple of (is_ready, list_of_issues)
        """
        issues = []
        
        # Check source directory
        if not self.source_dir.exists():
            issues.append(f"Source directory does not exist: {self.source_dir}")
        
        # Check templates directory
        if not self.templates_dir.exists():
            issues.append(f"Templates directory does not exist: {self.templates_dir}")
        
        # Check output directory (create if needed)
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            issues.append(f"Cannot create output directory {self.output_dir}: {e}")
        
        # Check for source files
        if self.source_dir.exists():
            source_files = list(self.source_dir.rglob("*"))
            if not any(f.is_file() and f.suffix.lower() in self.supported_extensions 
                      for f in source_files):
                issues.append("No supported source files found in staging directory")
        
        # Check for templates
        if self.templates_dir.exists():
            template_files = list(self.templates_dir.glob("*.json"))
            if not template_files:
                issues.append("No template files found in templates directory")
        
        is_ready = len(issues) == 0
        
        log_system_event("storypack_importer", "Import readiness validation", {
            "is_ready": is_ready,
            "issues_count": len(issues),
            "issues": issues
        })
        
        return is_ready, issues
    
    def create_storypack_structure(self, storypack_name: str) -> Path:
        """
        Create the basic directory structure for a new storypack.
        
        Args:
            storypack_name: Name of the storypack to create
            
        Returns:
            Path to the created storypack directory
        """
        storypack_path = self.output_dir / storypack_name
        
        # Create main directory
        storypack_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        subdirs = ['characters', 'canon', 'memory']
        for subdir in subdirs:
            (storypack_path / subdir).mkdir(exist_ok=True)
        
        log_system_event("storypack_importer", "Storypack structure created", {
            "storypack_name": storypack_name,
            "storypack_path": str(storypack_path),
            "subdirectories": subdirs
        })
        
        return storypack_path
    
    def get_import_summary(self) -> Dict[str, Any]:
        """
        Generate a summary of the current import environment.
        
        Returns:
            Dictionary containing import environment information
        """
        # Discover files
        discovered_files = self.discover_source_files()
        
        # Load templates
        templates = self.load_templates()
        
        # Check readiness
        is_ready, issues = self.validate_import_readiness()
        
        summary = {
            "timestamp": datetime.now(UTC).isoformat(),
            "source_directory": str(self.source_dir),
            "output_directory": str(self.output_dir),
            "templates_directory": str(self.templates_dir),
            "ai_available": self.ai_available,
            "discovered_files": {
                cat: [str(f) for f in files] 
                for cat, files in discovered_files.items()
            },
            "available_templates": list(templates.keys()),
            "import_ready": is_ready,
            "validation_issues": issues,
            "supported_extensions": list(self.supported_extensions)
        }
        
        return summary
    
    def run_basic_import(self, storypack_name: str) -> Dict[str, Any]:
        """
        Run a basic import process without AI enhancement.
        
        Args:
            storypack_name: Name of the storypack to create
            
        Returns:
            Dictionary containing import results
        """
        self.logger.info(f"Starting basic import for storypack: {storypack_name}")
        
        # Validate readiness
        is_ready, issues = self.validate_import_readiness()
        if not is_ready:
            error_msg = f"Import validation failed: {issues}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg, "issues": issues}
        
        # Discover source files
        discovered_files = self.discover_source_files()
        
        # Load templates
        templates = self.load_templates()
        
        # Create storypack structure
        storypack_path = self.create_storypack_structure(storypack_name)
        
        # Create basic meta.json from template
        if 'meta_template' in templates:
            meta_data = self._create_basic_meta(storypack_name, templates['meta_template'])
            meta_path = storypack_path / "meta.json"
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, indent=2)
            self.logger.info(f"Created meta.json for {storypack_name}")
        
        result = {
            "success": True,
            "storypack_name": storypack_name,
            "storypack_path": str(storypack_path),
            "discovered_files": {
                cat: [str(f) for f in files] 
                for cat, files in discovered_files.items()
            },
            "templates_used": list(templates.keys()),
            "created_files": ["meta.json"]
        }
        
        log_system_event("storypack_importer", "Basic import completed", result)
        
        return result
    
    def _create_basic_meta(self, storypack_name: str, meta_template: Dict) -> Dict:
        """Create basic metadata from template."""
        # Start with template structure
        meta_data = meta_template.copy()
        
        # Remove template-specific fields
        if 'template_info' in meta_data:
            del meta_data['template_info']
        
        # Set basic required fields
        meta_data.update({
            "name": storypack_name,
            "title": storypack_name.replace('_', ' ').title(),
            "version": "1.0.0",
            "description": f"Imported storypack: {storypack_name}",
            "author": "OpenChronicle Import Tool",
            "created": datetime.now(UTC).strftime('%Y-%m-%d'),
            "last_modified": datetime.now(UTC).strftime('%Y-%m-%d')
        })
        
        # Clean up optional fields marked for deletion
        self._clean_optional_fields(meta_data)
        
        return meta_data
    
    def _clean_optional_fields(self, data: Any) -> None:
        """Recursively remove fields marked with '_optional': True."""
        if isinstance(data, dict):
            keys_to_remove = []
            for key, value in data.items():
                if isinstance(value, dict):
                    if value.get('_optional') is True:
                        keys_to_remove.append(key)
                    else:
                        # Remove just the _optional marker if it exists
                        if '_optional' in value:
                            del value['_optional']
                        self._clean_optional_fields(value)
                elif isinstance(value, list):
                    for item in value:
                        self._clean_optional_fields(item)
            
            # Remove optional fields
            for key in keys_to_remove:
                del data[key]
        elif isinstance(data, list):
            for item in data:
                self._clean_optional_fields(item)

    async def analyze_content_with_ai(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Analyze content using AI-powered content analyzer."""
        try:
            log_system_event("storypack_importer", "AI content analysis started", {
                "file": file_path.name,
                "content_length": len(content)
            })
            
            if not self.ai_available or not self.content_analyzer:
                raise Exception("AI capabilities not available")
            
            # First, determine content category
            category_result = await self.content_analyzer.analyze_content_category(content)
            primary_category = category_result.get("primary_category", "unknown")
            
            # Extract specific data based on category
            extracted_data = {}
            if primary_category == "character":
                extracted_data = await self.content_analyzer.extract_character_data(content)
            elif primary_category == "location":
                extracted_data = await self.content_analyzer.extract_location_data(content)
            elif primary_category == "lore":
                extracted_data = await self.content_analyzer.extract_lore_data(content)
            else:
                # For other content types, use general analysis
                extracted_data = {"content": content, "type": primary_category}
            
            # Combine category analysis with extracted data
            result = {
                "file_path": str(file_path),
                "category_analysis": category_result,
                "extracted_data": extracted_data,
                "processing_timestamp": datetime.now(UTC).isoformat(),
                "source_content_length": len(content),
                "ai_processing": True
            }
            
            log_system_event("storypack_importer", "AI content analysis completed", {
                "file": file_path.name,
                "category": primary_category,
                "confidence": extracted_data.get('confidence', 0.0),
                "success": True
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"AI content analysis failed for {file_path.name}: {e}")
            log_system_event("storypack_importer", "AI content analysis failed", {
                "file": file_path.name,
                "error": str(e),
                "fallback_used": True
            })
            
            return {
                "file_path": str(file_path),
                "error": str(e),
                "fallback_content": content,
                "processing_timestamp": datetime.now(UTC).isoformat(),
                "ai_processing": False
            }

    async def run_ai_import(self, storypack_name: str) -> Dict[str, Any]:
        """Run a full AI-powered import process."""
        try:
            log_system_event("storypack_importer", "AI import process started", {
                "storypack_name": storypack_name
            })
            
            # Validate readiness
            is_ready, issues = self.validate_import_readiness()
            if not is_ready:
                return {
                    "success": False,
                    "error": "Import validation failed",
                    "issues": issues
                }
            
            # Initialize AI if not already done
            if not self.ai_available:
                if not self.initialize_ai():
                    return {
                        "success": False,
                        "error": "AI initialization failed"
                    }
            
            # Discover and analyze files
            discovered_files = self.discover_source_files()
            analysis_results = []
            
            for category, files in discovered_files.items():
                for file_path in files:
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        analysis = await self.analyze_content_with_ai(file_path, content)
                        analysis_results.append(analysis)
                    except Exception as e:
                        self.logger.error(f"Failed to process {file_path}: {e}")
            
            # Generate metadata for the entire storypack
            all_content = []
            for result in analysis_results:
                if "fallback_content" in result:
                    all_content.append(result["fallback_content"])
                elif "extracted_data" in result and "content" in result["extracted_data"]:
                    all_content.append(result["extracted_data"]["content"])
            
            metadata = {}
            if self.content_analyzer:
                metadata = await self.content_analyzer.generate_import_metadata(all_content, storypack_name)
            
            # Create storypack structure
            storypack_path = self.create_storypack_structure(storypack_name)
            
            # Save analysis results
            analysis_file = storypack_path / "import_analysis.json"
            analysis_data = {
                "storypack_name": storypack_name,
                "import_timestamp": datetime.now(UTC).isoformat(),
                "metadata": metadata,
                "analysis_results": analysis_results,
                "processing_summary": {
                    "total_files": len(analysis_results),
                    "ai_processed": len([r for r in analysis_results if r.get("ai_processing", False)]),
                    "categories": list(set(r.get("category_analysis", {}).get("primary_category", "unknown") 
                                         for r in analysis_results))
                }
            }
            
            with analysis_file.open('w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2)
            
            log_system_event("storypack_importer", "AI import process completed", {
                "storypack_name": storypack_name,
                "files_processed": len(analysis_results),
                "output_path": str(storypack_path)
            })
            
            return {
                "success": True,
                "storypack_name": storypack_name,
                "storypack_path": str(storypack_path),
                "files_processed": len(analysis_results),
                "analysis_results": analysis_results,
                "metadata": metadata
            }
            
        except Exception as e:
            self.logger.error(f"AI import process failed: {e}")
            log_system_event("storypack_importer", "AI import process failed", {
                "storypack_name": storypack_name,
                "error": str(e)
            })
            
            return {
                "success": False,
                "error": str(e),
                "storypack_name": storypack_name
            }


# Convenience function for quick testing
def quick_import_test(storypack_name: str = "test_import") -> Dict[str, Any]:
    """Quick test function for import functionality."""
    importer = StorypackImporter()
    importer.initialize_ai()
    return importer.run_basic_import(storypack_name)


if __name__ == "__main__":
    # Simple test when run directly
    print("OpenChronicle Storypack Importer")
    print("=" * 40)
    
    importer = StorypackImporter()
    
    # Get import summary
    summary = importer.get_import_summary()
    print(f"Source files found: {sum(len(files) for files in summary['discovered_files'].values())}")
    print(f"Templates available: {len(summary['available_templates'])}")
    print(f"AI available: {summary['ai_available']}")
    print(f"Import ready: {summary['import_ready']}")
    
    if summary['validation_issues']:
        print("Issues:")
        for issue in summary['validation_issues']:
            print(f"  - {issue}")
    
    # Run basic test if ready
    if summary['import_ready']:
        print("\nRunning basic import test...")
        result = quick_import_test()
        if result['success']:
            print(f"✅ Test import successful: {result['storypack_name']}")
        else:
            print(f"❌ Test import failed: {result.get('error', 'Unknown error')}")
