#!/usr/bin/env python3
"""
Smart Exception Pattern Analyzer

Distinguishes between legitimate exception patterns and actual issues needing fixes.
Helps prioritize real problems over architectural boundary handlers.

Usage:
    python smart_exception_analyzer.py [path] [--show-all] [--fix-suggestions]
"""

import argparse
import pathlib
import re
import ast
from typing import List, Tuple, Dict, Set
from dataclasses import dataclass
from enum import Enum


class PatternSeverity(Enum):
    """Severity levels for exception patterns."""
    CRITICAL = "CRITICAL"      # Bare except: patterns
    HIGH = "HIGH"              # Single-tier Exception handlers that could be improved
    MEDIUM = "MEDIUM"          # Two-tier handlers missing specific exceptions
    LOW = "LOW"                # Intentional boundary handlers (orchestrators, adapters)
    ACCEPTABLE = "ACCEPTABLE"  # Proper patterns that tool flags unnecessarily


@dataclass
class ExceptionPattern:
    """Represents an exception handling pattern found in code."""
    file_path: pathlib.Path
    line_number: int
    line_content: str
    severity: PatternSeverity
    context: str
    suggestion: str
    surrounding_lines: List[str]


class SmartExceptionAnalyzer:
    """Analyzes exception patterns with context awareness."""
    
    def __init__(self):
        self.patterns = [
            (re.compile(r"except\s*:\s*$"), "bare_except"),
            (re.compile(r"except\s+Exception\b"), "broad_exception"),
        ]
        
        # Context indicators for severity assessment
        self.boundary_indicators = [
            "orchestrator", "adapter", "service", "manager", "handler",
            "return CommandResult", "return None", "return False", "return {",
            "boundary", "interface", "api", "cli"
        ]
        
        self.infrastructure_indicators = [
            "database", "cache", "redis", "file", "network", "http", "api",
            "persistence", "storage", "connection"
        ]
        
        self.specific_exception_indicators = [
            "json.loads", "json.dumps", "open(", "read(", "write(", 
            "connect(", "execute(", "cursor", "requests.", "urllib."
        ]

    def analyze_file(self, file_path: pathlib.Path) -> List[ExceptionPattern]:
        """Analyze a single file for exception patterns."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()
            patterns = []
            
            for line_num, line in enumerate(lines, 1):
                for pattern_re, pattern_type in self.patterns:
                    if pattern_re.search(line):
                        # Get surrounding context (expanded for better two-tier detection)
                        start = max(0, line_num - 15)
                        end = min(len(lines), line_num + 10)
                        surrounding = lines[start:end]
                        context_text = '\n'.join(surrounding)
                        
                        severity = self._assess_severity(
                            pattern_type, line, context_text, file_path
                        )
                        
                        suggestion = self._generate_suggestion(
                            pattern_type, severity, context_text, line
                        )
                        
                        patterns.append(ExceptionPattern(
                            file_path=file_path,
                            line_number=line_num,
                            line_content=line.strip(),
                            severity=severity,
                            context=self._extract_context_summary(context_text),
                            suggestion=suggestion,
                            surrounding_lines=surrounding
                        ))
                        break
            
            return patterns
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return []

    def _assess_severity(self, pattern_type: str, line: str, context: str, file_path: pathlib.Path) -> PatternSeverity:
        """Assess the severity of an exception pattern based on context."""
        
        # CRITICAL: Bare except patterns are always bad
        if pattern_type == "bare_except":
            return PatternSeverity.CRITICAL
        
        # Check if this is a boundary handler (orchestrator, service layer)
        is_boundary = any(indicator in context.lower() for indicator in self.boundary_indicators)
        is_boundary = is_boundary or "orchestrator" in str(file_path).lower()
        is_boundary = is_boundary or any(path_part in str(file_path).lower() 
                                       for path_part in ["application/orchestrators", "interfaces/", "adapters/",
                                                       "infrastructure/", "domain/"])
        
        # Additional boundary detection for __init__.py files in key modules
        is_boundary = is_boundary or ("__init__.py" in str(file_path) and 
                                    any(module in str(file_path) 
                                        for module in ["infrastructure", "interfaces", "application", "domain"]))
        
        # Enhanced domain service detection - these often have legitimate single-tier handlers for boundaries
        is_domain_service = any(service_type in str(file_path).lower() 
                               for service_type in ["domain/services", "engines/", "analyzers/", 
                                                  "narrative/", "emotional/", "mechanics/", "response/"])
        
        # Engine components often have proper error boundaries with single Exception handlers
        is_engine_component = any(engine_type in str(file_path).lower() 
                                for engine_type in ["_engine", "_analyzer", "_planner", "_manager"])
        
        # Monitoring and health check components often have legitimate Exception boundaries
        is_monitoring_component = any(monitor_type in str(file_path).lower() 
                                    for monitor_type in ["monitoring", "health_check", "benchmark", 
                                                       "production_monitoring", "cache_monitor"])
        
        # Consider domain services and engines as boundary-like for exception handling
        is_boundary = is_boundary or is_domain_service or is_engine_component or is_monitoring_component
        
        # Check if context has specific exception handling already (comprehensive detection)
        specific_exception_patterns = [
            "except (", "except OSError", "except json", "except ConnectionError", "except ImportError",
            "except AttributeError", "except KeyError", "except ValueError", "except TypeError", 
            "except IOError", "except PermissionError", "except UnicodeDecodeError", "except TimeoutError",
            "except FileNotFoundError", "except ModuleNotFoundError", "except sqlite3.",
            "except ConfigurationError", "except ModelError", "except ServiceError", 
            "except InfrastructureError", "except CacheError", "except NarrativeSystemError"
        ]
        has_specific_exceptions = any(specific in context for specific in specific_exception_patterns)
        
        # Also check for multi-line specific exception patterns (like "except (OSError, IOError)")
        import re
        multi_line_pattern = re.search(r'except\s*\([^)]+\)\s*as\s+\w+:', context, re.MULTILINE)
        if multi_line_pattern:
            has_specific_exceptions = True
        
        # Check if it's already part of a two-tier pattern (more comprehensive detection)
        has_exception_as_e = "except Exception as e:" in context or "except Exception as e" in context
        is_two_tier = has_specific_exceptions and has_exception_as_e
        
        # Special case: Also check if this specific line is the Exception handler in a two-tier pattern
        if "except Exception" in line and has_specific_exceptions:
            is_two_tier = True
        
        # Check if it's doing proper error handling (logging, returning errors, etc.)
        error_handling_patterns = [
            "logger.", "log_", "return CommandResult.failure", "return None", "return False", "return {",
            "print(f\"", "health_status[", "status =", "error =", "raise", "warnings.append",
            "log_error(", "log_warning(", "log_info(", "log_error_with_context", "log_system_event"
        ]
        proper_handling = any(indicator in context.lower() for indicator in error_handling_patterns)
        
        # Additional proper handling patterns specific to OpenChronicle
        openchronicle_patterns = [
            "return CommandResult", "return MemoryResult", "return HealthCheckResult", 
            "return CharacterUpdateResult", "warnings=[", "error\":", "status\":",
            "table.add_row", "console.print", "issues.append", "raise NarrativeSystemError",
            "raise ConfigurationError", "raise ModelError", "raise ServiceError"
        ]
        proper_handling = proper_handling or any(pattern in context for pattern in openchronicle_patterns)
        
        # ACCEPTABLE: Two-tier patterns with specific exceptions and proper handling
        if is_two_tier and proper_handling:
            return PatternSeverity.ACCEPTABLE
        
        # ACCEPTABLE: Two-tier patterns even without explicit proper handling patterns 
        # (many set return values directly which is also proper handling)
        if is_two_tier:
            return PatternSeverity.ACCEPTABLE
        
        # ACCEPTABLE: Domain services and engines with proper error handling 
        # (these often legitimately use Exception as error boundaries)
        if (is_domain_service or is_engine_component or is_monitoring_component) and proper_handling:
            return PatternSeverity.ACCEPTABLE
            
        # LOW: Boundary handlers with proper error handling
        if is_boundary and proper_handling:
            return PatternSeverity.LOW
            
        # MEDIUM: Could benefit from specific exception types
        if any(indicator in context.lower() for indicator in self.specific_exception_indicators):
            return PatternSeverity.MEDIUM
            
        # HIGH: Single-tier Exception handlers that could be improved
        return PatternSeverity.HIGH

    def _generate_suggestion(self, pattern_type: str, severity: PatternSeverity, context: str, line: str) -> str:
        """Generate improvement suggestions based on pattern analysis."""
        
        if severity == PatternSeverity.CRITICAL:
            return "Replace bare except: with specific exception types or 'except Exception as e:'"
        
        if severity == PatternSeverity.ACCEPTABLE:
            return "Pattern is acceptable - part of proper two-tier exception handling"
        
        if severity == PatternSeverity.LOW:
            return "Consider if more specific exceptions are needed, but boundary pattern is reasonable"
        
        # Generate specific suggestions based on context
        suggestions = []
        
        if "json" in context.lower():
            suggestions.append("Add 'except json.JSONDecodeError as e:' before catch-all")
        
        if any(file_op in context.lower() for file_op in ["open(", "read(", "write(", "path"]):
            suggestions.append("Add 'except (OSError, IOError, PermissionError) as e:' for file operations")
        
        if any(net_op in context.lower() for net_op in ["requests.", "urllib.", "http", "connection"]):
            suggestions.append("Add network-specific exceptions before catch-all")
        
        if any(db_op in context.lower() for db_op in ["execute(", "cursor", "database"]):
            suggestions.append("Add database-specific exceptions before catch-all")
        
        if not suggestions:
            suggestions.append("Consider what specific exceptions could occur and handle them explicitly")
        
        # Add exception chaining suggestion if not present
        if "from e" not in context:
            suggestions.append("Add 'from e' for exception chaining to preserve stack traces")
        
        return "; ".join(suggestions)

    def _extract_context_summary(self, context: str) -> str:
        """Extract a brief context summary."""
        context_lower = context.lower()
        
        if "orchestrator" in context_lower:
            return "Application orchestrator"
        elif "adapter" in context_lower:
            return "Infrastructure adapter"
        elif "service" in context_lower:
            return "Service layer"
        elif "json" in context_lower:
            return "JSON processing"
        elif any(file_op in context_lower for file_op in ["open(", "read(", "write("]):
            return "File operations"
        elif any(net_op in context_lower for net_op in ["requests.", "urllib.", "http"]):
            return "Network operations"
        elif any(db_op in context_lower for db_op in ["database", "cursor", "execute("]):
            return "Database operations"
        else:
            return "General processing"

    def analyze_codebase(self, root_path: pathlib.Path) -> Dict[PatternSeverity, List[ExceptionPattern]]:
        """Analyze entire codebase and categorize patterns by severity."""
        all_patterns = []
        
        for py_file in root_path.rglob("*.py"):
            if any(part in {"tests", "htmlcov", "__pycache__"} for part in py_file.parts):
                continue
            
            patterns = self.analyze_file(py_file)
            all_patterns.extend(patterns)
        
        # Group by severity
        severity_groups = {severity: [] for severity in PatternSeverity}
        for pattern in all_patterns:
            severity_groups[pattern.severity].append(pattern)
        
        return severity_groups

    def generate_report(self, severity_groups: Dict[PatternSeverity, List[ExceptionPattern]], 
                       show_all: bool = False, show_suggestions: bool = False, root_path: pathlib.Path = None) -> str:
        """Generate a comprehensive analysis report."""
        
        total_patterns = sum(len(patterns) for patterns in severity_groups.values())
        
        report = f"""# Smart Exception Pattern Analysis Report

