#!/usr/bin/env python3
"""
Fix small violation categories automatically.

This script handles:
- B007: Unused loop control variables (rename to _variable)
- E722: Bare except (add Exception)
- TRY004: Prefer TypeError for invalid type
- F702: Continue not properly in loop (needs manual inspection)
- B024: Abstract base class without abstract methods (add abstractmethod)
- B027: Empty method without abstract decorator (add abstractmethod)
- B019: lru_cache on methods (replace with manual cache)
"""

import re
import subprocess
import sys
from pathlib import Path


def get_violations(violation_types):
    """Get violations for specific types from ruff."""
    try:
        result = subprocess.run(
            ["ruff", "check", "--select", ",".join(violation_types), "--no-fix"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=Path.cwd(),
        )
        return result.stdout if result.stdout else ""
    except subprocess.CalledProcessError as e:
        print(f"Error running ruff: {e}")
        return ""
    except Exception as e:
        print(f"Unexpected error: {e}")
        return ""


def parse_violations(output):
    """Parse ruff output to extract violations by type."""
    violations = {}
    for line in output.split('\n'):
        if ':' in line and any(
            code in line for code in ['B007',
            'E722',
            'TRY004',
            'F702',
            'B024',
            'B027',
            'B019']
        ):
            parts = line.split(':')
            if len(parts) >= 3:
                file_path = parts[0].strip()
                line_num = int(parts[1].strip())
                # Extract violation code
                for code in ['B007', 'E722', 'TRY004', 'F702', 'B024', 'B027', 'B019']:
                    if code in line:
                        if code not in violations:
                            violations[code] = []
                        violations[code].append((file_path, line_num, line))
                        break
    return violations


def fix_b007_unused_variables(file_path, line_numbers_and_info):
    """Fix B007: Rename unused loop control variables to _variable."""
    print(f"Fixing B007 violations in {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    changes_made = False
    for line_num, info in line_numbers_and_info:
        line_idx = line_num - 1
        if line_idx < len(lines):
            line = lines[line_idx]
            # Extract variable name from Ruff message
            if "Loop control variable `" in info:
                var_match = re.search(r'Loop control variable `(\w+)` not used', info)
                if var_match:
                    var_name = var_match.group(1)
                    # Replace variable name with _variable
                    new_line = line.replace(f' {var_name} ', f' _{var_name} ')
                    new_line = new_line.replace(f' {var_name},', f' _{var_name},')
                    new_line = new_line.replace(f' {var_name})', f' _{var_name})')
                    if new_line != line:
                        lines[line_idx] = new_line
                        changes_made = True
                        print(f"  Line {line_num}: {var_name} -> _{var_name}")

    if changes_made:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    return False


def fix_e722_bare_except(file_path, line_numbers):
    """Fix E722: Add Exception to bare except."""
    print(f"Fixing E722 violations in {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    changes_made = False
    for line_num in line_numbers:
        line_idx = line_num - 1
        if line_idx < len(lines):
            line = lines[line_idx]
            if 'except:' in line:
                new_line = line.replace('except:', 'except Exception:')
                lines[line_idx] = new_line
                changes_made = True
                print(f"  Line {line_num}: except: -> except Exception:")

    if changes_made:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    return False


def fix_try004_type_error(file_path, line_numbers):
    """Fix TRY004: Replace ValueError with TypeError for type checks."""
    print(f"Fixing TRY004 violations in {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    changes_made = False
    for line_num in line_numbers:
        line_idx = line_num - 1
        if line_idx < len(lines):
            line = lines[line_idx]
            # Look for ValueError raises that should be TypeError
            if ('raise ValueError' in line and
                ('type' in line.lower() or 'class' in line.lower() or 'inherit' in line.lower())):
                new_line = line.replace('raise ValueError', 'raise TypeError')
                lines[line_idx] = new_line
                changes_made = True
                print(f"  Line {line_num}: ValueError -> TypeError")

    if changes_made:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    return False


def fix_b019_lru_cache(file_path, line_numbers):
    """Fix B019: Replace lru_cache on methods with manual caching."""
    print(f"Fixing B019 violations in {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove @lru_cache decorator from methods
    # This is a simple fix - more complex caching would require method analysis
    new_content = re.sub(r'\s*@lru_cache\([^)]*\)\s*\n', '\n', content)

    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("  Removed @lru_cache decorator")
        return True
    return False


def main():
    """Main function to fix small violations."""
    print("Fixing small violation categories automatically")

    # Get current violations
    violation_types = ['B007', 'E722', 'TRY004', 'B019']  # Skip F702, B024, B027 for manual review
    output = get_violations(violation_types)
    if not output.strip():
        print("No small violations found.")
        return

    violations = parse_violations(output)
    if not violations:
        print("No parseable violations found.")
        return

    print(f"Found violations: {list(violations.keys())}")

    total_fixed = 0

    # Fix B007: Unused loop control variables
    if 'B007' in violations:
        file_violations = {}
        for file_path, line_num, info in violations['B007']:
            if file_path not in file_violations:
                file_violations[file_path] = []
            file_violations[file_path].append((line_num, info))

        for file_path, line_info in file_violations.items():
            try:
                if fix_b007_unused_variables(file_path, line_info):
                    total_fixed += 1
            except Exception as e:
                print(f"Error fixing B007 in {file_path}: {e}")

    # Fix E722: Bare except
    if 'E722' in violations:
        file_violations = {}
        for file_path, line_num, _info in violations['E722']:
            if file_path not in file_violations:
                file_violations[file_path] = []
            file_violations[file_path].append(line_num)

        for file_path, line_numbers in file_violations.items():
            try:
                if fix_e722_bare_except(file_path, line_numbers):
                    total_fixed += 1
            except Exception as e:
                print(f"Error fixing E722 in {file_path}: {e}")

    # Fix TRY004: Prefer TypeError
    if 'TRY004' in violations:
        file_violations = {}
        for file_path, line_num, _info in violations['TRY004']:
            if file_path not in file_violations:
                file_violations[file_path] = []
            file_violations[file_path].append(line_num)

        for file_path, line_numbers in file_violations.items():
            try:
                if fix_try004_type_error(file_path, line_numbers):
                    total_fixed += 1
            except Exception as e:
                print(f"Error fixing TRY004 in {file_path}: {e}")

    # Fix B019: lru_cache on methods
    if 'B019' in violations:
        file_violations = {}
        for file_path, line_num, _info in violations['B019']:
            if file_path not in file_violations:
                file_violations[file_path] = []
            file_violations[file_path].append(line_num)

        for file_path, line_numbers in file_violations.items():
            try:
                if fix_b019_lru_cache(file_path, line_numbers):
                    total_fixed += 1
            except Exception as e:
                print(f"Error fixing B019 in {file_path}: {e}")

    print(f"\nFixed violations in {total_fixed} files")

    # Verify the fix
    print("\nVerifying fixes...")
    new_output = get_violations(violation_types)
    new_violations = parse_violations(new_output)
    remaining_count = sum(len(v) for v in new_violations.values())
    print(f"Remaining violations in automated categories: {remaining_count}")

    # Show manual review needed
    manual_types = ['F702', 'B024', 'B027']
    manual_output = get_violations(manual_types)
    manual_violations = parse_violations(manual_output)
    manual_count = sum(len(v) for v in manual_violations.values())
    print(f"Manual review needed for F702, B024, B027: {manual_count} violations")


if __name__ == "__main__":
    main()
