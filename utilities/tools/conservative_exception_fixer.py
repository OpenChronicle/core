#!/usr/bin/env python3
"""
Conservative Exception Handler Fixer

Applies minimal, safe exception handling improvements with high confidence.
Focuses on specific patterns that can be safely automated.

Usage:
    python conservative_exception_fixer.py [path] [--dry-run] [--max-files N]
"""

import argparse
import pathlib
import re
import sys
from typing import List, Tuple


class ConservativeExceptionFixer:
    """Conservative, high-confidence exception handling fixes."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.patterns = [
            # Match: except Exception as e: followed by simple patterns
            (re.compile(r'^(\s*)except Exception as e:\s*$'), 'exception_as_e'),
            # Match: except: followed by simple patterns  
            (re.compile(r'^(\s*)except:\s*$'), 'bare_except'),
        ]
        
    def fix_simple_exception_handler(self, lines: List[str], match_idx: int, pattern_type: str, indent: str) -> List[str]:
        """Fix simple exception handlers with conservative replacements."""
        
        # Analyze the next few lines to understand the pattern
        next_lines = []
        for i in range(match_idx + 1, min(len(lines), match_idx + 4)):
            if lines[i].strip() == '':
                continue
            next_line_indent = len(lines[i]) - len(lines[i].lstrip())
            expected_indent = len(indent) + 4
            
            if next_line_indent < expected_indent:
                break  # End of except block
            next_lines.append(lines[i])
        
        # Conservative patterns we can safely fix
        if len(next_lines) == 1:
            next_line = next_lines[0].strip()
            
            # Pattern: Simple re-raise
            if next_line in ['raise', 'pass']:
                if pattern_type == 'bare_except':
                    return [f"{indent}except Exception:"]
                else:
                    return [f"{indent}except Exception as e:"]
            
            # Pattern: Simple logging + re-raise
            if next_line.startswith('logger.') and 'raise' in lines[match_idx + 2:match_idx + 3]:
                return [
                    f"{indent}except Exception as e:",
                    f"{indent}    # Error logged - re-raise to preserve stack trace",
                    f"{indent}    {next_line}",
                    f"{indent}    raise"
                ]
            
            # Pattern: Simple return None/False
            if next_line in ['return None', 'return False', 'return', 'continue']:
                return [
                    f"{indent}except Exception as e:",
                    f"{indent}    # Defensive handler - {next_line}",
                    f"{indent}    {next_line}"
                ]
        
        # If we can't confidently fix it, leave it alone
        return None
    
    def process_file(self, file_path: pathlib.Path) -> Tuple[bool, List[str]]:
        """Process a single file with conservative fixes."""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            original_lines = lines.copy()
            changes = []
            
            i = 0
            while i < len(lines):
                line = lines[i]
                
                for pattern, pattern_type in self.patterns:
                    match = pattern.match(line)
                    if match:
                        indent = match.group(1)
                        
                        # Try to fix this pattern
                        replacement = self.fix_simple_exception_handler(lines, i, pattern_type, indent)
                        
                        if replacement:
                            # Remove original except block
                            original_except_end = i + 1
                            while (original_except_end < len(lines) and 
                                   lines[original_except_end].strip() and
                                   len(lines[original_except_end]) - len(lines[original_except_end].lstrip()) > len(indent)):
                                original_except_end += 1
                            
                            # Replace with new handler
                            lines[i:original_except_end] = replacement
                            changes.append(f"Line {i+1}: Conservative exception fix applied")
                            i += len(replacement) - 1  # Adjust index
                            break
                
                i += 1
            
            # Write changes if modified
            modified = lines != original_lines
            if modified and not self.dry_run:
                new_content = '\n'.join(lines)
                file_path.write_text(new_content, encoding='utf-8')
                changes.append(f"File updated: {file_path}")
            
        except Exception as e:
            return False, [f"Error processing {file_path}: {e}"]
        else:
            return modified, changes


def scan_for_simple_patterns(path: pathlib.Path) -> List[Tuple[int, str]]:
    """Scan for simple exception patterns we can safely fix."""
    simple_patterns = [
        re.compile(r"except\s*:\s*$"),           # bare except
        re.compile(r"except\s+Exception\s+as\s+\w+:\s*$"),  # except Exception as e:
    ]
    
    hits = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for lineno, line in enumerate(lines, start=1):
            for pattern in simple_patterns:
                if pattern.search(line):
                    # Check if next line is simple (good candidate for fixing)
                    if lineno < len(lines):
                        next_line = lines[lineno].strip()
                        if next_line in ['raise', 'pass', 'return None', 'return False', 'return', 'continue'] or next_line.startswith('logger.'):
                            hits.append((lineno, line.rstrip()))
                            break
    except Exception:
        pass
    
    return hits


def iter_py_files(root: pathlib.Path) -> List[pathlib.Path]:
    """Get Python files, excluding tests and generated content."""
    files = []
    for p in root.rglob("*.py"):
        if any(part in {"tests", "htmlcov", "__pycache__"} for part in p.parts):
            continue
        files.append(p)
    return files


def main() -> int:
    """Main execution function."""
    ap = argparse.ArgumentParser(description="Conservative exception handling fixes")
    ap.add_argument("path", nargs="?", default="src/openchronicle",
                   help="Root directory to scan")
    ap.add_argument("--dry-run", action="store_true",
                   help="Show what would be changed without making changes")
    ap.add_argument("--max-files", type=int, default=20,
                   help="Maximum number of files to process")
    
    args = ap.parse_args()
    
    root = pathlib.Path(args.path).resolve()
    if not root.exists():
        print(f"Path not found: {root}")
        return 2
    
    # Find files with simple patterns we can fix
    candidates = []
    for file_path in iter_py_files(root):
        simple_patterns = scan_for_simple_patterns(file_path)
        if simple_patterns:
            candidates.append((file_path, len(simple_patterns)))
    
    # Sort by pattern count
    candidates.sort(key=lambda x: x[1], reverse=True)
    target_files = [f for f, _ in candidates[:args.max_files]]
    
    if not target_files:
        print("No files with simple fixable patterns found")
        return 0
    
    print(f"Processing {len(target_files)} files with simple exception patterns...")
    
    fixer = ConservativeExceptionFixer(dry_run=args.dry_run)
    total_modified = 0
    
    for file_path in target_files:
        print(f"\nProcessing: {file_path}")
        
        modified, changes = fixer.process_file(file_path)
        
        if modified:
            total_modified += 1
            print(f"  ✓ Modified")
            for change in changes[:5]:  # Show first 5 changes
                print(f"    - {change}")
            if len(changes) > 5:
                print(f"    ... and {len(changes) - 5} more changes")
        else:
            print(f"  - No safe changes identified")
    
    print(f"\nSummary: {total_modified} files modified")
    
    if args.dry_run:
        print("\nDRY RUN - No actual changes were made")
        print("Run without --dry-run to apply changes")
    else:
        print(f"\nChanges applied to {total_modified} files")
        print("Run exception hygiene check to see remaining patterns")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
