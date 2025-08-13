#!/usr/bin/env python3
"""
Automated TRY002 (raise-vanilla-class) fixer for OpenChronicle.

This script fixes TRY002 violations by converting bare exception class raises
to proper exception instantiation.

Example fixes:
- raise ValueError -> raise ValueError()
- raise CustomError -> raise CustomError()
"""

import re
import sys
from pathlib import Path
from typing import Tuple


def fix_try002_in_file(file_path: Path) -> Tuple[bool, int]:
    """Fix TRY002 violations in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixes_count = 0
        
        # Pattern: raise ExceptionClass (without parentheses)
        # Look for raise followed by a word that looks like a class name
        pattern = re.compile(
            r'(\s+raise\s+)([A-Z]\w*Error|[A-Z]\w*Exception|\w*Error|\w*Exception)(\s*(?:\n|$|#))',
            re.MULTILINE
        )
        
        def add_parentheses(match):
            nonlocal fixes_count
            raise_part = match.group(1)
            exception_class = match.group(2)
            end_part = match.group(3)
            
            # Skip if it already has parentheses or arguments
            if '(' in exception_class:
                return match.group(0)
            
            fixes_count += 1
            return f"{raise_part}{exception_class}(){end_part}"
        
        content = pattern.sub(add_parentheses, content)
        
        # Write back if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, fixes_count
        
        return False, 0
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0


def main():
    if len(sys.argv) != 2:
        print("Usage: python fix_try002.py <directory>")
        sys.exit(1)
    
    target_dir = Path(sys.argv[1])
    if not target_dir.exists():
        print(f"Directory {target_dir} does not exist")
        sys.exit(1)
    
    total_files_changed = 0
    total_fixes = 0
    
    # Find all Python files
    python_files = list(target_dir.rglob("*.py"))
    
    print(f"Scanning {len(python_files)} Python files for TRY002 violations...")
    
    for py_file in python_files:
        changed, fixes = fix_try002_in_file(py_file)
        if changed:
            total_files_changed += 1
            total_fixes += fixes
            print(f"Fixed {fixes} TRY002 violations in {py_file}")
    
    print(f"\nSummary:")
    print(f"- Files changed: {total_files_changed}")
    print(f"- Total fixes: {total_fixes}")


if __name__ == "__main__":
    main()
