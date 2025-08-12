#!/usr/bin/env python3
"""
Exception Refactoring Tool for OpenChronicle

This script systematically replaces broad `except Exception` handlers with
specific exception types based on the context and imports of each file.

Usage:
    python utilities/tools/exception_refactor.py <file_path>
    python utilities/tools/exception_refactor.py --scan-all  # List all files needing fixes
    python utilities/tools/exception_refactor.py --fix-all   # Fix all files automatically
"""

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class ExceptionRefactorer:
    """Refactors broad exception handlers to specific ones."""
    
    def __init__(self):
        self.exception_mappings = {
            # Infrastructure patterns
            'redis': ['redis.exceptions.RedisError', 'redis.exceptions.ConnectionError', 'CacheError', 'CacheConnectionError'],
            'cache': ['CacheError', 'CacheConnectionError'],
            'database': ['DatabaseError', 'DatabaseConnectionError'],
            'sqlalchemy': ['sqlalchemy.exc.SQLAlchemyError', 'sqlalchemy.exc.OperationalError'],
            'aiosqlite': ['sqlite3.Error', 'DatabaseError'],
            
            # Network patterns
            'httpx': ['httpx.HTTPError', 'httpx.ConnectError', 'httpx.TimeoutException'],
            'requests': ['requests.exceptions.RequestException', 'requests.exceptions.ConnectionError'],
            'aioredis': ['aioredis.exceptions.RedisError', 'CacheError'],
            
            # File system patterns
            'file': ['FileNotFoundError', 'PermissionError', 'OSError'],
            'path': ['FileNotFoundError', 'PermissionError', 'OSError'],
            'json': ['json.JSONDecodeError', 'ValidationError'],
            'yaml': ['yaml.YAMLError', 'ValidationError'],
            
            # Model patterns
            'llm': ['ModelError', 'ModelConnectionError'],
            'openai': ['openai.error.OpenAIError', 'ModelError'],
            'anthropic': ['anthropic.APIError', 'ModelError'],
            'transformers': ['transformers.utils.ModelNotFoundError', 'ModelError'],
            
            # Memory patterns
            'memory': ['MemoryError', 'CacheError'],
            'asyncio': ['asyncio.CancelledError', 'asyncio.TimeoutError'],
            
            # Validation patterns
            'pydantic': ['pydantic.ValidationError', 'ValidationError'],
            'validation': ['ValidationError', 'ValueError'],
        }
        
        self.core_exceptions = {
            'OpenChronicleError',
            'ValidationError', 
            'InfrastructureError',
            'CacheError',
            'CacheConnectionError', 
            'DatabaseError',
            'DatabaseConnectionError',
            'ModelError',
            'ModelConnectionError',
            'FileNotFoundError',
            'FilePermissionError',
        }
        
    def analyze_file(self, file_path: Path) -> Dict:
        """Analyze a file for exception handling patterns."""
        content = file_path.read_text(encoding='utf-8')
        
        # Find broad exception handlers
        broad_exceptions = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if re.search(r'except\s+Exception\s*(as\s+\w+)?:', line):
                broad_exceptions.append({
                    'line': i + 1,
                    'content': line.strip(),
                    'context': self._get_context(lines, i)
                })
        
        # Analyze imports to determine context
        imports = self._analyze_imports(content)
        context_hints = self._determine_context(content, file_path)
        
        return {
            'file': str(file_path),
            'broad_exceptions': broad_exceptions,
            'imports': imports,
            'context_hints': context_hints,
            'recommended_exceptions': self._recommend_exceptions(imports, context_hints)
        }
    
    def _get_context(self, lines: List[str], line_idx: int, context_size: int = 3) -> List[str]:
        """Get surrounding context for an exception handler."""
        start = max(0, line_idx - context_size)
        end = min(len(lines), line_idx + context_size + 1)
        return lines[start:end]
    
    def _analyze_imports(self, content: str) -> Set[str]:
        """Extract relevant imports from file content."""
        imports = set()
        
        # Simple regex-based import extraction
        import_patterns = [
            r'import\s+(\w+)',
            r'from\s+(\w+)',
            r'from\s+.*?import.*?(\w+)',
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            imports.update(matches)
        
        return imports
    
    def _determine_context(self, content: str, file_path: Path) -> Set[str]:
        """Determine the functional context of the file."""
        context_hints = set()
        
        # Path-based hints
        path_parts = file_path.parts
        for part in path_parts:
            if part in ['cache', 'memory', 'database', 'persistence', 'llm', 'models']:
                context_hints.add(part)
        
        # Content-based hints
        content_lower = content.lower()
        for keyword in ['redis', 'cache', 'database', 'sql', 'http', 'file', 'json', 'yaml']:
            if keyword in content_lower:
                context_hints.add(keyword)
        
        return context_hints
    
    def _recommend_exceptions(self, imports: Set[str], context_hints: Set[str]) -> List[str]:
        """Recommend specific exceptions based on context."""
        recommended = set()
        
        # Add exceptions based on imports
        for imp in imports:
            if imp in self.exception_mappings:
                recommended.update(self.exception_mappings[imp])
        
        # Add exceptions based on context
        for hint in context_hints:
            if hint in self.exception_mappings:
                recommended.update(self.exception_mappings[hint])
        
        # Always include core exceptions for infrastructure files
        if any(hint in ['cache', 'database', 'memory', 'persistence'] for hint in context_hints):
            recommended.update(['InfrastructureError', 'ConnectionError', 'OSError'])
        
        return sorted(list(recommended))
    
    def generate_refactor_suggestions(self, analysis: Dict) -> List[Dict]:
        """Generate specific refactoring suggestions."""
        suggestions = []
        
        for exc in analysis['broad_exceptions']:
            context = ' '.join(exc['context']).lower()
            
            # Determine specific exceptions based on context
            specific_exceptions = []
            
            if 'redis' in context or 'cache' in context:
                specific_exceptions = ['CacheError', 'CacheConnectionError', 'ConnectionError']
            elif 'database' in context or 'sql' in context:
                specific_exceptions = ['DatabaseError', 'DatabaseConnectionError', 'OSError']
            elif 'file' in context or 'path' in context:
                specific_exceptions = ['FileNotFoundError', 'PermissionError', 'OSError']
            elif 'json' in context:
                specific_exceptions = ['json.JSONDecodeError', 'ValidationError']
            elif 'http' in context or 'request' in context:
                specific_exceptions = ['httpx.HTTPError', 'ConnectionError', 'OSError']
            else:
                # Default pattern for infrastructure code
                specific_exceptions = ['InfrastructureError', 'ConnectionError', 'OSError']
            
            suggestions.append({
                'line': exc['line'],
                'original': exc['content'],
                'suggested_exceptions': specific_exceptions,
                'context': exc['context']
            })
        
        return suggestions
    
    def scan_all_files(self, src_dir: Path = None) -> List[Dict]:
        """Scan all Python files for broad exception handlers."""
        if src_dir is None:
            src_dir = Path("src/openchronicle")
        
        results = []
        
        for py_file in src_dir.rglob("*.py"):
            if py_file.name.startswith('.'):
                continue
                
            try:
                analysis = self.analyze_file(py_file)
                if analysis['broad_exceptions']:
                    results.append(analysis)
            except Exception as e:
                print(f"Error analyzing {py_file}: {e}")
        
        return results
    
    def print_analysis_report(self, results: List[Dict]):
        """Print a comprehensive analysis report."""
        total_files = len(results)
        total_exceptions = sum(len(r['broad_exceptions']) for r in results)
        
        print(f"\n🔍 Exception Analysis Report")
        print(f"=" * 50)
        print(f"Files with broad exceptions: {total_files}")
        print(f"Total broad exception handlers: {total_exceptions}")
        print()
        
        # Sort by number of exceptions (worst first)
        results.sort(key=lambda x: len(x['broad_exceptions']), reverse=True)
        
        for i, result in enumerate(results[:10]):  # Top 10 worst files
            print(f"{i+1}. {result['file']}")
            print(f"   Broad exceptions: {len(result['broad_exceptions'])}")
            print(f"   Context: {', '.join(result['context_hints'])}")
            print(f"   Recommended: {', '.join(result['recommended_exceptions'][:3])}...")
            print()


def main():
    """Main CLI interface."""
    refactorer = ExceptionRefactorer()
    
    if len(sys.argv) == 1 or sys.argv[1] == '--help':
        print(__doc__)
        return
    
    if sys.argv[1] == '--scan-all':
        print("🔍 Scanning all files for broad exception handlers...")
        results = refactorer.scan_all_files()
        refactorer.print_analysis_report(results)
        
    elif sys.argv[1] == '--fix-all':
        print("🛠️ Automated fixing not yet implemented")
        print("Use --scan-all to see analysis, then fix manually using the suggestions")
        
    else:
        # Analyze specific file
        file_path = Path(sys.argv[1])
        if not file_path.exists():
            print(f"Error: File {file_path} not found")
            return
        
        analysis = refactorer.analyze_file(file_path)
        suggestions = refactorer.generate_refactor_suggestions(analysis)
        
        print(f"\n🔍 Analysis for {file_path}")
        print(f"=" * 50)
        print(f"Broad exceptions found: {len(analysis['broad_exceptions'])}")
        print(f"Imports: {', '.join(sorted(analysis['imports']))}")
        print(f"Context: {', '.join(analysis['context_hints'])}")
        print(f"Recommended exceptions: {', '.join(analysis['recommended_exceptions'])}")
        print()
        
        for suggestion in suggestions:
            print(f"Line {suggestion['line']}: {suggestion['original']}")
            print(f"  Suggested: except ({', '.join(suggestion['suggested_exceptions'])}) as e:")
            print()


if __name__ == "__main__":
    main()
