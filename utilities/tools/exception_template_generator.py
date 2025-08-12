#!/usr/bin/env python3
"""
Semi-Automated Exception Handler Generator

Generates exception handling code templates for manual review and application.
Safer than full automation but faster than manual work.

Usage:
    python exception_template_generator.py [path] > exception_fixes.md
"""

import argparse
import pathlib
import re
from typing import List, Tuple, Dict


def analyze_context(file_path: pathlib.Path, line_num: int, lines: List[str]) -> str:
    """Analyze context around exception handler to suggest appropriate fix."""
    
    # Get surrounding context
    start = max(0, line_num - 10)
    end = min(len(lines), line_num + 5)
    context = '\n'.join(lines[start:end])
    
    # Context analysis
    context_lower = context.lower()
    
    # File operations
    if any(keyword in context_lower for keyword in ['open(', 'read(', 'write(', 'path(', 'file']):
        return """
```python
except (OSError, IOError, PermissionError) as e:
    # File operation failed
    raise InfrastructureError(f"File operation failed: {e}") from e
except Exception as e:
    # Unexpected error in file operation
    raise
```
**Context**: File operations detected"""
    
    # JSON operations
    if 'json' in context_lower:
        return """
```python
except json.JSONDecodeError as e:
    # Invalid JSON format
    raise ValidationError(f"Invalid JSON: {e}") from e
except Exception as e:
    # Unexpected error in JSON processing
    raise
```
**Context**: JSON operations detected"""
    
    # Database operations
    if any(keyword in context_lower for keyword in ['cursor', 'execute', 'sqlite', 'database']):
        return """
```python
except sqlite3.Error as e:
    # Database operation failed
    raise InfrastructureError(f"Database operation failed: {e}") from e
except Exception as e:
    # Unexpected database error
    raise
```
**Context**: Database operations detected"""
    
    # Service/Business logic
    if any(keyword in context_lower for keyword in ['service', 'orchestrator', 'manager', 'engine']):
        return """
```python
except (ServiceError, ValidationError, InfrastructureError):
    # Re-raise domain exceptions
    raise
except Exception as e:
    # Wrap unexpected errors in service context
    raise ServiceError(f"Service operation failed: {e}") from e
```
**Context**: Service layer operations detected"""
    
    # Logging/Monitoring boundaries
    if any(keyword in context_lower for keyword in ['log', 'telemetry', 'event', 'monitor']):
        return """
```python
except Exception as e:
    # Boundary handler - log and continue safely
    logger.error(f"Operation failed: {e}")
    return None  # or appropriate default
```
**Context**: Logging/monitoring boundary detected"""
    
    # Default generic pattern
    return """
```python
except Exception as e:
    # Generic handler - analyze context for specific exceptions
    # Consider: What specific errors could occur here?
    # Then add appropriate specific handlers above this catch-all
    raise
```
**Context**: Generic - needs manual analysis"""


def generate_exception_report(root_path: pathlib.Path) -> str:
    """Generate a comprehensive exception fixing report."""
    
    patterns = [
        re.compile(r"except\s*:\s*$"),           # bare except
        re.compile(r"except\s+Exception\b"),     # broad except Exception
    ]
    
    report = """# Exception Handler Fix Report

This report contains suggested fixes for exception handling patterns.
Review each suggestion and apply manually after verification.

"""
    
    file_count = 0
    total_patterns = 0
    
    for py_file in root_path.rglob("*.py"):
        if any(part in {"tests", "htmlcov", "__pycache__"} for part in py_file.parts):
            continue
            
        try:
            lines = py_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            
            file_violations = []
            for line_num, line in enumerate(lines, 1):
                for pattern in patterns:
                    if pattern.search(line):
                        file_violations.append((line_num, line.strip()))
                        break
            
            if file_violations:
                file_count += 1
                total_patterns += len(file_violations)
                
                report += f"\n## File: `{py_file}`\n"
                report += f"**Patterns found**: {len(file_violations)}\n\n"
                
                for line_num, original_line in file_violations:
                    report += f"### Line {line_num}: `{original_line}`\n"
                    
                    suggested_fix = analyze_context(py_file, line_num - 1, lines)
                    report += suggested_fix
                    report += "\n\n---\n"
        
        except Exception as e:
            continue
    
    report += f"""
## Summary

- **Files with patterns**: {file_count}
- **Total patterns**: {total_patterns}
- **Recommendation**: Start with files having 5+ patterns for maximum impact

## Usage Instructions

1. Review each suggested fix in context
2. Verify the suggested exception types are appropriate
3. Add necessary imports at the top of files
4. Apply the fix manually
5. Test the changes

## Import Statements You May Need

```python
# For file operations
from openchronicle.domain.exceptions import InfrastructureError

# For validation/service errors  
from openchronicle.domain.exceptions import ServiceError, ValidationError

# For JSON operations
import json

# For database operations
import sqlite3
```
"""
    
    return report


def main():
    """Generate exception fix report."""
    ap = argparse.ArgumentParser(description="Generate exception fix templates")
    ap.add_argument("path", nargs="?", default="src/openchronicle",
                   help="Root directory to analyze")
    args = ap.parse_args()
    
    root = pathlib.Path(args.path).resolve()
    if not root.exists():
        print(f"Path not found: {root}")
        return 2
    
    report = generate_exception_report(root)
    print(report)
    
    return 0


if __name__ == "__main__":
    exit(main())
