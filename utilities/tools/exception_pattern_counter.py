#!/usr/bin/env python3
"""
Exception Pattern Counter - Find high-impact files for targeted fixing
"""

import subprocess
import collections
import pathlib


def count_patterns_by_file(root_path: str = "src/openchronicle") -> dict:
    """Count exception patterns by file."""
    try:
        result = subprocess.run(['python', 'utilities/tools/exception_hygiene.py', root_path], 
                               capture_output=True, text=True, cwd=pathlib.Path.cwd())
        
        lines = result.stdout.split('\n')
        file_counts = collections.Counter()
        
        for line in lines:
            if '.py:' in line and ' - ' in line:
                # Extract file path
                parts = line.split(' - ')
                if len(parts) >= 2:
                    file_part = parts[-1].strip()
                    file_counts[file_part] += 1
        
        return file_counts
    
    except Exception as e:
        print(f"Error counting patterns: {e}")
        return {}


def main():
    """Show files ranked by exception pattern count."""
    print("Analyzing exception patterns by file...")
    
    file_counts = count_patterns_by_file()
    
    if not file_counts:
        print("No patterns found or error occurred")
        return
    
    print(f"\nTop files by exception pattern count (Total: {sum(file_counts.values())} patterns):")
    print("=" * 80)
    
    for i, (file_path, count) in enumerate(file_counts.most_common(20), 1):
        # Shorten path for display
        display_path = file_path.replace('C:\\Temp\\openchronicle-core\\src\\openchronicle\\', '')
        print(f"{i:2d}. {count:2d} patterns: {display_path}")
    
    # Provide recommendations
    high_impact = [f for f, c in file_counts.most_common(5) if c >= 5]
    medium_impact = [f for f, c in file_counts.most_common(15) if 2 <= c < 5]
    
    print(f"\n** RECOMMENDATIONS **")
    print(f"High Impact (5+ patterns): {len(high_impact)} files")
    print(f"Medium Impact (2-4 patterns): {len(medium_impact)} files") 
    print(f"Low Impact (1 pattern): {len([f for f, c in file_counts.items() if c == 1])} files")
    
    print(f"\nSuggested approach:")
    print(f"1. Target high-impact files first (5+ patterns each)")
    print(f"2. Batch process medium-impact files")
    print(f"3. Consider automation for low-impact files")


if __name__ == "__main__":
    main()
