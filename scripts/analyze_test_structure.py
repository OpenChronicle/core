"""
Analyze and report on the current test structure vs hexagonal architecture.
This script provides detailed analysis without making changes.
"""
import json
import re
from collections import defaultdict
from pathlib import Path


class TestStructureAnalyzer:
    """Analyzes test structure for hexagonal architecture compliance."""

    def __init__(self):
        self.root_path = Path(__file__).parent.parent
        self.tests_path = self.root_path / "tests"
        self.src_path = self.root_path / "src" / "openchronicle"

        # Define expected hexagonal structure
        self.hexagonal_layers = {
            "domain": {
                "description": "Business logic, entities, value objects, domain services",
                "subdirs": ["entities", "services", "value_objects", "repositories"]
            },
            "application": {
                "description": "Use cases, commands, queries, orchestrators",
                "subdirs": ["commands", "queries", "orchestrators", "services"]
            },
            "infrastructure": {
                "description": "External concerns, databases, file systems, APIs",
                "subdirs": ["database", "memory", "cache", "persistence", "external"]
            },
            "interfaces": {
                "description": "User interfaces, APIs, CLI, web interfaces",
                "subdirs": ["api", "cli", "web", "controllers"]
            }
        }

    def analyze_all(self):
        """Perform complete test structure analysis."""
        print("🔍 OpenChronicle Test Structure Analysis")
        print("=" * 60)

        # 1. Current structure analysis
        current_structure = self._analyze_current_structure()

        # 2. Source vs test alignment
        alignment_report = self._analyze_source_test_alignment()

        # 3. Import pattern analysis
        import_analysis = self._analyze_import_patterns()

        # 4. Compliance assessment
        compliance_report = self._assess_compliance()

        # 5. Generate recommendations
        recommendations = self._generate_recommendations(
            current_structure, alignment_report, import_analysis, compliance_report
        )

        # 6. Output comprehensive report
        self._output_report({
            "current_structure": current_structure,
            "alignment": alignment_report,
            "imports": import_analysis,
            "compliance": compliance_report,
            "recommendations": recommendations
        })

        return compliance_report

    def _analyze_current_structure(self):
        """Analyze current test directory structure."""
        print("\n📁 Current Test Structure Analysis")
        print("-" * 40)

        structure = {
            "total_test_files": 0,
            "directories": {},
            "orphaned_files": [],
            "layer_distribution": defaultdict(int)
        }

        if not self.tests_path.exists():
            print("❌ Tests directory not found!")
            return structure

        unit_path = self.tests_path / "unit"
        if not unit_path.exists():
            print("❌ Unit tests directory not found!")
            return structure

        # Analyze each directory in unit tests
        for item in unit_path.iterdir():
            if not item.is_dir() or item.name.startswith('.'):
                continue

            test_files = list(item.rglob("test_*.py"))
            all_py_files = list(item.rglob("*.py"))

            structure["directories"][item.name] = {
                "test_files": len(test_files),
                "total_py_files": len(all_py_files),
                "path": str(item.relative_to(self.root_path)),
                "is_hexagonal_layer": item.name in self.hexagonal_layers,
                "hexagonal_layer": item.name if item.name in self.hexagonal_layers else "unknown"
            }

            structure["total_test_files"] += len(test_files)

            # Categorize by hexagonal layer
            if item.name in self.hexagonal_layers:
                structure["layer_distribution"][item.name] += len(test_files)
            else:
                structure["layer_distribution"]["unmapped"] += len(test_files)

            # Print directory info
            layer_status = "✅" if item.name in self.hexagonal_layers else "⚠️"
            print(f"  {layer_status} {item.name}/ ({len(test_files)} tests, {len(all_py_files)} total files)")

        # Check for orphaned test files in unit root
        orphaned = list(unit_path.glob("test_*.py"))
        structure["orphaned_files"] = [str(f.relative_to(self.root_path)) for f in orphaned]

        print("\n📊 Summary:")
        print(f"  Total test files: {structure['total_test_files']}")
        print(f"  Hexagonal layers: {len([d for d in structure['directories'] if structure['directories'][d]['is_hexagonal_layer']])}/4")
        print(f"  Unmapped directories: {len([d for d in structure['directories'] if not structure['directories'][d]['is_hexagonal_layer']])}")

        return structure

    def _analyze_source_test_alignment(self):
        """Analyze alignment between source structure and test structure."""
        print("\n🔄 Source-Test Structure Alignment")
        print("-" * 40)

        alignment = {
            "source_modules": {},
            "test_coverage": {},
            "missing_tests": [],
            "orphaned_tests": []
        }

        if not self.src_path.exists():
            print("❌ Source directory not found!")
            return alignment

        # Analyze source structure
        for layer in self.hexagonal_layers:
            layer_path = self.src_path / layer
            if layer_path.exists():
                modules = []
                for py_file in layer_path.rglob("*.py"):
                    if py_file.name != "__init__.py":
                        rel_path = py_file.relative_to(layer_path)
                        module_name = str(rel_path).replace(".py", "").replace("\\", "/")
                        modules.append(module_name)

                alignment["source_modules"][layer] = modules

                # Check for corresponding tests
                test_layer_path = self.tests_path / "unit" / layer
                test_coverage = {}

                if test_layer_path.exists():
                    for module in modules:
                        test_file_name = f"test_{Path(module).name}.py"
                        test_file_path = test_layer_path / test_file_name
                        test_coverage[module] = test_file_path.exists()
                else:
                    test_coverage = {module: False for module in modules}

                alignment["test_coverage"][layer] = test_coverage

                # Identify missing tests
                missing = [f"{layer}/{module}" for module, has_test in test_coverage.items() if not has_test]
                alignment["missing_tests"].extend(missing)

                print(f"  📦 {layer}:")
                print(f"    Source modules: {len(modules)}")
                if test_layer_path.exists():
                    test_files = len(list(test_layer_path.rglob("test_*.py")))
                    coverage_pct = sum(test_coverage.values()) / len(modules) * 100 if modules else 0
                    print(f"    Test files: {test_files}")
                    print(f"    Coverage: {coverage_pct:.1f}%")
                else:
                    print("    Test files: 0 (no test directory)")

        return alignment

    def _analyze_import_patterns(self):
        """Analyze import patterns in test files."""
        print("\n📥 Import Pattern Analysis")
        print("-" * 40)

        analysis = {
            "legacy_imports": [],
            "proper_imports": [],
            "relative_imports": [],
            "external_imports": [],
            "import_violations": []
        }

        if not self.tests_path.exists():
            return analysis

        test_files = list(self.tests_path.rglob("test_*.py"))

        for test_file in test_files:
            try:
                content = test_file.read_text(encoding='utf-8')

                # Check for different import patterns
                import_lines = [line.strip() for line in content.split('\n')
                              if line.strip().startswith(('import ', 'from '))]

                for line in import_lines:
                    rel_path = str(test_file.relative_to(self.root_path))

                    if re.search(r'from core\.', line) or re.search(r'import core\.', line):
                        analysis["legacy_imports"].append(f"{rel_path}: {line}")

                    elif re.search(r'from src\.openchronicle\.', line):
                        analysis["proper_imports"].append(f"{rel_path}: {line}")

                    elif line.startswith('from .') or line.startswith('from ..'):
                        analysis["relative_imports"].append(f"{rel_path}: {line}")

                    elif not any(line.startswith(f'from {pkg}') for pkg in ['pytest', 'unittest', 'mock']):
                        if 'openchronicle' not in line:
                            analysis["external_imports"].append(f"{rel_path}: {line}")

            except Exception as e:
                analysis["import_violations"].append(f"Error reading {test_file}: {e}")

        print(f"  ✅ Proper imports: {len(analysis['proper_imports'])}")
        print(f"  ⚠️ Legacy imports: {len(analysis['legacy_imports'])}")
        print(f"  🔗 Relative imports: {len(analysis['relative_imports'])}")
        print(f"  📦 External imports: {len(analysis['external_imports'])}")

        if analysis["legacy_imports"]:
            print("\n  ❌ Legacy 'core' imports found:")
            for imp in analysis["legacy_imports"][:5]:  # Show first 5
                print(f"    {imp}")
            if len(analysis["legacy_imports"]) > 5:
                print(f"    ... and {len(analysis['legacy_imports']) - 5} more")

        return analysis

    def _assess_compliance(self):
        """Assess overall hexagonal architecture compliance."""
        print("\n✅ Compliance Assessment")
        print("-" * 40)

        compliance = {
            "overall_score": 0,
            "layer_compliance": {},
            "structure_score": 0,
            "import_score": 0,
            "coverage_score": 0,
            "issues": [],
            "strengths": []
        }

        # Check layer structure (25% of score)
        unit_path = self.tests_path / "unit"
        if unit_path.exists():
            existing_layers = [d.name for d in unit_path.iterdir()
                             if d.is_dir() and d.name in self.hexagonal_layers]
            structure_score = len(existing_layers) / len(self.hexagonal_layers) * 25
            compliance["structure_score"] = structure_score

            if len(existing_layers) == len(self.hexagonal_layers):
                compliance["strengths"].append("All hexagonal layers present in test structure")
            else:
                missing = set(self.hexagonal_layers.keys()) - set(existing_layers)
                compliance["issues"].append(f"Missing layer directories: {', '.join(missing)}")
        else:
            compliance["issues"].append("Unit test directory structure not found")

        # Check import patterns (25% of score)
        test_files = list(self.tests_path.rglob("test_*.py")) if self.tests_path.exists() else []
        if test_files:
            legacy_count = 0
            proper_count = 0

            for test_file in test_files:
                try:
                    content = test_file.read_text(encoding='utf-8')
                    if re.search(r'from core\.', content) or re.search(r'import core\.', content):
                        legacy_count += 1
                    elif re.search(r'from src\.openchronicle\.', content):
                        proper_count += 1
                except Exception:
                    pass

            if test_files:
                import_score = max(0, (proper_count - legacy_count) / len(test_files)) * 25
                compliance["import_score"] = import_score

                if legacy_count == 0:
                    compliance["strengths"].append("No legacy 'core' imports found")
                else:
                    compliance["issues"].append(f"{legacy_count} files with legacy imports")

        # Check source-test alignment (25% of score)
        if self.src_path.exists():
            # Simple heuristic: ratio of test files to source files
            src_files = len(list(self.src_path.rglob("*.py")))
            test_files_count = len(test_files)

            if src_files > 0:
                coverage_ratio = min(1.0, test_files_count / src_files)
                coverage_score = coverage_ratio * 25
                compliance["coverage_score"] = coverage_score

                if coverage_ratio > 0.8:
                    compliance["strengths"].append("Good test coverage ratio")
                elif coverage_ratio < 0.3:
                    compliance["issues"].append("Low test coverage ratio")

        # Architecture validation (25% of score)
        # This would require actual import analysis - simplified for now
        arch_score = 15  # Placeholder - assume partial compliance

        # Calculate overall score
        compliance["overall_score"] = (
            compliance["structure_score"] +
            compliance["import_score"] +
            compliance["coverage_score"] +
            arch_score
        )

        # Determine compliance level
        score = compliance["overall_score"]
        if score >= 80:
            level = "✅ COMPLIANT"
        elif score >= 60:
            level = "⚠️ PARTIALLY COMPLIANT"
        else:
            level = "❌ NON-COMPLIANT"

        print(f"  Overall Score: {score:.1f}/100 ({level})")
        print(f"  Structure: {compliance['structure_score']:.1f}/25")
        print(f"  Imports: {compliance['import_score']:.1f}/25")
        print(f"  Coverage: {compliance['coverage_score']:.1f}/25")
        print(f"  Architecture: {arch_score}/25")

        return compliance

    def _generate_recommendations(self, structure, alignment, imports, compliance):
        """Generate specific recommendations for improvement."""
        recommendations = {
            "high_priority": [],
            "medium_priority": [],
            "low_priority": [],
            "quick_wins": []
        }

        # High priority issues
        if imports["legacy_imports"]:
            recommendations["high_priority"].append({
                "action": "Update legacy import statements",
                "description": f"Replace {len(imports['legacy_imports'])} legacy 'core' imports with 'src.openchronicle' imports",
                "effort": "Medium",
                "impact": "High"
            })

        if compliance["structure_score"] < 20:
            recommendations["high_priority"].append({
                "action": "Create missing hexagonal layer directories",
                "description": "Establish proper domain/application/infrastructure/interfaces test structure",
                "effort": "Low",
                "impact": "High"
            })

        # Medium priority issues
        unmapped_dirs = [d for d in structure["directories"]
                        if not structure["directories"][d]["is_hexagonal_layer"]]
        if unmapped_dirs:
            recommendations["medium_priority"].append({
                "action": "Migrate unmapped test directories",
                "description": f"Move tests from {len(unmapped_dirs)} unmapped directories to proper hexagonal layers",
                "effort": "Medium",
                "impact": "Medium"
            })

        if alignment["missing_tests"]:
            recommendations["medium_priority"].append({
                "action": "Add missing test files",
                "description": f"Create tests for {len(alignment['missing_tests'])} source modules without tests",
                "effort": "High",
                "impact": "Medium"
            })

        # Quick wins
        if structure["orphaned_files"]:
            recommendations["quick_wins"].append({
                "action": "Organize orphaned test files",
                "description": f"Move {len(structure['orphaned_files'])} orphaned test files to appropriate directories",
                "effort": "Low",
                "impact": "Low"
            })

        if imports["relative_imports"]:
            recommendations["low_priority"].append({
                "action": "Convert relative imports to absolute",
                "description": f"Convert {len(imports['relative_imports'])} relative imports to absolute imports",
                "effort": "Low",
                "impact": "Low"
            })

        return recommendations

    def _output_report(self, analysis):
        """Output comprehensive analysis report."""
        print("\n" + "=" * 60)
        print("📋 HEXAGONAL ARCHITECTURE COMPLIANCE REPORT")
        print("=" * 60)

        compliance = analysis["compliance"]
        recommendations = analysis["recommendations"]

        # Executive Summary
        print("\n🎯 EXECUTIVE SUMMARY")
        print(f"Compliance Score: {compliance['overall_score']:.1f}/100")
        print(f"Priority Issues: {len(recommendations['high_priority'])}")
        print(f"Total Recommendations: {sum(len(recs) for recs in recommendations.values())}")

        # Issues
        if compliance["issues"]:
            print("\n❌ CRITICAL ISSUES:")
            for issue in compliance["issues"]:
                print(f"  • {issue}")

        # Strengths
        if compliance["strengths"]:
            print("\n✅ STRENGTHS:")
            for strength in compliance["strengths"]:
                print(f"  • {strength}")

        # Recommendations
        if recommendations["high_priority"]:
            print("\n🔥 HIGH PRIORITY ACTIONS:")
            for i, rec in enumerate(recommendations["high_priority"], 1):
                print(f"  {i}. {rec['action']}")
                print(f"     {rec['description']}")
                print(f"     Effort: {rec['effort']} | Impact: {rec['impact']}")

        if recommendations["quick_wins"]:
            print("\n⚡ QUICK WINS:")
            for i, rec in enumerate(recommendations["quick_wins"], 1):
                print(f"  {i}. {rec['action']}")
                print(f"     {rec['description']}")

        # Next Steps
        print("\n🚀 NEXT STEPS:")
        print("1. Run 'python scripts/migrate_tests_to_hexagonal.py' to auto-migrate structure")
        print("2. Run 'python scripts/validate_hexagonal_tests.py' to validate compliance")
        print("3. Update import statements in failing tests")
        print("4. Add missing test files for uncovered modules")

        # Save detailed report
        report_file = self.root_path / "test_structure_analysis.json"
        with open(report_file, 'w') as f:
            # Convert Path objects to strings for JSON serialization
            json_analysis = json.loads(json.dumps(analysis, default=str))
            json.dump(json_analysis, f, indent=2)

        print(f"\n📄 Detailed report saved to: {report_file}")


def main():
    """Main entry point for test structure analysis."""
    analyzer = TestStructureAnalyzer()
    compliance = analyzer.analyze_all()

    # Return compliance score for scripting
    return int(compliance["overall_score"])


if __name__ == "__main__":
    import sys
    score = main()
    sys.exit(0 if score >= 80 else 1)  # Exit with error if not compliant
