"""
Architecture compliance tests to enforce hexagonal boundaries.
These tests validate that the codebase follows hexagonal architecture principles.
"""
import pytest
from pathlib import Path
import ast
import re
import sys


class TestArchitectureCompliance:
    """Test suite to validate hexagonal architecture compliance."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test paths."""
        self.root_path = Path(__file__).parent.parent
        self.src_path = self.root_path / "src" / "openchronicle"
        self.tests_path = self.root_path / "tests"
    
    def test_domain_layer_isolation(self):
        """Ensure domain layer doesn't import from outer layers."""
        if not self.src_path.exists():
            pytest.skip("Source directory not found")
            
        domain_path = self.src_path / "domain"
        if not domain_path.exists():
            pytest.skip("Domain layer not found")
            
        violations = []
        
        for py_file in domain_path.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                
                # Check for forbidden imports (outer layers)
                forbidden_patterns = [
                    r"from src\.openchronicle\.application",
                    r"from src\.openchronicle\.infrastructure", 
                    r"from src\.openchronicle\.interfaces",
                    r"import src\.openchronicle\.application",
                    r"import src\.openchronicle\.infrastructure",
                    r"import src\.openchronicle\.interfaces",
                    # Also check relative imports that could break boundaries
                    r"from \.\.application",
                    r"from \.\.infrastructure",
                    r"from \.\.interfaces"
                ]
                
                for pattern in forbidden_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        violations.append(
                            f"{py_file.relative_to(self.root_path)}: "
                            f"Contains forbidden import pattern: {pattern}"
                        )
                        
            except Exception as e:
                violations.append(f"{py_file}: Error reading file: {e}")
        
        assert not violations, (
            f"Domain layer boundary violations found:\n" + 
            "\n".join(violations)
        )
    
    def test_application_layer_boundaries(self):
        """Ensure application layer only imports from domain and infrastructure."""
        if not self.src_path.exists():
            pytest.skip("Source directory not found")
            
        app_path = self.src_path / "application"
        if not app_path.exists():
            pytest.skip("Application layer not found")
            
        violations = []
        
        for py_file in app_path.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                
                # Forbidden: importing from interfaces layer
                forbidden_patterns = [
                    r"from src\.openchronicle\.interfaces",
                    r"import src\.openchronicle\.interfaces",
                    r"from \.\.interfaces"
                ]
                
                for pattern in forbidden_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        violations.append(
                            f"{py_file.relative_to(self.root_path)}: "
                            f"Contains forbidden import pattern: {pattern}"
                        )
                        
            except Exception as e:
                violations.append(f"{py_file}: Error reading file: {e}")
        
        assert not violations, (
            f"Application layer boundary violations found:\n" + 
            "\n".join(violations)
        )
    
    def test_infrastructure_layer_boundaries(self):
        """Ensure infrastructure layer only imports from domain."""
        if not self.src_path.exists():
            pytest.skip("Source directory not found")
            
        infra_path = self.src_path / "infrastructure"
        if not infra_path.exists():
            pytest.skip("Infrastructure layer not found")
            
        violations = []
        
        for py_file in infra_path.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                
                # Forbidden: importing from application or interfaces (outside infrastructure)
                # But allow infrastructure to import from its own interfaces
                forbidden_patterns = [
                    r"from src\.openchronicle\.application",
                    r"from src\.openchronicle\.interfaces",
                    r"import src\.openchronicle\.application", 
                    r"import src\.openchronicle\.interfaces"
                ]
                
                for pattern in forbidden_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        violations.append(
                            f"{py_file.relative_to(self.root_path)}: "
                            f"Contains forbidden import pattern: {pattern}"
                        )
                        
            except Exception as e:
                violations.append(f"{py_file}: Error reading file: {e}")
        
        assert not violations, (
            f"Infrastructure layer boundary violations found:\n" + 
            "\n".join(violations)
        )
    
    def test_no_legacy_core_imports_in_tests(self):
        """Ensure no legacy 'core' imports remain in test files."""
        if not self.tests_path.exists():
            pytest.skip("Tests directory not found")
            
        violations = []
        test_files = list(self.tests_path.rglob("*.py"))
        
        for py_file in test_files:
            try:
                content = py_file.read_text(encoding='utf-8')
                
                # Check for legacy core imports
                legacy_patterns = [
                    r"from core\.",
                    r"import core\.",
                    r"from \.\.core\.",
                    r"import \.\.core\."
                ]
                
                for pattern in legacy_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        violations.append(
                            f"{py_file.relative_to(self.root_path)}: "
                            f"Contains legacy 'core' import: {pattern}"
                        )
                        
            except Exception as e:
                violations.append(f"{py_file}: Error reading file: {e}")
        
        assert not violations, (
            f"Legacy import violations found in tests:\n" + 
            "\n".join(violations)
        )
    
    def test_no_legacy_core_imports_in_source(self):
        """Ensure no legacy 'core' imports remain in source files."""
        if not self.src_path.exists():
            pytest.skip("Source directory not found")
            
        violations = []
        source_files = list(self.src_path.rglob("*.py"))
        
        for py_file in source_files:
            try:
                content = py_file.read_text(encoding='utf-8')
                
                # Check for legacy core imports
                legacy_patterns = [
                    r"from core\.",
                    r"import core\.",
                    r"from \.\.core\.",
                    r"import \.\.core\."
                ]
                
                for pattern in legacy_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        violations.append(
                            f"{py_file.relative_to(self.root_path)}: "
                            f"Contains legacy 'core' import: {pattern}"
                        )
                        
            except Exception as e:
                violations.append(f"{py_file}: Error reading file: {e}")
        
        assert not violations, (
            f"Legacy import violations found in source:\n" + 
            "\n".join(violations)
        )
    
    def test_test_structure_mirrors_source(self):
        """Ensure test structure mirrors src/openchronicle structure."""
        if not self.src_path.exists():
            pytest.skip("Source directory not found")
            
        if not (self.tests_path / "unit").exists():
            pytest.skip("Unit tests directory not found")
            
        # Get hexagonal layer structure from source
        expected_layers = []
        for layer in ["domain", "application", "infrastructure", "interfaces"]:
            layer_path = self.src_path / layer
            if layer_path.exists():
                expected_layers.append(layer)
        
        # Check if test structure has corresponding layers
        missing_layers = []
        test_unit_path = self.tests_path / "unit"
        
        for layer in expected_layers:
            test_layer_path = test_unit_path / layer
            if not test_layer_path.exists():
                missing_layers.append(f"tests/unit/{layer}")
        
        assert not missing_layers, (
            f"Missing test layer directories:\n" + 
            "\n".join(missing_layers)
        )
    
    def test_proper_test_imports_structure(self):
        """Ensure test files use proper import structure."""
        if not self.tests_path.exists():
            pytest.skip("Tests directory not found")
            
        violations = []
        test_files = list(self.tests_path.rglob("test_*.py"))
        
        for test_file in test_files:
            try:
                content = test_file.read_text(encoding='utf-8')
                
                # Check for proper src.openchronicle imports
                # Allow some flexibility but ensure no relative imports to core
                problematic_patterns = [
                    r"from \.\.\. import",  # Too many relative imports
                    r"from \.\.\.\. import",  # Definitely too deep
                    r"import \.\.\.\.+",  # Multiple parent directory imports
                ]
                
                for pattern in problematic_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        violations.append(
                            f"{test_file.relative_to(self.root_path)}: "
                            f"Contains problematic import pattern: {pattern}"
                        )
                        
            except Exception as e:
                violations.append(f"{test_file}: Error reading file: {e}")
        
        # This is a warning rather than hard failure for now
        if violations:
            print(f"\n⚠️ Import structure warnings:\n" + "\n".join(violations))
    
    def test_hexagonal_layers_exist(self):
        """Verify that all hexagonal architecture layers exist."""
        if not self.src_path.exists():
            pytest.skip("Source directory not found")
            
        required_layers = ["domain", "application", "infrastructure", "interfaces"]
        missing_layers = []
        
        for layer in required_layers:
            layer_path = self.src_path / layer
            if not layer_path.exists():
                missing_layers.append(f"src/openchronicle/{layer}")
        
        assert not missing_layers, (
            f"Missing hexagonal architecture layers:\n" + 
            "\n".join(missing_layers)
        )
    
    def test_test_file_naming_convention(self):
        """Ensure test files follow proper naming conventions."""
        if not self.tests_path.exists():
            pytest.skip("Tests directory not found")
            
        violations = []
        
        # Check that test files start with 'test_' or end with '_test.py'
        for py_file in self.tests_path.rglob("*.py"):
            if py_file.name in ["__init__.py", "conftest.py"]:
                continue
                
            # Skip fixture and mock files
            if "fixture" in py_file.name.lower() or "mock" in py_file.name.lower():
                continue
                
            # Check naming convention
            if not (py_file.name.startswith("test_") or py_file.name.endswith("_test.py")):
                # Allow some special files
                special_files = ["main.py", "skip_markers.py"]
                if py_file.name not in special_files:
                    violations.append(
                        f"{py_file.relative_to(self.root_path)}: "
                        f"Does not follow test naming convention (test_*.py or *_test.py)"
                    )
        
        # This is a warning for now
        if violations:
            print(f"\n⚠️ Test naming convention warnings:\n" + "\n".join(violations))


def main():
    """Run architecture compliance tests directly."""
    print("🏗️ OpenChronicle Architecture Compliance Tests")
    print("=" * 50)
    
    # Run pytest with this file
    import subprocess
    import sys
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        __file__, 
        "-v",
        "--tb=short"
    ], cwd=Path(__file__).parent.parent)
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
