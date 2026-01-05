# OpenChronicle Core v2 (clean slate)

This branch introduces a fresh orchestration core intended for a manager/supervisor/worker LLM system. The prior implementation now lives in `v1.reference/` as a frozen snapshot.

Key points:

- New source root: `src/openchronicle/`
- Plugins root: `plugins/`
- V1 snapshot: `v1.reference/` (read-only reference)

Use `oc --help` after installing in editable mode (`pip install -e .`) to explore the minimal CLI.
