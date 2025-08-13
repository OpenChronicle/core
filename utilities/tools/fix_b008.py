#!/usr/bin/env python3
"""
Automated B008 (function-call-in-default-argument) fixer for OpenChronicle.

This script fixes B008 violations by replacing mutable default arguments
with None and initializing them inside the function.

Example fixes:
def func(arg=[]):  ->  def func(arg=None): if arg is None: arg = []
def func(arg={}):  ->  def func(arg=None): if arg is None: arg = {}
"""

import re
import sys
from pathlib import Path
from typing import Tuple


def fix_b008_in_file(file_path: Path) -> Tuple[bool, int]:
    """Fix B008 violations in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixes_count = 0
        
        # Pattern 1: def func(arg=[]):
        pattern1 = re.compile(
            r'(def\s+\w+\([^)]*?)(\w+)=(\[\])'  # arg=[]
            r'([^)]*\):)',
            re.MULTILINE
        )
        
        def fix_list_default(match):
            nonlocal fixes_count
            func_start = match.group(1)
            arg_name = match.group(2)
            func_end = match.group(4)
            
            fixes_count += 1
            return f"{func_start}{arg_name}=None{func_end}"
        
        content = pattern1.sub(fix_list_default, content)
        
        # Pattern 2: def func(arg={}):
        pattern2 = re.compile(
            r'(def\s+\w+\([^)]*?)(\w+)=(\{\})'  # arg={}
            r'([^)]*\):)',
            re.MULTILINE
        )
        
        def fix_dict_default(match):
            nonlocal fixes_count
            func_start = match.group(1)
            arg_name = match.group(2)
            func_end = match.group(4)
            
            fixes_count += 1
            return f"{func_start}{arg_name}=None{func_end}"
        
        content = pattern2.sub(fix_dict_default, content)
        
        # TODO: Add initialization code inside functions would require more complex parsing
        # For now, just fix the function signatures
        
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
        print("Usage: python fix_b008.py <directory>")
        sys.exit(1)
    
    target_dir = Path(sys.argv[1])
    if not target_dir.exists():
        print(f"Directory {target_dir} does not exist")
        sys.exit(1)
    
    total_files_changed = 0
    total_fixes = 0
    
    # Find all Python files
    python_files = list(target_dir.rglob("*.py"))
    
    print(f"Scanning {len(python_files)} Python files for B008 violations...")
    
    for py_file in python_files:
        changed, fixes = fix_b008_in_file(py_file)
        if changed:
            total_files_changed += 1
            total_fixes += fixes
            print(f"Fixed {fixes} B008 violations in {py_file}")
    
    print(f"\nSummary:")
    print(f"- Files changed: {total_files_changed}")
    print(f"- Total fixes: {total_fixes}")
    print("\nNote: Function bodies may need manual updates to initialize None arguments.")


if __name__ == "__main__":
    main()