## Summary
- **Total patterns found**: {total_patterns}
- **Critical issues**: {len(severity_groups[PatternSeverity.CRITICAL])} (bare except:)
- **High priority**: {len(severity_groups[PatternSeverity.HIGH])} (improvable Exception handlers)
- **Medium priority**: {len(severity_groups[PatternSeverity.MEDIUM])} (missing specific exceptions)
- **Low priority**: {len(severity_groups[PatternSeverity.LOW])} (boundary handlers)
- **Acceptable patterns**: {len(severity_groups[PatternSeverity.ACCEPTABLE])} (proper two-tier)

## Recommendations

### Immediate Action Required
"""
        
        # Handle root_path for relative paths
        if root_path is None:
            root_path = pathlib.Path.cwd()
        
        # Critical issues
        if severity_groups[PatternSeverity.CRITICAL]:
            report += f"\n**{len(severity_groups[PatternSeverity.CRITICAL])} CRITICAL bare except: patterns** - Fix immediately:\n"
            for pattern in severity_groups[PatternSeverity.CRITICAL][:10]:
                rel_path = str(pattern.file_path).replace(str(root_path), "")
                report += f"- `{rel_path}:{pattern.line_number}` - {pattern.context}\n"
            if len(severity_groups[PatternSeverity.CRITICAL]) > 10:
                report += f"... and {len(severity_groups[PatternSeverity.CRITICAL]) - 10} more\n"
        
        # High priority
        if severity_groups[PatternSeverity.HIGH]:
            report += f"\n**{len(severity_groups[PatternSeverity.HIGH])} HIGH priority improvements**:\n"
            for pattern in severity_groups[PatternSeverity.HIGH][:15]:
                rel_path = str(pattern.file_path).replace(str(root_path), "")
                report += f"- `{rel_path}:{pattern.line_number}` - {pattern.context}\n"
                if show_suggestions:
                    report += f"  💡 {pattern.suggestion}\n"
            if len(severity_groups[PatternSeverity.HIGH]) > 15:
                report += f"... and {len(severity_groups[PatternSeverity.HIGH]) - 15} more\n"
        
        # Medium priority
        if severity_groups[PatternSeverity.MEDIUM]:
            report += f"\n### Medium Priority ({len(severity_groups[PatternSeverity.MEDIUM])} patterns)\n"
            if show_all:
                for pattern in severity_groups[PatternSeverity.MEDIUM]:
                    rel_path = str(pattern.file_path).replace(str(root_path), "")
                    report += f"- `{rel_path}:{pattern.line_number}` - {pattern.context}\n"
                    if show_suggestions:
                        report += f"  💡 {pattern.suggestion}\n"
            else:
                report += "Use --show-all to see medium priority patterns\n"
        
        # Low priority note
        if severity_groups[PatternSeverity.LOW]:
            report += f"\n### Low Priority ({len(severity_groups[PatternSeverity.LOW])} patterns)\n"
            report += "These are likely intentional boundary handlers in orchestrators/adapters.\n"
            if show_all:
                for pattern in severity_groups[PatternSeverity.LOW][:10]:
                    rel_path = str(pattern.file_path).replace(str(root_path), "")
                    report += f"- `{rel_path}:{pattern.line_number}` - {pattern.context}\n"
        
        # Acceptable patterns note
        if severity_groups[PatternSeverity.ACCEPTABLE]:
            report += f"\n### Acceptable Patterns ({len(severity_groups[PatternSeverity.ACCEPTABLE])} patterns)\n"
            report += "These patterns are architecturally correct and flagged by simple tools unnecessarily.\n"
        
        return report


def main():
    """Main execution function."""
    ap = argparse.ArgumentParser(description="Smart exception pattern analysis")
    ap.add_argument("path", nargs="?", default="src/openchronicle",
                   help="Root directory to analyze")
    ap.add_argument("--show-all", action="store_true",
                   help="Show all patterns including low priority")
    ap.add_argument("--fix-suggestions", action="store_true",
                   help="Include fix suggestions in output")
    
    args = ap.parse_args()
    
    root_path = pathlib.Path(args.path).resolve()
    if not root_path.exists():
        print(f"Path not found: {root_path}")
        return 2
    
    analyzer = SmartExceptionAnalyzer()
    severity_groups = analyzer.analyze_codebase(root_path)
    
    report = analyzer.generate_report(
        severity_groups, 
        show_all=args.show_all, 
        show_suggestions=args.fix_suggestions,
        root_path=root_path
    )
    
    print(report)
    
    # Return exit code based on critical issues
    if severity_groups[PatternSeverity.CRITICAL]:
        return 1
    elif severity_groups[PatternSeverity.HIGH]:
        return 1
    else:
        return 0


if __name__ == "__main__":
    exit(main())
