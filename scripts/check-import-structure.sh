#!/bin/bash
# 📁 OpenChronicle Architecture Guard - Import Structure
# Validates import patterns for maintainability

echo "🔍 Validating import patterns..."

# Check for deep relative imports (prefer absolute)
DEEP_RELATIVES=$(grep -r "from \.\.\." src/ 2>/dev/null || true)

if [ ! -z "$DEEP_RELATIVES" ]; then
    echo "⚠️ WARNING: Deep relative imports detected (prefer absolute):"
    echo "$DEEP_RELATIVES"
    echo ""
    echo "💡 Consider converting to absolute imports:"
    echo "  from ...deep.path → from src.openchronicle.deep.path"
    echo ""
fi

# Count import patterns for metrics
ABSOLUTE_IMPORTS=$(grep -r "from src.openchronicle" src/ 2>/dev/null | wc -l || echo "0")
RELATIVE_IMPORTS=$(grep -r "from \." src/ 2>/dev/null | wc -l || echo "0")

echo "📊 Import pattern metrics:"
echo "  Absolute imports: $ABSOLUTE_IMPORTS"
echo "  Relative imports: $RELATIVE_IMPORTS"

echo "✅ Import structure validation complete"
