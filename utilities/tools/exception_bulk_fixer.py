#!/usr/bin/env python3
"""
Bulk Exception Handler Fixer

Automated tool to apply consistent two-tier exception handling patterns
across the OpenChronicle codebase based on context analysis.

Usage:
    python exception_bulk_fixer.py [path] [--dry-run] [--max-files N]
"""

import argparse
import pathlib
import re
import sys
from typing import List, Tuple, Dict, Set
import ast


class ExceptionPatternFixer:
    """Applies context-aware exception handling improvements."""
    
    # Exception type mappings by file context
    CONTEXT_EXCEPTIONS = {
        'file_operations': ['OSError', 'IOError', 'PermissionError', 'FileNotFoundError'],
        'json_operations': ['json.JSONDecodeError'],
        'encoding_operations': ['UnicodeDecodeError', 'UnicodeEncodeError'],
        'http_operations': ['requests.RequestException', 'urllib.error.URLError'],
        'database_operations': ['sqlite3.Error', 'psycopg2.Error'],
        'service_layer': ['ServiceError', 'ValidationError', 'InfrastructureError'],
        'model_operations': ['ModelError', 'AdapterError', 'ConfigurationError']
    }
    
    # Common import patterns to add
    IMPORT_ADDITIONS = {
        'json': 'import json',
        'requests': 'import requests',
        'urllib': 'import urllib.error',
        'sqlite3': 'import sqlite3',
        'service_errors': 'from openchronicle.domain.exceptions import ServiceError, ValidationError, InfrastructureError',
        'model_errors': 'from openchronicle.core.model_management.exceptions import ModelError, AdapterError, ConfigurationError'
    }
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.patterns = [
            re.compile(r"except\s*:\s*$"),           # bare except
            re.compile(r"except\s+Exception\b"),     # broad except Exception
        ]
        
    def analyze_file_context(self, content: str) -> Set[str]:
        """Analyze file content to determine appropriate exception contexts."""
        contexts = set()
        
        # File operations
        if any(keyword in content for keyword in ['open(', 'read(', 'write(', 'Path(', 'os.path']):
            contexts.add('file_operations')
            
        # JSON operations
        if 'json.' in content or 'JSON' in content:
            contexts.add('json_operations')
            
        # Encoding operations
        if any(keyword in content for keyword in ['encode(', 'decode(', 'encoding=', 'utf-8']):
            contexts.add('encoding_operations')
            
        # HTTP operations
        if any(keyword in content for keyword in ['requests.', 'urllib.', 'http']):
            contexts.add('http_operations')
            
        # Database operations
        if any(keyword in content for keyword in ['sqlite3.', 'cursor.', 'execute(', 'fetchall(']):
            contexts.add('database_operations')
            
        # Service layer (domain/application/infrastructure patterns)
        if any(pattern in content for pattern in ['domain/', 'application/', 'infrastructure/']):
            contexts.add('service_layer')
            
        # Model operations
        if any(keyword in content for keyword in ['model_', 'adapter_', 'orchestrator']):
            contexts.add('model_operations')
            
        return contexts
    
    def get_specific_exceptions(self, contexts: Set[str]) -> List[str]:
        """Get appropriate specific exceptions for the given contexts."""
        exceptions = []
        for context in contexts:
            if context in self.CONTEXT_EXCEPTIONS:
                exceptions.extend(self.CONTEXT_EXCEPTIONS[context])
        return list(set(exceptions))  # Remove duplicates
    
    def get_required_imports(self, contexts: Set[str], existing_imports: Set[str]) -> List[str]:
        """Determine what imports need to be added."""
        needed_imports = []
        
        if 'json_operations' in contexts and 'json' not in existing_imports:
            needed_imports.append(self.IMPORT_ADDITIONS['json'])
            
        if 'service_layer' in contexts and 'ServiceError' not in existing_imports:
            needed_imports.append(self.IMPORT_ADDITIONS['service_errors'])
            
        if 'model_operations' in contexts and 'ModelError' not in existing_imports:
            needed_imports.append(self.IMPORT_ADDITIONS['model_errors'])
            
        return needed_imports
    
    def extract_existing_imports(self, content: str) -> Set[str]:
        """Extract existing imports from file content."""
        imports = set()
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.names:
                        for alias in node.names:
                            imports.add(alias.name)
        except SyntaxError:
            # Fallback to regex if AST parsing fails
            import_lines = re.findall(r'^(?:from\s+\S+\s+)?import\s+(.+)$', content, re.MULTILINE)
            for line in import_lines:
                for item in line.split(','):
                    imports.add(item.strip().split(' as ')[0])
        return imports
    
    def generate_two_tier_handler(self, specific_exceptions: List[str], context_line: str, surrounding_context: List[str]) -> str:
        """Generate a two-tier exception handler based on context."""
        indent = len(context_line) - len(context_line.lstrip())
        base_indent = ' ' * indent
        inner_indent = ' ' * (indent + 4)
        
        # Analyze surrounding context for better exception handling
        context_str = '\n'.join(surrounding_context).lower()
        
        # Determine if this is likely a logging/monitoring boundary
        is_boundary = any(keyword in context_str for keyword in [
            'log_', 'logger', 'telemetry', 'monitor', 'metric', 'event'
        ])
        
        # Determine operation type
        is_file_op = any(keyword in context_str for keyword in [
            'open(', 'read', 'write', 'path', 'file'
        ])
        is_json_op = 'json' in context_str
        is_service_op = any(keyword in context_str for keyword in [
            'service', 'adapter', 'orchestrator', 'manager'
        ])
        
        # Build appropriate handler
        if is_boundary:
            # Boundary pattern - catch-all with logging
            return f"""{base_indent}except Exception as e:
{inner_indent}# Boundary exception handler - log and continue safely
{inner_indent}logger.error(f"Operation failed: {{e}}")
{inner_indent}return None  # or appropriate default"""
        
        elif is_file_op and not specific_exceptions:
            # File operations pattern
            return f"""{base_indent}except (OSError, IOError, PermissionError) as e:
{inner_indent}# File operation failed
{inner_indent}raise InfrastructureError(f"File operation failed: {{e}}") from e
{base_indent}except Exception as e:
{inner_indent}# Unexpected error in file operation
{inner_indent}raise"""
        
        elif is_json_op:
            # JSON operations pattern
            return f"""{base_indent}except json.JSONDecodeError as e:
{inner_indent}# Invalid JSON format
{inner_indent}raise ValidationError(f"Invalid JSON: {{e}}") from e
{base_indent}except Exception as e:
{inner_indent}# Unexpected error in JSON processing
{inner_indent}raise"""
        
        elif is_service_op:
            # Service operations pattern
            return f"""{base_indent}except (ServiceError, ValidationError, InfrastructureError):
{inner_indent}# Re-raise domain exceptions
{inner_indent}raise
{base_indent}except Exception as e:
{inner_indent}# Wrap unexpected errors
{inner_indent}raise ServiceError(f"Service operation failed: {{e}}") from e"""
        
        else:
            # Generic two-tier pattern
            return f"""{base_indent}except Exception as e:
{inner_indent}# Re-raise with context preservation
{inner_indent}raise"""
    
    def fix_exception_patterns(self, file_path: pathlib.Path) -> Tuple[bool, List[str]]:
        """Fix exception patterns in a single file."""
        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content
            changes = []
            
            # Analyze context
            contexts = self.analyze_file_context(content)
            existing_imports = self.extract_existing_imports(content)
            specific_exceptions = self.get_specific_exceptions(contexts)
            required_imports = self.get_required_imports(contexts, existing_imports)
            
            # Add missing imports
            if required_imports:
                lines = content.split('\n')
                import_insert_idx = 0
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        import_insert_idx = i + 1
                
                for import_stmt in required_imports:
                    lines.insert(import_insert_idx, import_stmt)
                    import_insert_idx += 1
                    changes.append(f"Added import: {import_stmt}")
                
                content = '\n'.join(lines)
            
            # Fix exception patterns
            lines = content.split('\n')
            modified_lines = []
            i = 0
            
            while i < len(lines):
                line = lines[i]
                matched_pattern = None
                
                for pattern in self.patterns:
                    if pattern.search(line):
                        matched_pattern = pattern
                        break
                
                if matched_pattern:
                    # Get surrounding context (5 lines before and after)
                    start_ctx = max(0, i - 5)
                    end_ctx = min(len(lines), i + 6)
                    surrounding_context = lines[start_ctx:end_ctx]
                    
                    # Replace with context-aware handler
                    new_handler = self.generate_two_tier_handler(specific_exceptions, line, surrounding_context)
                    modified_lines.append(new_handler)
                    changes.append(f"Line {i+1}: Replaced broad exception handler")
                else:
                    modified_lines.append(line)
                
                i += 1
            
            final_content = '\n'.join(modified_lines)
            
            # Write changes if not dry run
            if not self.dry_run and final_content != original_content:
                file_path.write_text(final_content, encoding='utf-8')
                changes.append(f"File updated: {file_path}")
            
        except Exception as e:
            return False, [f"Error processing {file_path}: {e}"]
        else:
            return final_content != original_content, changes


