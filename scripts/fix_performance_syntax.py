"""
Quick fix for performance file import syntax errors.
"""
from pathlib import Path


def fix_performance_syntax():
    """Fix syntax errors in performance files."""

    root_path = Path(__file__).parent.parent

    files_to_fix = [
        "src/openchronicle/infrastructure/performance/analysis/bottleneck_analyzer.py",
        "src/openchronicle/infrastructure/performance/metrics/collector.py",
        "src/openchronicle/infrastructure/performance/metrics/storage.py"
    ]

    for file_path in files_to_fix:
        full_path = root_path / file_path
        if full_path.exists():
            try:
                content = full_path.read_text(encoding='utf-8')
                # Fix the escaped newline issue
                content = content.replace('\\n\\n#!/usr/bin/env python3', '\n#!/usr/bin/env python3')
                content = content.replace('IPerformanceInterfacePort\\n\\n#!/usr/bin/env python3', 'IPerformanceInterfacePort\n#!/usr/bin/env python3')

                full_path.write_text(content, encoding='utf-8')
                print(f"✅ Fixed syntax: {file_path}")
            except Exception as e:
                print(f"⚠️ Error fixing {file_path}: {e}")


if __name__ == "__main__":
    fix_performance_syntax()
