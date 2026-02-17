# OpenChronicle v2 - Feature & Implementation Backlog

This document tracks planned features, implementation gaps, and future work for the OpenChronicle v2 project.

**Last Updated:** 2026-02-04

---

## Status Legend

| Symbol | Meaning             |
| ------ | ------------------- |
| ✅     | Implemented         |
| 🟡     | In Progress         |
| 🔴     | Not Started         |
| ⚪     | Stubbed/Placeholder |
| ⏸️     | Deferred            |

---

## Priority 0 — Foundation (Blocking)

### 0.1 Scheduler Service (Core)

**Status:** ✅ Implemented
**Effort:** Medium
**Rationale:** Enables scheduled responses, periodic scans, metrics snapshots. Unlocks downstream features (Discord, security scanner, dev agent runner). Built as a core service in `application/services/` per Decision #4 (hybrid taxonomy).

**Requirements:**

- [x] Job store (core SQLite — `scheduled_jobs` table, 16 columns, 2 indexes)
- [x] One-shot scheduled tasks (auto-complete after fire)
- [x] Recurring jobs (interval-based, `cron_expr` column reserved for v1)
- [x] Deterministic execution order (`next_due_at ASC`, `created_at ASC`, `id ASC`)
- [x] `scheduler.tick(now, max_jobs)` — atomic claim via `BEGIN IMMEDIATE`, drift prevention
- [x] `scheduler.serve()` — async polling loop with clean shutdown
- [x] Job lifecycle: active/paused/completed/cancelled with state transition validation
- [x] CLI: `oc scheduler {add|list|pause|resume|cancel|tick}`
- [x] RPC: `scheduler.{add|list|pause|resume|cancel|tick}` (6 handlers)
- [x] Events: `scheduler.job_created/paused/resumed/cancelled/fired/tick_completed`

**Acceptance Criteria:**

- [x] Jobs persist across restarts (SQLite)
- [x] Deterministic ordering verified by tests
- [x] No double-fire under concurrent tick() (concurrency stress test T6)
- [x] 52+ tests (28 service, 13 storage, 11 CLI)

---

## Priority 1 — Client Integrations

### 1.1 Discord Interface (Core Driver)

**Status:** ✅ Implemented
**Location:** `src/openchronicle/interfaces/discord/` (optional `[discord]` extra)
**Tests:** 60 unit tests (`test_discord_*.py`) + 7 integration tests

Implemented as a core interfaces driver per Decision #4 (hybrid taxonomy).
The driver interacts with core directly via the container (same process), not
via STDIO RPC. Core remains fully functional without Discord installed — the
`discord.py` package is an optional extra, all discord imports are lazy and
confined to `interfaces/discord/` and `interfaces/cli/commands/discord.py`.

**Implemented:**

- [x] Discord bot receiving messages (`commands.Bot` subclass)
- [x] 6 slash commands: `/newconvo`, `/remember`, `/forget`, `/explain`, `/mode`, `/history`
- [x] Session-to-conversation mapping (file-backed, multi-user)
- [x] Message splitting for Discord's 2000-char limit
- [x] Privacy gate and interaction routing honored
- [x] Config from `core.json` + env vars (three-layer precedence)
- [x] `oc discord start` CLI command with lazy import guard

**Architectural posture (enforced by tests):**

- Core must remain fully functional without Discord (`test_architectural_posture.py`)
- No `core.*` module imports discord (`test_hexagonal_boundaries.py`)
- Multi-session isolation: no module-level mutable state (`test_architectural_posture.py`)

---

## Priority 2 — Safety & Security

### 2.1 Dev Folder Security Scanner Plugin

**Status:** 🔴 Not Started
**Effort:** Medium
**Depends On:** Scheduler Service (core)

**Requirements:**

- [ ] Integrate existing scanners (not inventing new ones):
  - [ ] Secrets scanning: gitleaks or trufflehog
  - [ ] Dependency vulnerability: osv-scanner
  - [ ] Container scanning: trivy (optional)
  - [ ] Static analysis: semgrep rules (optional)
- [ ] Deterministic scan runs with stable tool versions
- [ ] Reports stored in output directory with timestamps + "latest" pointer
- [ ] Alert channels: CLI/RPC retrieval
- [ ] Optional Discord alerts (if Discord interface configured)

**Acceptance Criteria:**

