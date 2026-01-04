# V1 Reference Snapshot

This folder contains the complete OpenChronicle v1 codebase, including source, docs, tests, and tooling, preserved as a frozen reference. Nothing in `v1.reference/` is used by the new v2 core and it should remain read-only.

What was moved:

- Core source, docs, tests, configs, and tooling were relocated here to keep history accessible without impacting the new architecture.

Purpose:

- Serve as a reference when re-implementing ideas in v2.
- Preserve historical behavior and documentation.

Replacement:

- The new orchestration core lives under `src/openchronicle_core/` with plugins under `plugins/`.
