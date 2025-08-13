#!/usr/bin/env python3
"""
Automated B904 (raise-without-from-inside-except) fixer for OpenChronicle.

This script fixes B904 violations by adding proper exception chaining with
'raise ... from err' or 'raise ... from None' patterns.

Example fixes:
- except Exception as e: raise ValueError("msg") -> raise ValueError("msg") from e
- except Exception: raise ValueError("msg") -> raise ValueError("msg") from None
"""

import ast
import re
import sys
from pathlib import Path
from typing import Tuple


def fix_b904_in_file(file_path: Path) -> Tuple[bool, int]:
    """Fix B904 violations in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixes_count = 0
        
        # Parse the file to understand the AST structure
        try:
            tree = ast.parse(content)
        except SyntaxError:
            print(f"Syntax error in {file_path}, skipping")
            return False, 0
        
        # Pattern 1: except Exception as e: raise SomeError(...) 
        # -> except Exception as e: raise SomeError(...) from e
        pattern1 = re.compile(
            r'(\s+except\s+[^:]+\s+as\s+(\w+):\s*\n)'  # except clause with variable
            r'((?:\s+[^r\n].*\n)*?)'  # optional non-raise lines
            r'(\s+)(raise\s+[^(]+\([^)]*\))'  # raise statement
            r'(?!\s+from)',  # not already followed by 'from'
            re.MULTILINE | re.DOTALL
        )
        
        def replace_with_exception_var(match):
            nonlocal fixes_count
            except_line = match.group(1)
            exc_var = match.group(2)
            middle_lines = match.group(3) or ""
            indent = match.group(4)
            raise_stmt = match.group(5)
            
            # Skip if it's a re-raise (bare raise)
            if raise_stmt.strip() == "raise":
                return match.group(0)
            
            fixes_count += 1
            return f"{except_line}{middle_lines}{indent}{raise_stmt} from {exc_var}"
        
        content = pattern1.sub(replace_with_exception_var, content)
        
        # Pattern 2: except Exception: raise SomeError(...) 
        # -> except Exception: raise SomeError(...) from None
        pattern2 = re.compile(
            r'(\s+except\s+[^:]+:\s*\n)'  # except clause without variable
            r'((?:\s+[^r\n].*\n)*?)'  # optional non-raise lines
            r'(\s+)(raise\s+[^(]+\([^)]*\))'  # raise statement
            r'(?!\s+from)',  # not already followed by 'from'
            re.MULTILINE | re.DOTALL
        )
        
        def replace_with_none(match):
            nonlocal fixes_count
            except_line = match.group(1)
            middle_lines = match.group(2) or ""
            indent = match.group(3)
            raise_stmt = match.group(4)
            
            # Skip if it's a re-raise (bare raise)
            if raise_stmt.strip() == "raise":
                return match.group(0)
                
            # Skip if the except clause includes 'as'
            if ' as ' in except_line:
                return match.group(0)
            
            fixes_count += 1
            return f"{except_line}{middle_lines}{indent}{raise_stmt} from None"
        
        content = pattern2.sub(replace_with_none, content)
        
        # Write back if changes were made
        if content != original_content:
            # Verify the result is still valid Python
            try:
                ast.parse(content)
            except SyntaxError as e:
                print(f"Generated invalid syntax in {file_path}: {e}")
                return False, 0
                
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, fixes_count
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0
    else:
        return False, 0


def main():
    if len(sys.argv) != 2:
        print("Usage: python fix_b904.py <directory>")
        sys.exit(1)
    
    target_dir = Path(sys.argv[1])
    if not target_dir.exists():
        print(f"Directory {target_dir} does not exist")
        sys.exit(1)
    
    total_files_changed = 0
    total_fixes = 0
    
    # Find all Python files
    python_files = list(target_dir.rglob("*.py"))
    
    print(f"Scanning {len(python_files)} Python files for B904 violations...")
    
    for py_file in python_files:
        changed, fixes = fix_b904_in_file(py_file)
        if changed:
            total_files_changed += 1
            total_fixes += fixes
            print(f"Fixed {fixes} B904 violations in {py_file}")
    
    print(f"\nSummary:")
    print(f"- Files changed: {total_files_changed}")
    print(f"- Total fixes: {total_fixes}")


if __name__ == "__main__":
    main()
