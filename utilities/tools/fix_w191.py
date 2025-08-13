#!/usr/bin/env python3
"""
Automated W191 (tab-indentation) fixer for OpenChronicle.

This script fixes W191 violations by replacing tabs with spaces
using the standard 4-space indentation.
"""

import sys
from pathlib import Path
from typing import Tuple


def fix_w191_in_file(file_path: Path) -> Tuple[bool, int]:
    """Fix W191 violations in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace tabs with 4 spaces
        fixed_content = content.expandtabs(4)
        
        if fixed_content != original_content:
            # Count number of lines that changed
            original_lines = original_content.splitlines()
            fixed_lines = fixed_content.splitlines()
            
            fixes_count = sum(1 for orig, fixed in zip(original_lines, fixed_lines) 
                            if orig != fixed)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True, fixes_count
        
        return False, 0
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0


def main():
    if len(sys.argv) != 2:
        print("Usage: python fix_w191.py <directory>")
        sys.exit(1)
    
    target_dir = Path(sys.argv[1])
    if not target_dir.exists():
        print(f"Directory {target_dir} does not exist")
        sys.exit(1)
    
    total_files_changed = 0
    total_fixes = 0
    
    # Find all Python files
    python_files = list(target_dir.rglob("*.py"))
    
    print(f"Scanning {len(python_files)} Python files for W191 violations...")
    
    for py_file in python_files:
        changed, fixes = fix_w191_in_file(py_file)
        if changed:
            total_files_changed += 1
            total_fixes += fixes
            print(f"Fixed {fixes} W191 violations in {py_file}")
    
    print(f"\nSummary:")
    print(f"- Files changed: {total_files_changed}")
    print(f"- Total fixes: {total_fixes}")


if __name__ == "__main__":
    main()
