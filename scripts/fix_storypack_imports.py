"""
Fix application layer storypack import violations.
Replace relative interface imports with domain ports.
"""
import re
from pathlib import Path


def fix_storypack_imports():
    """Fix all storypack files to use domain ports instead of relative interface imports."""

    root_path = Path(__file__).parent.parent

    # Create interface port in domain for storypack operations
    interface_port_path = root_path / "src" / "openchronicle" / "domain" / "ports" / "storypack_port.py"

    interface_port_content = '''"""
Storypack interfaces port for domain layer operations.
Abstract interfaces for storypack import operations without dependency violations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union


class IStorypackProcessorPort(ABC):
    """Port for storypack processing operations."""

    @abstractmethod
    async def process_content(self, content: Any) -> Dict[str, Any]:
        """Process storypack content."""
        pass

    @abstractmethod
    async def validate_structure(self, data: Dict) -> bool:
        """Validate storypack structure."""
        pass

    @abstractmethod
    async def extract_metadata(self, content: Any) -> Dict[str, Any]:
        """Extract metadata from content."""
        pass

    @abstractmethod
    async def classify_content(self, content: str) -> str:
        """Classify content type."""
        pass

    @abstractmethod
    async def format_output(self, data: Dict) -> str:
        """Format output data."""
        pass

    @abstractmethod
    async def build_storypack(self, components: Dict) -> Dict[str, Any]:
        """Build storypack from components."""
        pass

    @abstractmethod
    async def generate_template(self, template_type: str) -> str:
        """Generate template content."""
        pass

    @abstractmethod
    async def parse_content(self, content: str) -> Dict[str, Any]:
        """Parse content structure."""
        pass

    @abstractmethod
    async def analyze_structure(self, data: Dict) -> Dict[str, Any]:
        """Analyze content structure."""
        pass

    @abstractmethod
    async def validate_content(self, content: Any) -> bool:
        """Validate content."""
        pass
'''

    if not interface_port_path.exists():
        interface_port_path.write_text(interface_port_content, encoding='utf-8')
        print(f"✅ Created storypack interface port: {interface_port_path.relative_to(root_path)}")

    # Define the storypack files to fix
    storypack_files = [
        "src/openchronicle/application/services/importers/storypack/generators/output_formatter.py",
        "src/openchronicle/application/services/importers/storypack/generators/storypack_builder.py",
        "src/openchronicle/application/services/importers/storypack/generators/template_engine.py",
        "src/openchronicle/application/services/importers/storypack/parsers/content_parser.py",
        "src/openchronicle/application/services/importers/storypack/parsers/metadata_extractor.py",
        "src/openchronicle/application/services/importers/storypack/parsers/structure_analyzer.py",
        "src/openchronicle/application/services/importers/storypack/processors/ai_processor.py",
        "src/openchronicle/application/services/importers/storypack/processors/content_classifier.py",
        "src/openchronicle/application/services/importers/storypack/processors/validation_engine.py"
    ]

    # Fix each storypack file
    for file_path in storypack_files:
        full_path = root_path / file_path
        if full_path.exists():
            fix_storypack_file(full_path, root_path)

    print("\\n🎯 Next Steps:")
    print("1. Create infrastructure adapter implementing IStorypackProcessorPort")
    print("2. Update dependency injection to wire storypack operations")
    print("3. Fix performance module violations")


def fix_storypack_file(file_path: Path, root_path: Path):
    """Fix a specific storypack file."""

    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content

        # Replace relative interface imports with domain port imports
        relative_import_patterns = [
            r'from \.\.interfaces\s+import.*',
            r'from \.\.interfaces\..*',
            r'import \.\.interfaces.*'
        ]

        for pattern in relative_import_patterns:
            content = re.sub(pattern, '', content)

        # Add domain port import at the top
        port_import = "from src.openchronicle.domain.ports.storypack_port import IStorypackProcessorPort\\n"

        # Find the best place to add the import (after existing imports)
        lines = content.split('\\n')
        import_insert_index = 0

        for i, line in enumerate(lines):
            if line.strip().startswith('from ') or line.strip().startswith('import '):
                import_insert_index = i + 1
            elif line.strip() and not line.strip().startswith('#'):
                break

        # Add the port import if not already present
        if "IStorypackProcessorPort" not in content:
            lines.insert(import_insert_index, port_import.strip())
            content = '\\n'.join(lines)

        # Update class constructors to accept storypack_processor_port
        if "__init__" in content:
            # Find the __init__ method and update it
            init_pattern = r'def __init__\\(self([^)]*)\\):'
            init_match = re.search(init_pattern, content)

            if init_match:
                current_params = init_match.group(1)
                if "storypack_processor_port" not in current_params:
                    new_params = current_params + ", storypack_processor_port: IStorypackProcessorPort"
                    new_init = f"def __init__(self{new_params}):"
                    content = re.sub(init_pattern, new_init, content)

                    # Add the assignment in the constructor
                    constructor_body_start = content.find(new_init) + len(new_init)
                    indent = "        "  # Adjust based on actual indentation
                    injection_line = f"\\n{indent}self.storypack_processor_port = storypack_processor_port\\n"
                    content = content[:constructor_body_start] + injection_line + content[constructor_body_start:]

        # Only write if content changed
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            print(f"✅ Fixed: {file_path.relative_to(root_path)}")
        else:
            print(f"ℹ️ No changes needed: {file_path.relative_to(root_path)}")

    except Exception as e:
        print(f"⚠️ Error fixing {file_path}: {e}")


if __name__ == "__main__":
    fix_storypack_imports()
