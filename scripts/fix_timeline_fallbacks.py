"""
Fix timeline fallback files to use proper dependency injection.
This removes all infrastructure imports from the domain layer.
"""
from pathlib import Path


def fix_timeline_fallback_files():
    """Fix all timeline fallback files to use dependency injection."""

    root_path = Path(__file__).parent.parent

    # Define the files to fix
    fallback_files = [
        "src/openchronicle/domain/services/timeline/shared/fallback_navigation.py",
        "src/openchronicle/domain/services/timeline/shared/fallback_state.py",
        "src/openchronicle/domain/services/timeline/shared/fallback_timeline.py"
    ]

    # Create a persistence port in domain
    persistence_port_path = root_path / "src" / "openchronicle" / "domain" / "ports" / "persistence_port.py"

    persistence_port_content = '''"""
Persistence port for domain layer operations.
Abstract interface for database operations without infrastructure dependencies.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union


class IPersistencePort(ABC):
    """Port for persistence operations in domain layer."""

    @abstractmethod
    async def init_database(self, story_id: str) -> bool:
        """Initialize database for story."""
        pass

    @abstractmethod
    async def execute_query(self, story_id: str, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute a database query."""
        pass

    @abstractmethod
    async def execute_update(self, story_id: str, query: str, params: Optional[Dict] = None) -> bool:
        """Execute a database update."""
        pass

    @abstractmethod
    async def get_scenes(self, story_id: str, limit: int = 5) -> List[Dict]:
        """Get scenes for navigation."""
        pass

    @abstractmethod
    async def get_scene_by_id(self, story_id: str, scene_id: str) -> Optional[Dict]:
        """Get a specific scene."""
        pass

    @abstractmethod
    async def update_scene_state(self, story_id: str, scene_id: str, state_data: Dict) -> bool:
        """Update scene state."""
        pass
'''

    if not persistence_port_path.exists():
        persistence_port_path.write_text(persistence_port_content, encoding='utf-8')
        print(f"✅ Created persistence port: {persistence_port_path.relative_to(root_path)}")

    # Fix each fallback file
    for file_path in fallback_files:
        full_path = root_path / file_path
        if full_path.exists():
            fix_fallback_file(full_path, root_path)

    print("\n🎯 Next Steps:")
    print("1. Create infrastructure adapter implementing IPersistencePort")
    print("2. Update dependency injection to wire persistence operations")
    print("3. Test that timeline operations still work")


def fix_fallback_file(file_path: Path, root_path: Path):
    """Fix a specific fallback file."""

    try:
        content = file_path.read_text(encoding='utf-8')

        # Remove commented infrastructure imports
        patterns_to_remove = [
            r'\s*# from src\.openchronicle\.infrastructure\.persistence import.*\n',
            r'\s*# from src\.openchronicle\.infrastructure\..*\n'
        ]

        for pattern in patterns_to_remove:
            import re
            content = re.sub(pattern, '', content)

        # Add dependency injection import at the top
        dependency_import = """from src.openchronicle.domain.ports.persistence_port import IPersistencePort
from typing import Optional
"""

        # Find the class definition and add dependency injection
        if "class " in content:
            # Add the import after existing imports
            import_section_end = content.find("class ")
            if import_section_end != -1:
                before_class = content[:import_section_end]
                after_class = content[import_section_end:]

                # Add dependency injection import if not already present
                if "IPersistencePort" not in before_class:
                    before_class += "\n" + dependency_import + "\n"

                content = before_class + after_class

        # Replace direct function calls with dependency injection calls
        replacements = [
            ("init_database(", "await self.persistence_port.init_database("),
            ("execute_query(", "await self.persistence_port.execute_query("),
            ("execute_update(", "await self.persistence_port.execute_update("),
        ]

        for old, new in replacements:
            content = content.replace(old, new)

        # Update class constructor to accept persistence_port
        if "__init__" in content:
            # Find the __init__ method and update it
            import re
            init_pattern = r'def __init__\(self([^)]*)\):'
            init_match = re.search(init_pattern, content)

            if init_match:
                current_params = init_match.group(1)
                if "persistence_port" not in current_params:
                    new_params = current_params + ", persistence_port: IPersistencePort"
                    new_init = f"def __init__(self{new_params}):"
                    content = re.sub(init_pattern, new_init, content)

                    # Add the assignment in the constructor
                    constructor_body_start = content.find(new_init) + len(new_init)
                    indent = "        "  # Adjust based on actual indentation
                    injection_line = f"\n{indent}self.persistence_port = persistence_port\n"
                    content = content[:constructor_body_start] + injection_line + content[constructor_body_start:]

        # Write the updated content
        file_path.write_text(content, encoding='utf-8')
        print(f"✅ Fixed: {file_path.relative_to(root_path)}")

    except Exception as e:
        print(f"⚠️ Error fixing {file_path}: {e}")


if __name__ == "__main__":
    fix_timeline_fallback_files()