def scan_file_for_patterns(path: pathlib.Path) -> List[Tuple[int, str]]:
    """Scan file for exception patterns."""
    patterns = [
        re.compile(r"except\s*:\s*$"),           # bare except
        re.compile(r"except\s+Exception\b"),     # broad except Exception
    ]
    
    hits = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return hits
    
    for lineno, line in enumerate(text, start=1):
        for pat in patterns:
            if pat.search(line):
                hits.append((lineno, line.rstrip()))
                break
    return hits


def iter_py_files(root: pathlib.Path) -> List[pathlib.Path]:
    """Iterate Python files, excluding tests and coverage."""
    files = []
    for p in root.rglob("*.py"):
        if any(part in {"tests", "htmlcov", "__pycache__"} for part in p.parts):
            continue
        files.append(p)
    return files


def main() -> int:
    """Main execution function."""
    ap = argparse.ArgumentParser(description="Bulk fix exception handling patterns")
    ap.add_argument("path", nargs="?", default="src/openchronicle", 
                   help="Root directory to scan")
    ap.add_argument("--dry-run", action="store_true", 
                   help="Show what would be changed without making changes")
    ap.add_argument("--max-files", type=int, default=10,
                   help="Maximum number of files to process")
    ap.add_argument("--priority", choices=['high', 'medium', 'low'], default='high',
                   help="Priority level for file selection")
    
    args = ap.parse_args()
    
    root = pathlib.Path(args.path).resolve()
    if not root.exists():
        print(f"Path not found: {root}")
        return 2
    
    # Find files with patterns
    files_with_patterns = []
    for file_path in iter_py_files(root):
        patterns = scan_file_for_patterns(file_path)
        if patterns:
            files_with_patterns.append((file_path, len(patterns)))
    
    # Sort by pattern count (highest first)
    files_with_patterns.sort(key=lambda x: x[1], reverse=True)
    
    # Apply priority filter
    if args.priority == 'high':
        target_files = [f for f, count in files_with_patterns if count >= 5]
    elif args.priority == 'medium':
        target_files = [f for f, count in files_with_patterns if 2 <= count < 5]
    else:
        target_files = [f for f, count in files_with_patterns if count == 1]
    
    # Limit by max_files
    target_files = target_files[:args.max_files]
    
    if not target_files:
        print(f"No files found matching priority '{args.priority}' criteria")
        return 0
    
    print(f"Processing {len(target_files)} files with {args.priority} priority...")
    
    fixer = ExceptionPatternFixer(dry_run=args.dry_run)
    total_changes = 0
    
    for file_path in target_files:
        print(f"\nProcessing: {file_path}")
        
        changed, changes = fixer.fix_exception_patterns(file_path)
        
        if changed:
            total_changes += 1
            print(f"  ✓ Modified")
            for change in changes:
                print(f"    - {change}")
        else:
            print(f"  - No changes needed")
    
    print(f"\nSummary: {total_changes} files modified")
    
    if args.dry_run:
        print("DRY RUN - No actual changes were made")
        print("Run without --dry-run to apply changes")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
