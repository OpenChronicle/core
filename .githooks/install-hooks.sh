#!/usr/bin/env bash
# Installs all git hooks for openchronicle-core.
#
# - pre-commit: managed by the 'pre-commit' Python framework
# - post-commit: scrubbed zip export (from .githooks/post-commit)
#
# Usage: bash .githooks/install-hooks.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Installing hooks for openchronicle-core..."

# Install pre-commit framework hooks (if pre-commit is available)
if command -v pre-commit &>/dev/null; then
    echo "  Installing pre-commit hooks..."
    pre-commit install
else
    echo "  WARNING: 'pre-commit' not found. Install with: pip install pre-commit"
    echo "           Then run: pre-commit install"
fi

# Install post-commit hook
echo "  Installing post-commit hook..."
cp "$REPO_ROOT/.githooks/post-commit" "$REPO_ROOT/.git/hooks/post-commit"
chmod +x "$REPO_ROOT/.git/hooks/post-commit"

echo "Done. All hooks installed."
