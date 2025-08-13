#!/usr/bin/env python3
"""
Fix B025 violations: Duplicate exception handlers.

This script removes duplicate exception handlers by identifying and removing
identical exception handling blocks.
"""

import re
import subprocess
import sys
from pathlib import Path


def get_b025_violations():
    """Get all B025 violations from ruff."""
    try:
        result = subprocess.run(
            ["ruff", "check", "--select", "B025", "--no-fix"],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running ruff: {e}")
        return ""


def parse_violations(output):
    """Parse ruff output to extract file paths and line numbers."""
    violations = []
    for line in output.split('\n'):
        if ':' in line and 'B025' in line:
            parts = line.split(':')
            if len(parts) >= 3:
                file_path = parts[0].strip()
                line_num = int(parts[1].strip())
                violations.append((file_path, line_num))
    return violations


def fix_duplicate_exception_handlers(file_path, line_numbers):
    """Fix duplicate exception handlers in a file."""
    print(f"Fixing B025 violations in {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Group line numbers by proximity to identify duplicate blocks
    # Sort line numbers and group consecutive ones
    line_numbers.sort()
    groups = []
    current_group = [line_numbers[0]]

    for i in range(1, len(line_numbers)):
        if line_numbers[i] - line_numbers[i-1] <= 3:  # Within 3 lines
            current_group.append(line_numbers[i])
        else:
            groups.append(current_group)
            current_group = [line_numbers[i]]
    groups.append(current_group)

    # Process each group (remove duplicates)
    lines_to_remove = set()

    for group in groups:
        if len(group) > 1:
            # Check if these are actually duplicate except blocks
            for line_num in group[1:]:  # Keep first, remove others
                # Check if it's an except line
                line_idx = line_num - 1
                if line_idx < len(lines) and 'except' in lines[line_idx]:
                    # Mark this block for removal
                    # Find the end of this except block
                    block_start = line_idx
                    block_end = block_start + 1

                    # Find the end of the except block
                    indent_level = len(lines[block_start]) - len(lines[block_start].lstrip())
                    while block_end < len(lines):
                        line = lines[block_end]
                        if line.strip() == '':
                            block_end += 1
                            continue
                        current_indent = len(line) - len(line.lstrip())
                        if current_indent <= indent_level and line.strip():
                            break
                        block_end += 1

                    # Mark all lines in this block for removal
                    for i in range(block_start, block_end):
                        lines_to_remove.add(i)

    # Remove the duplicate lines
    if lines_to_remove:
        new_lines = [line for i, line in enumerate(lines) if i not in lines_to_remove]

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        print(f"  Removed {len(lines_to_remove)} duplicate lines")
        return True

    return False


def main():
    """Main function to fix B025 violations."""
    print("Fixing B025 violations: Duplicate exception handlers")

    # Get current violations
    output = get_b025_violations()
    if not output.strip():
        print("No B025 violations found.")
        return

    violations = parse_violations(output)
    if not violations:
        print("No parseable B025 violations found.")
        return

    print(f"Found {len(violations)} B025 violations")

    # Group violations by file
    file_violations = {}
    for file_path, line_num in violations:
        if file_path not in file_violations:
            file_violations[file_path] = []
        file_violations[file_path].append(line_num)

    # Fix each file
    total_fixed = 0
    for file_path, line_numbers in file_violations.items():
        try:
            if fix_duplicate_exception_handlers(file_path, line_numbers):
                total_fixed += 1
        except Exception as e:
            print(f"Error fixing {file_path}: {e}")

    print(f"\nFixed B025 violations in {total_fixed} files")

    # Verify the fix
    print("\nVerifying fixes...")
    new_output = get_b025_violations()
    new_violations = parse_violations(new_output)
    print(f"Remaining B025 violations: {len(new_violations)}")


if __name__ == "__main__":
    main()
