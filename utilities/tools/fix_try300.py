#!/usr/bin/env python3
"""
Automated TRY300 (try-consider-else) fixer for OpenChronicle.

This script fixes TRY300 violations by moving return statements from try blocks
to else blocks where appropriate.

Example fixes:
try:
    operation()
    return result
except Exception:
    handle_error()

->

try:
    operation()
except Exception:
    handle_error()
else:
    return result
"""

import re
import sys
from pathlib import Path
from typing import Tuple


def fix_try300_in_file(file_path: Path) -> Tuple[bool, int]:
    """Fix TRY300 violations in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixes_count = 0
        
        # Pattern: try block ending with return statement before except
        # Simple pattern for common cases
        pattern = re.compile(
            r'(\s+try:\s*\n)'  # try:
            r'((?:\s+.*\n)*?)'  # try block content
            r'(\s+)(return\s+[^\n]*)\n'  # return statement
            r'(\s+except\s+[^:]*:\s*\n)'  # except clause
            r'((?:\s+.*\n)*?)'  # except block content
            r'(?=\s*(?:def|class|\w+\s*=|\n\s*\n|$))',  # end of block
            re.MULTILINE | re.DOTALL
        )
        
        def move_return_to_else(match):
            nonlocal fixes_count
            try_start = match.group(1)
            try_content = match.group(2)
            return_indent = match.group(3)
            return_stmt = match.group(4)
            except_clause = match.group(5)
            except_content = match.group(6)
            
            # Only move simple return statements to avoid complexity
            if 'return' in try_content:  # Multiple returns, skip
                return match.group(0)
            
            fixes_count += 1
            return (f"{try_start}{try_content}"
                   f"{except_clause}{except_content}"
                   f"{return_indent}else:\n"
                   f"{return_indent}    {return_stmt}\n")
        
        content = pattern.sub(move_return_to_else, content)
        
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
        print("Usage: python fix_try300.py <directory>")
        sys.exit(1)
    
    target_dir = Path(sys.argv[1])
    if not target_dir.exists():
        print(f"Directory {target_dir} does not exist")
        sys.exit(1)
    
    total_files_changed = 0
    total_fixes = 0
    
    # Find all Python files
    python_files = list(target_dir.rglob("*.py"))
    
    print(f"Scanning {len(python_files)} Python files for TRY300 violations...")
    
    for py_file in python_files:
        changed, fixes = fix_try300_in_file(py_file)
        if changed:
            total_files_changed += 1
            total_fixes += fixes
            print(f"Fixed {fixes} TRY300 violations in {py_file}")
    
    print(f"\nSummary:")
    print(f"- Files changed: {total_files_changed}")
    print(f"- Total fixes: {total_fixes}")


if __name__ == "__main__":
    main()
