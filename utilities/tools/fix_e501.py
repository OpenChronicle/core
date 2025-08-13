#!/usr/bin/env python3
"""
Automated E501 (line-too-long) fixer for OpenChronicle.

This script fixes E501 violations by splitting long lines at safe breakpoints
like commas, operators, and string concatenations.

Example fixes:
- Long function calls -> Split at commas
- Long imports -> Split import lists
- Long string concatenations -> Split with proper continuation
"""

import re
import sys
from pathlib import Path
from typing import Tuple


def fix_e501_in_file(file_path: Path) -> Tuple[bool, int]:
    """Fix E501 violations in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        original_lines = lines.copy()
        fixes_count = 0
        max_line_length = 88
        
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Skip if line is not too long
            if len(line.rstrip()) <= max_line_length:
                new_lines.append(line)
                i += 1
                continue
            
            # Try to fix long lines
            fixed_line = fix_long_line(line, max_line_length)
            if fixed_line != line:
                fixes_count += 1
                if isinstance(fixed_line, list):
                    new_lines.extend(fixed_line)
                else:
                    new_lines.append(fixed_line)
            else:
                new_lines.append(line)
            i += 1
        
        # Write back if changes were made
        if new_lines != original_lines:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            return True, fixes_count
        
        return False, 0
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0


def fix_long_line(line: str, max_length: int):
    """Try to fix a single long line by splitting it appropriately."""
    stripped = line.rstrip()
    if len(stripped) <= max_length:
        return line
    
    # Get indentation
    indent = len(line) - len(line.lstrip())
    base_indent = " " * indent
    
    # Pattern 1: Long function calls with multiple arguments
    if re.search(r'\([^)]*,.*\)', stripped):
        return split_function_call(line, max_length, base_indent)
    
    # Pattern 2: Long import statements
    if stripped.lstrip().startswith(('from ', 'import ')):
        return split_import_statement(line, max_length, base_indent)
    
    # Pattern 3: Long string concatenations
    if ' + ' in stripped and ('"' in stripped or "'" in stripped):
        return split_string_concatenation(line, max_length, base_indent)
    
    # Pattern 4: Long assignments with operators
    if ' = ' in stripped:
        return split_assignment(line, max_length, base_indent)
    
    return line  # Can't safely split


def split_function_call(line: str, max_length: int, base_indent: str):
    """Split a long function call across multiple lines."""
    stripped = line.rstrip()
    
    # Find the function call pattern
    match = re.match(r'(\s*\w+.*?\()(.*?)(\).*?)$', stripped)
    if not match:
        return line
    
    func_start = match.group(1)
    args = match.group(2)
    func_end = match.group(3)
    
    # Split arguments at commas
    if ',' in args:
        arg_parts = []
        current_arg = ""
        paren_depth = 0
        
        for char in args:
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == ',' and paren_depth == 0:
                arg_parts.append(current_arg.strip())
                current_arg = ""
                continue
            current_arg += char
        
        if current_arg.strip():
            arg_parts.append(current_arg.strip())
        
        if len(arg_parts) > 1:
            result = [f"{func_start}\n"]
            for i, arg in enumerate(arg_parts):
                comma = "," if i < len(arg_parts) - 1 else ""
                result.append(f"{base_indent}    {arg}{comma}\n")
            result.append(f"{base_indent}{func_end}\n")
            return result
    
    return line


def split_import_statement(line: str, max_length: int, base_indent: str):
    """Split a long import statement."""
    stripped = line.rstrip()
    
    # Pattern: from module import (a, b, c)
    match = re.match(r'(\s*from\s+\S+\s+import\s+\()(.*?)(\))', stripped)
    if match:
        import_start = match.group(1)
        imports = match.group(2)
        import_end = match.group(3)
        
        if ',' in imports:
            import_parts = [part.strip() for part in imports.split(',') if part.strip()]
            if len(import_parts) > 1:
                result = [f"{import_start}\n"]
                for i, imp in enumerate(import_parts):
                    comma = "," if i < len(import_parts) - 1 else ""
                    result.append(f"{base_indent}    {imp}{comma}\n")
                result.append(f"{base_indent}{import_end}\n")
                return result
    
    return line


def split_string_concatenation(line: str, max_length: int, base_indent: str):
    """Split long string concatenations."""
    stripped = line.rstrip()
    
    # Simple case: split at ' + ' operators
    if ' + ' in stripped:
        parts = stripped.split(' + ')
        if len(parts) > 1:
            result = []
            first = True
            for i, part in enumerate(parts):
                if first:
                    result.append(f"{part.rstrip()}\n")
                    first = False
                else:
                    result.append(f"{base_indent}    + {part.rstrip()}\n")
            return result
    
    return line


def split_assignment(line: str, max_length: int, base_indent: str):
    """Split long assignment statements."""
    stripped = line.rstrip()
    
    # Pattern: variable = long_expression
    match = re.match(r'(\s*\w+.*?=\s*)(.*)', stripped)
    if match:
        var_part = match.group(1)
        expr_part = match.group(2)
        
        # If the variable part itself is too long, can't split
        if len(var_part) > max_length - 10:
            return line
        
        # Try to break at operators
        for op in [' and ', ' or ', ' + ', ' - ', ' * ', ' / ']:
            if op in expr_part:
                parts = expr_part.split(op, 1)
                if len(parts) == 2:
                    return [
                        f"{var_part}{parts[0].rstrip()}{op.rstrip()}\n",
                        f"{base_indent}    {op.lstrip()}{parts[1].rstrip()}\n"
                    ]
    
    return line


def main():
    if len(sys.argv) != 2:
        print("Usage: python fix_e501.py <directory>")
        sys.exit(1)
    
    target_dir = Path(sys.argv[1])
    if not target_dir.exists():
        print(f"Directory {target_dir} does not exist")
        sys.exit(1)
    
    total_files_changed = 0
    total_fixes = 0
    
    # Find all Python files
    python_files = list(target_dir.rglob("*.py"))
    
    print(f"Scanning {len(python_files)} Python files for E501 violations...")
    
    for py_file in python_files:
        changed, fixes = fix_e501_in_file(py_file)
        if changed:
            total_files_changed += 1
            total_fixes += fixes
            print(f"Fixed {fixes} E501 violations in {py_file}")
    
    print(f"\nSummary:")
    print(f"- Files changed: {total_files_changed}")
    print(f"- Total fixes: {total_fixes}")


if __name__ == "__main__":
    main()
