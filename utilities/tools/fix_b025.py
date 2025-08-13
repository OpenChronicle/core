#!/usr/bin/env python3
"""
Automated B025 (duplicate-try-block-exception) fixer for OpenChronicle.

This script fixes B025 violations by consolidating duplicate exception
handlers in try-except blocks.

Example fixes:
except ValueError as e:
    handle_error()
except ValueError as e:
    handle_error()

->

except ValueError as e:
    handle_error()
"""

import re
import sys
from pathlib import Path
from typing import Tuple


def fix_b025_in_file(file_path: Path) -> Tuple[bool, int]:
    """Fix B025 violations in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixes_count = 0
        
        # Pattern: Find consecutive except blocks with same exception type
        # This is a simplified approach for common cases
        pattern = re.compile(
            r'(\s+except\s+([^:]+):\s*\n'  # First except clause
            r'(?:\s+[^\n]+\n)*?)'  # First except body
            r'(\s+except\s+\2:\s*\n'  # Duplicate except clause (same exception)
            r'(?:\s+[^\n]+\n)*?)',  # Duplicate except body
            re.MULTILINE | re.DOTALL
        )
        
        def consolidate_except_blocks(match):
            nonlocal fixes_count
            first_block = match.group(1)
            exception_type = match.group(2)
            duplicate_block = match.group(3)
            
            # For safety, only consolidate if the blocks are identical
            # or if one is clearly a subset/duplicate
            first_body = first_block.split('\n')[1:-1]  # Skip except line and last empty
            duplicate_body = duplicate_block.split('\n')[1:-1]  # Skip except line and last empty
            
            # Simple case: identical blocks
            if first_body == duplicate_body:
                fixes_count += 1
                return first_block  # Keep only the first block
            
            # Don't consolidate complex cases for safety
            return match.group(0)
        
        content = pattern.sub(consolidate_except_blocks, content)
        
        # Write back if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, fixes_count
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0
    else:
        return False, 0
        print(f"Error processing {file_path}: {e}")
        return False, 0


def main():
    if len(sys.argv) != 2:
        print("Usage: python fix_b025.py <directory>")
        sys.exit(1)
    
    target_dir = Path(sys.argv[1])
    if not target_dir.exists():
        print(f"Directory {target_dir} does not exist")
        sys.exit(1)
    
    total_files_changed = 0
    total_fixes = 0
    
    # Find all Python files
    python_files = list(target_dir.rglob("*.py"))
    
    print(f"Scanning {len(python_files)} Python files for B025 violations...")
    
    for py_file in python_files:
        changed, fixes = fix_b025_in_file(py_file)
        if changed:
            total_files_changed += 1
            total_fixes += fixes
            print(f"Fixed {fixes} B025 violations in {py_file}")
    
    print(f"\nSummary:")
    print(f"- Files changed: {total_files_changed}")
    print(f"- Total fixes: {total_fixes}")


if __name__ == "__main__":
    main()
