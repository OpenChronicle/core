#!/usr/bin/env python3
"""
Fix B904 violations by adding exception chaining (from err or from None).
"""

import re
import subprocess
import sys
from pathlib import Path


def get_b904_violations():
    """Get all B904 violations from ruff."""
    result = subprocess.run(
        ["ruff", "check", "--select=B904"],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )

    print(f"Ruff return code: {result.returncode}")
    print(f"Ruff stdout length: {len(result.stdout) if result.stdout else 0}")

    violations = []
    if result.stdout:
        lines = result.stdout.strip().split('\n')
        print(f"Processing {len(lines)} lines of output")
        for line in lines:
            if 'B904' in line:
                # Parse format: file:line:col: B904 message
                parts = line.split(':')
                if len(parts) >= 3:
                    try:
                        file_path = parts[0].strip()
                        line_num = int(parts[1].strip())
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'message': line.split('B904')[1].strip() if 'B904' in line else ''
                        })
                    except (ValueError, IndexError):
                        continue

    print(f"Found {len(violations)} violations")
    return violations


def fix_b904_violation(file_path, line_num):
    """Fix a single B904 violation by adding exception chaining."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if line_num > len(lines):
            return False

        # Get the line with the violation (convert to 0-based index)
        violation_line_idx = line_num - 1
        violation_line = lines[violation_line_idx]

        # Check if this is a raise statement
        if 'raise ' not in violation_line:
            return False

        # Find the except clause that captures the original exception
        except_var = None
        for i in range(violation_line_idx - 1, max(0, violation_line_idx - 10), -1):
            except_line = lines[i].strip()
            if except_line.startswith('except'):
                # Extract variable name from "except SomeError as e:"
                match = re.search(r'except\s+[^:]+\s+as\s+(\w+):', except_line)
                if match:
                    except_var = match.group(1)
                    break
                # Or just "except:" without variable
                elif except_line.endswith('except:'):
                    except_var = None
                    break

        # If no exception variable found, use "from None"
        if except_var is None:
            # Add "from None" to suppress exception chaining
            if 'from None' not in violation_line and 'from ' not in violation_line:
                new_line = violation_line.rstrip() + ' from None\n'
                lines[violation_line_idx] = new_line
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
        else:
            # Add "from {except_var}" to preserve exception chaining
            if f'from {except_var}' not in violation_line and 'from ' not in violation_line:
                new_line = violation_line.rstrip() + f' from {except_var}\n'
                lines[violation_line_idx] = new_line
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True

        return False

    except Exception as e:
        print(f"Error fixing {file_path}:{line_num}: {e}")
        return False


def main():
    """Main function to fix B904 violations."""
    print("Finding B904 violations...")
    violations = get_b904_violations()

    if not violations:
        print("No B904 violations found.")
        return

    print(f"Found {len(violations)} B904 violations")

    fixed_count = 0
    for violation in violations:
        print(f"Fixing {violation['file']}:{violation['line']}")
        if fix_b904_violation(violation['file'], violation['line']):
            fixed_count += 1
            print("  ✓ Fixed")
        else:
            print("  ✗ Failed to fix")

    print(f"\nFixed {fixed_count}/{len(violations)} B904 violations")

    # Verify the fixes
    print("\nVerifying fixes...")
    new_violations = get_b904_violations()
    remaining_count = len(new_violations)
    print(f"Remaining B904 violations: {remaining_count}")


if __name__ == "__main__":
    main()
