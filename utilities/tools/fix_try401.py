#!/usr/bin/env python3
"""
Automated TRY401 (verbose-log-message) fixer for OpenChronicle.

This script fixes TRY401 violations by removing redundant exception objects
from logging.exception() calls, since they automatically include traceback.

Example fixes:
- logger.exception(f"Error: {e}") -> logger.exception("Error")
- self.logger.exception(f"Failed {op}: {error}") -> self.logger.exception(f"Failed {op}")
"""

import re
import sys
from pathlib import Path
from typing import Tuple


def fix_try401_in_file(file_path: Path) -> Tuple[bool, int]:
    """Fix TRY401 violations in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixes_count = 0
        
        # Pattern: logger.exception(f"message: {exception_var}")
        # We need to remove the exception variable from f-strings in exception() calls
        pattern = re.compile(
            r'(\w+\.exception\(\s*)'  # logger.exception(
            r'f"([^"]*?):\s*\{(\w+)\}"'  # f"message: {exception_var}"
            r'(\s*\))',  # )
            re.MULTILINE | re.DOTALL
        )
        
        def replace_exception_fstring(match):
            nonlocal fixes_count
            prefix = match.group(1)  # logger.exception(
            message = match.group(2)  # message part
            exc_var = match.group(3)  # exception variable name
            suffix = match.group(4)  # )
            
            # Remove the exception variable from the message
            # Common patterns: "Error: {e}", "Failed operation: {error}", etc.
            fixes_count += 1
            return f'{prefix}f"{message}"' + suffix
        
        content = pattern.sub(replace_exception_fstring, content)
        
        # Pattern 2: logger.exception(f"message {exception_var}")
        pattern2 = re.compile(
            r'(\w+\.exception\(\s*)'  # logger.exception(
            r'f"([^"]*?)\s+\{(\w+)\}"'  # f"message {exception_var}"
            r'(\s*\))',  # )
            re.MULTILINE | re.DOTALL
        )
        
        def replace_exception_fstring2(match):
            nonlocal fixes_count
            prefix = match.group(1)
            message = match.group(2)
            exc_var = match.group(3)
            suffix = match.group(4)
            
            fixes_count += 1
            return f'{prefix}f"{message}"' + suffix
        
        content = pattern2.sub(replace_exception_fstring2, content)
        
        # Pattern 3: More complex cases with multiple parts
        pattern3 = re.compile(
            r'(\w+\.exception\(\s*)'
            r'f"([^"]*?)\{([^}]+)\}([^"]*?):\s*\{(\w+)\}"'
            r'(\s*\))',
            re.MULTILINE | re.DOTALL
        )
        
        def replace_complex_exception(match):
            nonlocal fixes_count
            prefix = match.group(1)
            part1 = match.group(2)
            var1 = match.group(3)
            part2 = match.group(4)
            exc_var = match.group(5)
            suffix = match.group(6)
            
            # Keep the first variable, remove the exception
            fixes_count += 1
            return f'{prefix}f"{part1}{{{var1}}}{part2}"' + suffix
        
        content = pattern3.sub(replace_complex_exception, content)
        
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
        print("Usage: python fix_try401.py <directory>")
        sys.exit(1)
    
    target_dir = Path(sys.argv[1])
    if not target_dir.exists():
        print(f"Directory {target_dir} does not exist")
        sys.exit(1)
    
    total_files_changed = 0
    total_fixes = 0
    
    # Find all Python files
    python_files = list(target_dir.rglob("*.py"))
    
    print(f"Scanning {len(python_files)} Python files for TRY401 violations...")
    
    for py_file in python_files:
        changed, fixes = fix_try401_in_file(py_file)
        if changed:
            total_files_changed += 1
            total_fixes += fixes
            print(f"Fixed {fixes} TRY401 violations in {py_file}")
    
    print(f"\nSummary:")
    print(f"- Files changed: {total_files_changed}")
    print(f"- Total fixes: {total_fixes}")


if __name__ == "__main__":
    main()
