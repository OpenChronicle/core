"""
Automated script to fix hexagonal architecture violations in source code.
This script identifies and helps fix the 16 boundary violations found.
"""
from pathlib import Path
import re
from typing import List, Dict, Tuple


class ArchitectureViolationFixer:
    """Fixes hexagonal architecture boundary violations."""
    
    def __init__(self):
        self.root_path = Path(__file__).parent.parent
        self.src_path = self.root_path / "src" / "openchronicle"
        
        # Violation patterns identified by validation
        self.violations = {
            "domain_to_infrastructure": [
                "src/openchronicle/domain/models/configuration_manager.py",
                "src/openchronicle/domain/services/timeline/shared/fallback_navigation.py",
                "src/openchronicle/domain/services/timeline/shared/fallback_state.py", 
                "src/openchronicle/domain/services/timeline/shared/fallback_timeline.py"
            ],
            "application_to_interfaces": [
                "src/openchronicle/application/services/importers/storypack/generators/output_formatter.py",
                "src/openchronicle/application/services/importers/storypack/generators/storypack_builder.py",
                "src/openchronicle/application/services/importers/storypack/generators/template_engine.py",
                "src/openchronicle/application/services/importers/storypack/parsers/content_parser.py",
                "src/openchronicle/application/services/importers/storypack/parsers/metadata_extractor.py",
                "src/openchronicle/application/services/importers/storypack/parsers/structure_analyzer.py",
                "src/openchronicle/application/services/importers/storypack/processors/ai_processor.py",
                "src/openchronicle/application/services/importers/storypack/processors/content_classifier.py",
                "src/openchronicle/application/services/importers/storypack/processors/validation_engine.py"
            ],
            "infrastructure_to_interfaces": [
                "src/openchronicle/infrastructure/performance/analysis/bottleneck_analyzer.py",
                "src/openchronicle/infrastructure/performance/metrics/collector.py",
                "src/openchronicle/infrastructure/performance/metrics/storage.py"
            ]
        }
    
    def analyze_violations(self) -> Dict[str, List[Dict]]:
        """Analyze each violation file to understand the specific imports."""
        analysis = {}
        
        for category, files in self.violations.items():
            analysis[category] = []
            
            for file_path in files:
                full_path = self.root_path / file_path
                if full_path.exists():
                    violation_info = self._analyze_file_violations(full_path, category)
                    analysis[category].append(violation_info)
                else:
                    print(f"⚠️ File not found: {file_path}")
        
        return analysis
    
    def _analyze_file_violations(self, file_path: Path, category: str) -> Dict:
        """Analyze a specific file for boundary violations."""
        try:
            content = file_path.read_text(encoding='utf-8')
            violations = []
            
            # Patterns to look for based on category
            if "domain_to_infrastructure" in category:
                patterns = [
                    r"from src\.openchronicle\.infrastructure",
                    r"import src\.openchronicle\.infrastructure"
                ]
            elif "application_to_interfaces" in category:
                patterns = [
                    r"from \.\.interfaces",
                    r"from src\.openchronicle\.interfaces"
                ]
            elif "infrastructure_to_interfaces" in category:
                patterns = [
                    r"from \.\.interfaces", 
                    r"from src\.openchronicle\.interfaces"
                ]
            else:
                patterns = []
            
            # Find violations
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                for pattern in patterns:
                    if re.search(pattern, line):
                        violations.append({
                            "line": i,
                            "content": line.strip(),
                            "pattern": pattern
                        })
            
            return {
                "file": str(file_path.relative_to(self.root_path)),
                "violations": violations,
                "category": category
            }
            
        except Exception as e:
            return {
                "file": str(file_path.relative_to(self.root_path)),
                "error": str(e),
                "category": category
            }
    
    def generate_fix_recommendations(self, analysis: Dict) -> Dict[str, List[str]]:
        """Generate specific fix recommendations for each violation category."""
        recommendations = {}
        
        for category, violations in analysis.items():
            recommendations[category] = []
            
            if category == "domain_to_infrastructure":
                recommendations[category] = [
                    "1. Create abstract interfaces in domain/ports/ for infrastructure dependencies",
                    "2. Move concrete implementations to infrastructure/adapters/",
                    "3. Use dependency injection to wire interfaces to implementations",
                    "4. Update domain code to depend only on abstract interfaces",
                    "Example: Create IConfigurationPort in domain/ports/, implement in infrastructure/"
                ]
            
            elif category == "application_to_interfaces":
                recommendations[category] = [
                    "1. Move shared interfaces to domain/ports/ if they're business logic",
                    "2. Use dependency injection for UI/API dependencies", 
                    "3. Consider if these should be application services instead",
                    "4. Replace relative imports with absolute imports to domain",
                    "Example: Move IOutputFormatter to domain/ports/output_port.py"
                ]
            
            elif category == "infrastructure_to_interfaces":
                recommendations[category] = [
                    "1. Use dependency injection for interface dependencies",
                    "2. Create abstract ports in domain for performance monitoring",
                    "3. Infrastructure should not know about UI interfaces",
                    "4. Consider event-driven architecture for cross-layer communication",
                    "Example: Create IPerformanceMonitor in domain/ports/"
                ]
        
        return recommendations
    
    def create_port_interfaces(self, analysis: Dict) -> List[str]:
        """Generate port interface files to fix violations."""
        created_files = []
        
        # Create ports directory if it doesn't exist
        ports_dir = self.src_path / "domain" / "ports"
        ports_dir.mkdir(exist_ok=True)
        
        # Configuration port for domain violations
        config_port = ports_dir / "configuration_port.py"
        if not config_port.exists():
            config_port.write_text('''"""
Configuration port for domain layer.
Abstract interface for configuration management without infrastructure dependencies.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class IConfigurationPort(ABC):
    """Port for configuration management in domain layer."""
    
    @abstractmethod
    async def get_config(self, key: str) -> Optional[Any]:
        """Get configuration value by key."""
        pass
    
    @abstractmethod
    async def set_config(self, key: str, value: Any) -> bool:
        """Set configuration value."""
        pass
    
    @abstractmethod
    async def get_all_configs(self) -> Dict[str, Any]:
        """Get all configuration values."""
        pass


class IPerformancePort(ABC):
    """Port for performance monitoring in domain layer."""
    
    @abstractmethod
    async def record_metric(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Record a performance metric."""
        pass
    
    @abstractmethod
    async def get_metrics(self, name: str, start_time: float = None) -> List[Dict]:
        """Get recorded metrics."""
        pass


class IStoragePort(ABC):
    """Port for storage operations in domain layer."""
    
    @abstractmethod
    async def store_data(self, key: str, data: Any) -> bool:
        """Store data with given key."""
        pass
    
    @abstractmethod
    async def retrieve_data(self, key: str) -> Optional[Any]:
        """Retrieve data by key."""
        pass
''', encoding='utf-8')
            created_files.append(str(config_port.relative_to(self.root_path)))
        
        return created_files
    
    def run_analysis(self) -> None:
        """Run complete violation analysis and generate report."""
        print("🔍 Analyzing Hexagonal Architecture Violations")
        print("=" * 50)
        
        # Analyze violations
        analysis = self.analyze_violations()
        
        # Generate recommendations  
        recommendations = self.generate_fix_recommendations(analysis)
        
        # Create port interfaces
        created_ports = self.create_port_interfaces(analysis)
        
        # Output detailed report
        total_violations = sum(len(v) for v in analysis.values())
        print(f"📊 Found violations in {total_violations} files")
        print()
        
        for category, violations in analysis.items():
            if violations:
                print(f"🚨 {category.upper().replace('_', ' ')}")
                print("-" * 30)
                
                for violation in violations:
                    if "error" in violation:
                        print(f"❌ {violation['file']}: {violation['error']}")
                    else:
                        print(f"📁 {violation['file']}")
                        for v in violation['violations']:
                            print(f"   Line {v['line']}: {v['content']}")
                
                print(f"\n💡 Recommended Fixes:")
                for rec in recommendations[category]:
                    print(f"   {rec}")
                print()
        
        if created_ports:
            print(f"✅ Created port interfaces:")
            for port in created_ports:
                print(f"   📄 {port}")
        
        print("\n🚀 Next Steps:")
        print("1. Review the violations above")
        print("2. Implement the recommended fixes")
        print("3. Run 'python scripts/validate_hexagonal_tests.py' to verify")
        print("4. Update dependency injection configuration")


def main():
    """Main entry point for violation analysis."""
    fixer = ArchitectureViolationFixer()
    fixer.run_analysis()


if __name__ == "__main__":
    main()
