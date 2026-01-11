## Budget Enforcement Implementation Summary

### Overview

Implemented crash-safe, deterministic budget enforcement for OpenChronicle v2 using event replay. The system prevents LLM execution when budget constraints are exceeded, with explicit event-based decision reporting.

### Architecture

#### 1. Domain Layer (`BudgetPolicy`)

**File**: [src/openchronicle/core/domain/models/budget_policy.py](src/openchronicle/core/domain/models/budget_policy.py)

Pure data model with two optional constraints:

- `max_total_tokens`: Maximum cumulative tokens across all LLM calls
- `max_llm_calls`: Maximum number of LLM execution attempts

No infrastructure dependencies; suitable for serialization.

#### 2. Replay-Derived Usage Tracking (`derive_usage`)

**File**: [src/openchronicle/core/application/replay/usage_derivation.py](src/openchronicle/core/application/replay/usage_derivation.py)

Derives current resource consumption deterministically from persisted events:

- Counts `llm.execution_recorded` events as authoritative execution records
- Extracts `total_tokens` from payloads; computes from `prompt_tokens + completion_tokens` if unavailable
- **Crash-safe**: Results depend only on event log; consistent across restarts

Returns `UsageSummary` with:

- `total_llm_calls`: Count of recorded executions
- `total_tokens`: Cumulative token consumption

#### 3. Budget Enforcement Gate (`BudgetGate`)

**File**: [src/openchronicle/core/application/policies/budget_gate.py](src/openchronicle/core/application/policies/budget_gate.py)

Application-level policy that enforces constraints before LLM execution:

**Method**: `check(project_id, policy, projected_tokens=None)`

Behavior:

1. Skips if policy has no constraints
2. Derives current usage from persisted events
3. If `total_llm_calls >= max_llm_calls`:
   - Emits `budget.blocked` event explaining reason
   - Raises `BudgetExceededError` (no silent downgrades)
4. If `total_tokens + projected_tokens > max_total_tokens`:
   - Emits `budget.blocked` event with all parameters
   - Raises `BudgetExceededError`

Event payload includes:

- `reason`: "max_llm_calls" or "max_total_tokens"
- `policy`: Full policy limits for explanation
- `current_usage`: Derived current consumption (calls + tokens)
- `projected_tokens`: Estimated tokens for attempted call

#### 4. LLM Execution Integration

**File**: [src/openchronicle/core/application/services/llm_execution.py](src/openchronicle/core/application/services/llm_execution.py)

Enhanced both LLM execution functions to support optional budget gating:

- `execute_with_route(...)` - Routing-anchored execution
- `execute_with_explicit_provider(...)` - Fallback/retry execution

New optional parameters:

- `budget_gate`: BudgetGate instance
- `project_id`: Project identifier for budget check
- `budget_policy`: Policy to enforce

Both functions call `budget_gate.check()` before attempting LLM calls when all three parameters provided.

#### 5. CLI Configuration Support

**File**: [src/openchronicle/core/infrastructure/config/budget_config.py](src/openchronicle/core/infrastructure/config/budget_config.py)

Function `load_budget_policy()` reads environment variables:

- `OC_BUDGET_MAX_TOKENS`: Maximum total tokens (optional, int)
- `OC_BUDGET_MAX_CALLS`: Maximum LLM calls (optional, int)

Returns `BudgetPolicy` with constraints from environment.

### Tests

**File**: [tests/test_budget_gate.py](tests/test_budget_gate.py)

Comprehensive test suite (14 tests) covering:

**No Constraints** (2 tests):

- Empty policy allows unlimited execution
- None policy allows unlimited execution

**Call Limits** (2 tests):

- Blocks when call count reaches limit
- Allows under call limit

**Token Limits** (4 tests):

- Blocks on token limit exceeded
- Allows within token limit
- Token limit without projection skipped
- Completes error event payload validation

**Determinism & Crash-Safety** (2 tests):

- Repeated checks produce identical results
- Multiple blocks emit deterministic events

**Usage Derivation** (4 tests):

- Derives from `llm.execution_recorded` events
- Computes from prompt + completion tokens
- Ignores non-execution events
- Handles empty projects

**Event Payloads** (1 test):

- `budget.blocked` contains all required fields for explainability

All tests pass with SQLite storage backend.

### Design Principles Maintained

✓ **Deterministic**: All decisions derived from persisted events, reproducible across restarts
✓ **Explainable**: Every budget block emits event with full reasoning
✓ **Crash-Safe**: No in-memory state required; event replay gives authoritative usage
✓ **Non-Invasive**: No silent degradation; blocks are explicit and terminal
✓ **Minimal**: No new persistence tables; uses existing event log
✓ **Focused**: Budget constraints only; does NOT affect routing or task execution semantics
✓ **Optional**: Can be used with or without budget policies

### Integration Points

1. **Before LLM Calls**: `execute_with_route()` and `execute_with_explicit_provider()` check budget
2. **Event Transparency**: All blocks emit `budget.blocked` events for audit trails
3. **CLI Ready**: Environment variables configure budgets for deployments
4. **Test-Friendly**: Works with synthetic events; no provider calls needed

### Example Usage

```python
from openchronicle.core.application.policies.budget_gate import BudgetGate
from openchronicle.core.domain.models.budget_policy import BudgetPolicy

# Create gate and policy
gate = BudgetGate(storage)
policy = BudgetPolicy(
    max_total_tokens=100_000,
    max_llm_calls=50
)

# In LLM execution function
gate.check(project_id, policy, projected_tokens=2000)
# Raises BudgetExceededError and emits budget.blocked if constraints violated

# From CLI/environment
from openchronicle.core.infrastructure.config.budget_config import load_budget_policy
policy = load_budget_policy()  # Reads OC_BUDGET_MAX_TOKENS, OC_BUDGET_MAX_CALLS
```

### Files Created/Modified

**Created:**

- `src/openchronicle/core/domain/models/budget_policy.py`
- `src/openchronicle/core/application/replay/usage_derivation.py`
- `src/openchronicle/core/application/policies/budget_gate.py`
- `src/openchronicle/core/infrastructure/config/budget_config.py`
- `src/openchronicle/core/infrastructure/config/__init__.py`
- `tests/test_budget_gate.py`

**Modified:**

- `src/openchronicle/core/application/services/llm_execution.py` (added optional budget parameters)

### Acceptance Criteria Met

✓ Budget decisions derived from replayed events (crash-safe)
✓ Budget enforcement happens before LLM calls
✓ When blocked, system emits `budget.blocked` and stops explicitly
✓ No routing/provider behavior changes
✓ v1.reference untouched
✓ All new tests pass (14/14)
✓ No errors in implementation code