- Scans run on schedule via scheduler service
- Reports are JSON-serializable and timestamped
- No false positives in baseline scan of clean repo

---

## Priority 3 — Workflow Automation

### 3.1 Dev Agent Runner (Sandboxed)

**Status:** 🔴 Not Started
**Effort:** Large (3+ weeks)
**Depends On:** Scheduler, Security Scanner
**Risk:** High — requires careful security design

**Requirements:**

- [ ] Sandboxed execution environment (dedicated container image)
- [ ] Plan + constraints + workspace + tool permissions model
- [ ] Explicit mounts (read-only vs read-write)
- [ ] Network restrictions (no network by default)
- [ ] Complete audit logging (commands, files touched, outputs, errors)
- [ ] Outputs: patch/branch or artifact bundle (never direct upstream push)

**Security Baseline:**

- [ ] Default deny: network, secrets access, external repo push
- [ ] Explicit allow-lists for commands, directories
- [ ] Time/resource limits enforced
- [ ] Human review gate before any upstream push

### 3.2 Serena MCP Capabilities Integration

**Status:** ⏸️ Deferred
**Depends On:** Dev Agent Runner (stable)

**Approach:**

- Start with "compatibility mode": allow Serena-like flows only inside sandbox runner container
- Integrate only after sandbox runner is stable, network policy is explicit, scanning pipeline exists

---

## Priority 4 — Advanced LLM Features

### 4.1 Mixture-of-Experts Mode

**Status:** 🔴 Not Started (Optional)
**Effort:** Medium
**Priority:** Low — may not be required for core usefulness

**Requirements:**

- [ ] Run N experts (default 3)
- [ ] Select output via agreement rules
- [ ] Produce aggregator decision with explainability:
  - Which experts agreed
  - Conflict summary
  - Why final output was chosen
- [ ] Deterministic selection rules with stable tie-breakers

**Constraints:**

- Must be optional, not default UX
- Clear cost implications documented

---

## Priority 5 — IDE / Developer Platform Integrations

### 5.1 VS Code Copilot SDK Integration

**Status:** 🔴 Not Started
**Effort:** Medium
**Depends On:** Dev Agent Runner (recommended)

**Requirements:**

- [ ] Authenticate explicitly (user-managed)
- [ ] Submit request payload, return structured output + logs
- [ ] Explicit opt-in network policy with full audit logging
- [ ] Sanitize payloads / respect PII gate

### 5.2 Goose (Block) Integration (Plugin / External Agent Driver)

**Status:** 🔴 Not Started
**Effort:** Medium
**Depends On:** Scheduler, Security Scanner, Sandbox Runner baseline

**What it is:** Goose is an open-source, local, extensible AI agent aimed at automating engineering tasks end-to-end (CLI + desktop), with support for multi-model configuration and MCP server integrations.

**Why we care:** Goose overlaps directly with the "dev-agent runner" concept, and could accelerate our path to background development workflows by reusing an existing agent runtime rather than inventing one. It also gives us an integration target for MCP-style tool ecosystems.

**Integration posture (keep core hardcore):**

- **Plugin-only integration.** Core must not depend on Goose.
- Treat Goose as an **external worker/agent** that our plugins can orchestrate via:
  - CLI process execution (stdio)
  - explicit workspace mounts
  - explicit network policy (default deny)
  - deterministic job envelopes

**Minimum viable capability (MVP):**

- A plugin that can:
  1. Launch Goose with a controlled workspace (sandbox dir/container mount)
  2. Provide an input "plan" or task description
  3. Capture outputs deterministically:
     - logs
     - artifacts (patches/files)
     - structured status
  4. Emit an OpenChronicle task result with full explainability:
     - what Goose was asked to do
     - what workspace it had access to
     - whether network was allowed
     - what it produced

**Security guardrails (non-negotiable):**

- Default **no internet** unless explicitly enabled per run.
- Strict allowlists for:
  - writable paths
  - executable commands
  - maximum runtime/resources
- No pushing to external remotes.
- All outputs must pass through our scanning pipeline before being considered "trusted."

**Where it fits in the sequence:**

- After:
  1. Scheduler plugin MVP
  2. Security scanning plugin MVP
  3. Sandbox runner baseline (or equivalent)
- Then Goose becomes either:
  - a backend option for "Dev Agent Runner," or
  - a parallel integration target for "agent execution engines."

**Notes:**

