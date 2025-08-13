#!/usr/bin/env python3
"""
Fix TRY300 violations by moving statements to else blocks.
"""

import re
import subprocess
import sys
from pathlib import Path


def get_try300_violations():
    """Get all TRY300 violations from ruff."""
    result = subprocess.run(
        ["ruff", "check", "--select=TRY300"],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )

    violations = []
    if result.stdout:
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if 'TRY300' in line:
                # Parse format: file:line:col: TRY300 message
                parts = line.split(':')
                if len(parts) >= 3:
                    try:
                        file_path = parts[0].strip()
                        line_num = int(parts[1].strip())
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'message': line.split('TRY300')[1].strip() if 'TRY300' in line else ''
                        })
                    except (ValueError, IndexError):
                        continue

    return violations


def fix_try300_violation(file_path, line_num):
    """Fix a single TRY300 violation."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if line_num > len(lines):
            return False

        # Get the line with the violation (convert to 0-based index)
        violation_line = lines[line_num - 1]

        # Look for try block structure
        indent_level = len(violation_line) - len(violation_line.lstrip())

        # Find the try statement by going backwards
        try_line_idx = None
        for i in range(line_num - 2, -1, -1):
            line = lines[i].strip()
            if line.startswith('try:') and len(lines[i]) - len(lines[i].lstrip()) < indent_level:
                try_line_idx = i
                break

        if try_line_idx is None:
            return False

        # Find existing except blocks
        except_blocks = []
        for i in range(line_num, len(lines)):
            line = lines[i].strip()
            line_indent = len(lines[i]) - len(lines[i].lstrip())

            if line_indent <= len(lines[try_line_idx]) - len(lines[try_line_idx].lstrip()):
                break

            if line.startswith('except'):
                except_blocks.append(i)

        if not except_blocks:
            return False

        # Insert else block before first except
        first_except_idx = except_blocks[0]

        # Get indentation of except block
        except_indent = len(lines[first_except_idx]) - len(lines[first_except_idx].lstrip())
        indent_str = ' ' * except_indent

        # Move the violation line to else block
        violation_content = violation_line.strip()

        # Create else block
        else_block = [
            f"{indent_str}else:\n",
            f"{indent_str}    {violation_content}\n"
        ]

        # Remove original violation line
        new_lines = lines[:line_num-1] + lines[line_num:]

        # Insert else block
        new_lines = new_lines[:first_except_idx-1] + else_block + new_lines[first_except_idx-1:]

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        return True

    except Exception as e:
        print(f"Error fixing {file_path}:{line_num}: {e}")
        return False


def main():
    """Main function to fix TRY300 violations."""
    print("Finding TRY300 violations...")
    violations = get_try300_violations()

    if not violations:
        print("No TRY300 violations found.")
        return

    print(f"Found {len(violations)} TRY300 violations")

    fixed_count = 0
    for violation in violations:
        print(f"Fixing {violation['file']}:{violation['line']}")
        if fix_try300_violation(violation['file'], violation['line']):
            fixed_count += 1
            print("  ✓ Fixed")
        else:
            print("  ✗ Failed to fix")

    print(f"\nFixed {fixed_count}/{len(violations)} TRY300 violations")


if __name__ == "__main__":
    main()
