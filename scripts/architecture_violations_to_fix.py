"""
Fix Source Code Architecture Violations
Priority: HIGH - These violate hexagonal architecture principles
"""

# Domain Layer Violations (4 files) - CRITICAL
# Domain should only depend on other domain modules, never outer layers

VIOLATIONS_TO_FIX = {
    "domain_violations": [
        {
            "file": "src/openchronicle/domain/models/configuration_manager.py",
            "issue": "Imports from infrastructure layer",
            "action": "Move infrastructure dependencies to dependency injection or ports"
        },
        {
            "file": "src/openchronicle/domain/services/timeline/shared/fallback_navigation.py",
            "issue": "Imports from infrastructure layer",
            "action": "Use dependency injection or abstract interfaces"
        },
        {
            "file": "src/openchronicle/domain/services/timeline/shared/fallback_state.py",
            "issue": "Imports from infrastructure layer",
            "action": "Use dependency injection or abstract interfaces"
        },
        {
            "file": "src/openchronicle/domain/services/timeline/shared/fallback_timeline.py",
            "issue": "Imports from infrastructure layer",
            "action": "Use dependency injection or abstract interfaces"
        }
    ],

    "application_violations": [
        # 9 files in application/services/importers/storypack/* importing from interfaces
        {
            "pattern": "src/openchronicle/application/services/importers/storypack/**/*.py",
            "issue": "Relative imports to interfaces (from ..interfaces)",
            "action": "Use dependency injection or move interfaces to domain"
        }
    ],

    "infrastructure_violations": [
        {
            "file": "src/openchronicle/infrastructure/performance/analysis/bottleneck_analyzer.py",
            "issue": "Imports from interfaces layer",
            "action": "Use dependency injection"
        },
        {
            "file": "src/openchronicle/infrastructure/performance/metrics/collector.py",
            "issue": "Imports from interfaces layer",
            "action": "Use dependency injection"
        },
        {
            "file": "src/openchronicle/infrastructure/performance/metrics/storage.py",
            "issue": "Imports from interfaces layer",
            "action": "Use dependency injection"
        }
    ]
}

# Recommended fix approach:
# 1. Create abstract interfaces in domain/ports/
# 2. Implement concrete versions in infrastructure/
# 3. Use dependency injection to wire them together
# 4. Remove direct imports between layers