- We should treat Goose as a _replaceable_ agent runtime. The integration should be a driver contract, not a Goose-specific assumption.

---

## Priority 6 — Platform Infrastructure

### 6.1 Private Git Server Integration

**Status:** 🔴 Not Started
**Effort:** Medium
**Depends On:** Dev Agent Runner

**Approach:**

- Self-hosted Git (Gitea/GitLab) behind network
- Clone/pull in sandbox, produce branches/patches
- Manual human review gate before any upstream push

---

## Infrastructure Gaps

### HTTP API

**Status:** ⚪ Stubbed
**File:** `src/openchronicle/interfaces/api/http_api.py`
**Effort:** Medium

**Requirements:**

- [ ] FastAPI or Flask wiring
- [ ] Authentication layer
- [ ] Streaming response support
- [ ] OpenAPI documentation
- [ ] Rate limiting middleware

### Output Directory Utilization

**Status:** ⚪ Reserved
**Env Var:** `OC_OUTPUT_DIR`

**Planned Uses:**

- [ ] Scheduler job outputs
- [ ] Security scanner reports
- [ ] Dev agent artifacts
- [ ] Export bundles

---

## Testing Gaps

### Performance Testing

**Status:** 🔴 Not Started

**Requirements:**

- [ ] Load testing for rate limiting / concurrency scenarios
- [ ] Performance regression testing suite
- [ ] Benchmark tracking over time

### Plugin Integration Testing

**Status:** 🟡 Partial

**Requirements:**

- [ ] Standardized plugin test harness
- [ ] Mock core for plugin unit tests
- [ ] Integration test templates

---

## Documentation Gaps

### Missing Documentation

- [ ] **Performance/Optimization Guide** — Scaling, caching strategies, perf tuning
- [ ] **Debugging Guide** — Troubleshooting procedures, common issues
- [ ] **Security Hardening Guide** — Production hardening beyond privacy gate
- [ ] **Contribution Guidelines** — CONTRIBUTING.md with PR process

---

## Technical Debt

### Known Issues

| Issue                               | Location                               | Priority |
| ----------------------------------- | -------------------------------------- | -------- |
| ~~Unicode encoding on Windows CLI~~ | `interfaces/cli/main.py`               | ✅ Fixed |
| ~~Test subprocess PATH issue~~      | `tests/test_task_submit_rpc.py`        | ✅ Fixed |
| ~~Docker acceptance JSON escaping~~ | `tools/docker/acceptance.ps1`          | ✅ Fixed |
| ~~docker-compose .env required~~    | `docker-compose.yml`                   | ✅ Fixed |
| ~~Smoke test assertion too strict~~ | `tests/integration/test_smoke_live.py` | ✅ Fixed |

### Code Quality Enforcement

All enforced via CI/tests:

- ✅ No tech debt marker comments (`test_no_soft_deprecation.py`)
- ✅ No secrets committed (`test_no_secrets_committed.py`)
- ✅ Strict mypy typing required
- ✅ Ruff formatting + linting required

---

## Implementation Sequence

Recommended order based on dependencies:

```text
1. Scheduler Service (P0) ✅
   └── Core service in application/services/

2. Discord Interface (P1) ✅
   └── Core driver in interfaces/discord/

3. Security Scanner Plugin (P2)
   └── Runs via scheduler service
   └── Safety rail for dev agent

4. HTTP API (Infrastructure)
   └── Web integrations
   └── External tool access

5. Dev Agent Runner (P3)
   └── Uses scheduler + scanner
   └── Sandboxed execution

6. Serena MCP Integration (P3.2)
   └── Inside sandbox runner only

7. VS Code Copilot SDK (P5.1)
   └── After sandbox exists

8. Goose Integration (P5.2)
   └── After scanner + sandbox baseline
   └── Replaceable agent runtime driver

9. Mixture-of-Experts (P4)
   └── Optional advanced feature

10. Private Git Server (P6)
    └── Platform infrastructure
```

---

## References

- **Architecture:** `docs/architecture/ARCHITECTURE.md`
- **Plugin Guide:** `docs/architecture/PLUGINS.md`
- **Plugin Roadmap:** `docs/plugins/plugin_backlog.md`
- **RPC Protocol:** `docs/protocol/stdio_rpc_v1.md`
- **Discord Contract:** `docs/integrations/discord_driver_contract.md`
- **Project Instructions:** `CLAUDE.md`
