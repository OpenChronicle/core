"""
Script to migrate existing tests to hexagonal architecture structure.
Run this script to reorganize tests to match src/openchronicle structure.
"""
import os
import re
import shutil
from pathlib import Path


class TestMigrator:
    """Migrates tests from legacy structure to hexagonal architecture."""

    def __init__(self):
        self.root_path = Path(__file__).parent.parent
        self.tests_path = self.root_path / "tests"

        # Mapping from current structure to target hexagonal structure
        self.legacy_to_hex_mapping = {
            # Characters -> Domain Entities
            "tests/unit/characters": "tests/unit/domain/entities/characters",
            "tests/unit/scenes": "tests/unit/domain/entities/scenes",

            # Narrative/Timeline -> Domain Services
            "tests/unit/narrative": "tests/unit/domain/services/narrative",
            "tests/unit/timeline": "tests/unit/domain/services/timeline",

            # Database/Memory -> Infrastructure
            "tests/unit/database": "tests/unit/infrastructure/database",
            "tests/unit/memory": "tests/unit/infrastructure/memory",
            "tests/unit/cache": "tests/unit/infrastructure/cache",
            "tests/unit/backup": "tests/unit/infrastructure/backup",
            "tests/unit/backup_management": "tests/unit/infrastructure/backup",

            # Management -> Application layer
            "tests/unit/management": "tests/unit/application/orchestrators",

            # API/CLI -> Interfaces
            "tests/unit/api": "tests/unit/interfaces/api",
            "tests/unit/cli": "tests/unit/interfaces/cli",

            # Models/Registry -> Keep as is (already in good spots)
            "tests/unit/models": "tests/unit/application/models",
            "tests/unit/registry": "tests/unit/infrastructure/registry",

            # Security/Content -> Infrastructure
            "tests/unit/security": "tests/unit/infrastructure/security",
            "tests/unit/content": "tests/unit/infrastructure/content",
            "tests/unit/images": "tests/unit/infrastructure/content/images"
        }

    def migrate_all_tests(self):
        """Execute complete test migration."""
        print("🔄 Starting test migration to hexagonal architecture...")

        # 1. Create backup
        self._create_backup()

        # 2. Analyze current structure
        self._analyze_current_structure()

        # 3. Create target directories
        self._create_target_directories()

        # 4. Move test files
        self._move_test_files()

        # 5. Update imports in test files
        self._update_test_imports()

        # 6. Consolidate fixtures
        self._consolidate_fixtures()

        # 7. Clean up empty legacy directories
        self._cleanup_legacy_dirs()

        # 8. Validate migration
        self._validate_migration()

        print("✅ Test migration completed successfully!")
        print("📋 Run 'python -m pytest --collect-only' to verify test discovery")

    def _create_backup(self):
        """Create backup of current tests folder."""
        backup_path = self.root_path / "tests_backup_pre_hexagonal"
        if backup_path.exists():
            shutil.rmtree(backup_path)
        shutil.copytree(self.tests_path, backup_path)
        print(f"📁 Backup created: {backup_path}")

    def _analyze_current_structure(self):
        """Analyze and report current test structure."""
        print("\n📊 Current test structure analysis:")
        unit_path = self.tests_path / "unit"

        for item in sorted(unit_path.iterdir()):
            if item.is_dir():
                test_count = len(list(item.rglob("test_*.py")))
                target = self.legacy_to_hex_mapping.get(f"tests/unit/{item.name}", "UNMAPPED")
                status = "✅" if target != "UNMAPPED" else "⚠️"
                print(f"  {status} {item.name}/ ({test_count} tests) → {target}")

    def _create_target_directories(self):
        """Create hexagonal directory structure."""
        print("\n🏗️ Creating hexagonal directory structure...")

        # Core hexagonal layers
        layers = [
            "tests/unit/domain/entities",
            "tests/unit/domain/services",
            "tests/unit/domain/value_objects",
            "tests/unit/application/commands",
            "tests/unit/application/queries",
            "tests/unit/application/orchestrators",
            "tests/unit/application/models",
            "tests/unit/infrastructure/database",
            "tests/unit/infrastructure/memory",
            "tests/unit/infrastructure/cache",
            "tests/unit/infrastructure/backup",
            "tests/unit/infrastructure/registry",
            "tests/unit/infrastructure/security",
            "tests/unit/infrastructure/content",
            "tests/unit/interfaces/api",
            "tests/unit/interfaces/cli"
        ]

        for layer_path in layers:
            full_path = self.root_path / layer_path
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"  📁 Created: {layer_path}")

    def _move_test_files(self):
        """Move test files to hexagonal structure."""
        print("\n📦 Moving test files...")

        for legacy_path, hex_path in self.legacy_to_hex_mapping.items():
            legacy_full = self.root_path / legacy_path
            target_full = self.root_path / hex_path

            if legacy_full.exists() and legacy_full.is_dir():
                # Create target directory
                target_full.mkdir(parents=True, exist_ok=True)

                # Move all Python files
                moved_count = 0
                for test_file in legacy_full.rglob("*.py"):
                    if test_file.name == "__init__.py":
                        continue

                    # Calculate relative path structure
                    rel_path = test_file.relative_to(legacy_full)
                    target_file = target_full / rel_path

                    # Create parent directories if needed
                    target_file.parent.mkdir(parents=True, exist_ok=True)

                    # Move the file
                    if not target_file.exists():
                        shutil.move(str(test_file), str(target_file))
                        moved_count += 1
                        print(f"    📦 {test_file.name} → {hex_path}")

                if moved_count > 0:
                    print(f"  ✅ Moved {moved_count} files from {legacy_path}")

    def _update_test_imports(self):
        """Update all import statements in test files."""
        print("\n🔧 Updating test imports...")

        # Import mapping patterns
        import_mappings = {
            # Legacy core imports
            r"from core\.": "from src.openchronicle.",
            r"import core\.": "import src.openchronicle.",

            # Specific legacy patterns
            r"from core\.characters\.": "from src.openchronicle.domain.entities.",
            r"from core\.scenes\.": "from src.openchronicle.domain.entities.",
            r"from core\.narrative\.": "from src.openchronicle.domain.services.",
            r"from core\.timeline\.": "from src.openchronicle.domain.services.",
            r"from core\.database\.": "from src.openchronicle.infrastructure.database.",
            r"from core\.memory\.": "from src.openchronicle.infrastructure.memory.",
            r"from core\.management\.": "from src.openchronicle.application.orchestrators.",

            # Relative import fixes
            r"from \.\.": "from src.openchronicle.",
            r"from \.": "from src.openchronicle."
        }

        updated_files = 0
        test_files = list(self.tests_path.rglob("*.py"))

        for test_file in test_files:
            if test_file.name in ["__init__.py", "conftest.py"]:
                continue

            try:
                content = test_file.read_text(encoding='utf-8')
                original_content = content

                # Apply import mappings
                for old_pattern, new_pattern in import_mappings.items():
                    content = re.sub(old_pattern, new_pattern, content)

                # Write back if changed
                if content != original_content:
                    test_file.write_text(content, encoding='utf-8')
                    updated_files += 1
                    print(f"    🔧 Updated: {test_file.relative_to(self.tests_path)}")

            except Exception as e:
                print(f"    ⚠️ Error updating {test_file}: {e}")

        print(f"  ✅ Updated imports in {updated_files} files")

    def _consolidate_fixtures(self):
        """Consolidate fixtures into central location."""
        print("\n🔧 Consolidating fixtures...")

        fixtures_dir = self.tests_path / "fixtures"
        fixtures_dir.mkdir(exist_ok=True)

        # Look for fixture files in various locations
        fixture_patterns = ["*fixture*.py", "*conftest*.py", "*mock*.py"]
        moved_fixtures = 0

        for pattern in fixture_patterns:
            for fixture_file in self.tests_path.rglob(pattern):
                if fixture_file.parent == fixtures_dir:
                    continue  # Already in fixtures dir

                if "fixtures" in str(fixture_file):
                    continue  # Skip if already in a fixtures folder

                target = fixtures_dir / fixture_file.name
                if not target.exists() and fixture_file.name != "conftest.py":
                    try:
                        shutil.move(str(fixture_file), str(target))
                        moved_fixtures += 1
                        print(f"    🔧 {fixture_file.name} → fixtures/")
                    except Exception as e:
                        print(f"    ⚠️ Could not move {fixture_file.name}: {e}")

        print(f"  ✅ Consolidated {moved_fixtures} fixture files")

    def _cleanup_legacy_dirs(self):
        """Remove empty legacy directories."""
        print("\n🗑️ Cleaning up empty directories...")

        removed_dirs = 0
        # Check all legacy paths for emptiness
        for legacy_path in self.legacy_to_hex_mapping.keys():
            legacy_dir = self.root_path / legacy_path
            if legacy_dir.exists() and legacy_dir.is_dir():
                try:
                    # Check if directory is empty (only __pycache__ or __init__.py allowed)
                    contents = list(legacy_dir.iterdir())
                    non_cache_contents = [
                        item for item in contents
                        if item.name not in ["__pycache__", "__init__.py"]
                    ]

                    if not non_cache_contents:
                        shutil.rmtree(legacy_dir)
                        removed_dirs += 1
                        print(f"    🗑️ Removed: {legacy_path}")

                except Exception as e:
                    print(f"    ⚠️ Could not remove {legacy_path}: {e}")

        print(f"  ✅ Removed {removed_dirs} empty directories")

    def _validate_migration(self):
        """Validate the migration was successful."""
        print("\n✅ Validating migration...")

        # Check hexagonal structure exists
        required_dirs = [
            "tests/unit/domain",
            "tests/unit/application",
            "tests/unit/infrastructure",
            "tests/unit/interfaces"
        ]

        for req_dir in required_dirs:
            dir_path = self.root_path / req_dir
            if dir_path.exists():
                test_count = len(list(dir_path.rglob("test_*.py")))
                print(f"    ✅ {req_dir} ({test_count} tests)")
            else:
                print(f"    ❌ Missing: {req_dir}")

        # Count total tests
        total_tests = len(list(self.tests_path.rglob("test_*.py")))
        print(f"\n📊 Total test files: {total_tests}")


def main():
    """Main entry point for test migration."""
    print("🏗️ OpenChronicle Test Migration to Hexagonal Architecture")
    print("=" * 60)

    migrator = TestMigrator()

    # Confirm before proceeding
    response = input("\n⚠️ This will restructure your tests folder. Continue? (y/N): ")
    if response.lower() != 'y':
        print("❌ Migration cancelled.")
        return

    migrator.migrate_all_tests()

    print("\n" + "=" * 60)
    print("🎉 Migration complete! Next steps:")
    print("1. Run: python -m pytest --collect-only")
    print("2. Run: python scripts/validate_hexagonal_tests.py")
    print("3. Run your test suite to ensure everything works")


if __name__ == "__main__":
    main()
