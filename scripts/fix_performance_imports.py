"""
Fix performance module import violations.
Replace relative interface imports with domain ports.
"""
from pathlib import Path
import re


def fix_performance_imports():
    """Fix performance module files to use domain ports instead of relative interface imports."""
    
    root_path = Path(__file__).parent.parent
    
    # Create performance interface port in domain for performance operations
    performance_interface_port_path = root_path / "src" / "openchronicle" / "domain" / "ports" / "performance_interface_port.py"
    
    performance_interface_port_content = '''"""
Performance interface port for domain layer operations.
Abstract interfaces for performance operations without dependency violations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union


class IPerformanceInterfacePort(ABC):
    """Port for performance interface operations."""
    
    @abstractmethod
    async def collect_metrics(self, metric_type: str, data: Dict) -> bool:
        """Collect performance metrics."""
        pass
    
    @abstractmethod
    async def store_metrics(self, metrics: Dict) -> bool:
        """Store performance metrics."""
        pass
    
    @abstractmethod
    async def analyze_bottlenecks(self, data: Dict) -> Dict[str, Any]:
        """Analyze performance bottlenecks."""
        pass
    
    @abstractmethod
    async def get_performance_report(self, criteria: Dict) -> Dict[str, Any]:
        """Generate performance report."""
        pass
    
    @abstractmethod
    async def track_resource_usage(self, resource_type: str) -> Dict[str, Any]:
        """Track resource usage."""
        pass
    
    @abstractmethod
    async def optimize_performance(self, optimization_type: str) -> bool:
        """Apply performance optimizations."""
        pass
'''
    
    if not performance_interface_port_path.exists():
        performance_interface_port_path.write_text(performance_interface_port_content, encoding='utf-8')
        print(f"✅ Created performance interface port: {performance_interface_port_path.relative_to(root_path)}")
    
    # Define the performance files to fix
    performance_files = [
        "src/openchronicle/infrastructure/performance/analysis/bottleneck_analyzer.py",
        "src/openchronicle/infrastructure/performance/metrics/collector.py",
        "src/openchronicle/infrastructure/performance/metrics/storage.py"
    ]
    
    # Fix each performance file
    for file_path in performance_files:
        full_path = root_path / file_path
        if full_path.exists():
            fix_performance_file(full_path, root_path)
    
    print("\\n🎯 Next Steps:")
    print("1. Create infrastructure adapter implementing IPerformanceInterfacePort")
    print("2. Update dependency injection to wire performance operations")
    print("3. Run validation to check remaining violations")


def fix_performance_file(file_path: Path, root_path: Path):
    """Fix a specific performance file."""
    
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
        port_import = "from src.openchronicle.domain.ports.performance_interface_port import IPerformanceInterfacePort\\n"
        
        # Find the best place to add the import (after existing imports)
        lines = content.split('\\n')
        import_insert_index = 0
        
        for i, line in enumerate(lines):
            if line.strip().startswith('from ') or line.strip().startswith('import '):
                import_insert_index = i + 1
            elif line.strip() and not line.strip().startswith('#'):
                break
        
        # Add the port import if not already present
        if "IPerformanceInterfacePort" not in content:
            lines.insert(import_insert_index, port_import.strip())
            content = '\\n'.join(lines)
        
        # Update class constructors to accept performance_interface_port
        if "__init__" in content:
            # Find the __init__ method and update it
            init_pattern = r'def __init__\\(self([^)]*)\\):'
            init_match = re.search(init_pattern, content)
            
            if init_match:
                current_params = init_match.group(1)
                if "performance_interface_port" not in current_params:
                    new_params = current_params + ", performance_interface_port: IPerformanceInterfacePort"
                    new_init = f"def __init__(self{new_params}):"
                    content = re.sub(init_pattern, new_init, content)
                    
                    # Add the assignment in the constructor
                    constructor_body_start = content.find(new_init) + len(new_init)
                    indent = "        "  # Adjust based on actual indentation
                    injection_line = f"\\n{indent}self.performance_interface_port = performance_interface_port\\n"
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
    fix_performance_imports()
