#!/bin/bash
# 🎯 OpenChronicle Architecture Guard - Hexagonal Boundaries
# Enforces clean layer separation in hexagonal architecture

echo "🔍 Checking hexagonal architecture compliance..."

# Domain layer should not import from application/infrastructure
DOMAIN_VIOLATIONS=$(grep -r "from src.openchronicle.application\|from src.openchronicle.infrastructure" src/openchronicle/domain/ 2>/dev/null || true)

if [ ! -z "$DOMAIN_VIOLATIONS" ]; then
    echo "❌ DOMAIN LAYER VIOLATION: Domain importing from outer layers!"
    echo "Hexagonal architecture requires domain independence:"
    echo "$DOMAIN_VIOLATIONS"
    echo ""
    echo "🏛️ Architecture layers (inside → outside):"
    echo "  domain/ → application/ → infrastructure/ → interfaces/"
    echo "  Inner layers must NOT import from outer layers"
    exit 1
else
    echo "✅ Domain layer boundaries respected - hexagonal architecture maintained!"
fi
