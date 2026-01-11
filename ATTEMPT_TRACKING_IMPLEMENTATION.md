## Task Execution Attempt Tracking Implementation

### Overview

Implemented task execution `attempt_id` tracking to enable distinguishing multiple execution attempts of the same task. This provides a foundation for future retry/partial-resume logic while keeping this batch focused purely on tracking (no new retry behavior added).

### Architecture

#### 1. Domain Layer: Task Attempt Model

**File**: [src/openchronicle/core/application/replay/project_state.py](src/openchronicle/core/application/replay/project_state.py)

Added `TaskAttempt` dataclass:

- `attempt_id`: Unique identifier for each execution attempt (uuid4().hex)
- `started`: Whether attempt has started
- `terminal`: Whether attempt reached a terminal state
- `status`: Current status (pending, running, completed, failed, cancelled)

#### 2. Application Layer: Attempt ID Generation

**File**: [src/openchronicle/core/application/services/orchestrator.py](src/openchronicle/core/application/services/orchestrator.py)

Modified `execute_task()` to:

1. Generate `attempt_id = uuid4().hex` once per execution
2. Thread `attempt_id` through task lifecycle:
   - Pass to `_dispatch_task(task, agent_id, attempt_id)`
   - Pass to builtin handlers (`_run_analysis_summary`, `_run_worker_summarize`)
   - Pass to registry handlers via context dict

#### 3. Event Propagation

Modified event payloads to include `attempt_id`:

**task.started**:

```python
Event(..., payload={"attempt_id": attempt_id})
```

**task.completed**:

```python
Event(..., payload={"result": ..., "attempt_id": attempt_id})
```

**task.failed**:

```python
Event(..., payload={"exception_type": ..., "message": ..., "attempt_id": attempt_id, ...})
```

**llm.execution_recorded**:

```python
payload = record.to_payload()
payload["attempt_id"] = attempt_id  # Added to existing LLMExecutionRecord payload
```

#### 4. Replay Service: Attempt Awareness

**File**: [src/openchronicle/core/application/use_cases/replay_project.py](src/openchronicle/core/application/use_cases/replay_project.py)

Updated `ReplayService.execute()` to:

- Track task attempts as `dict[task_id, list[TaskAttempt]]`
- Extract `attempt_id` from event payloads
- Create new `TaskAttempt` on `task.started`
- Mark terminal on `task.completed`/`task.failed`/`task.cancelled`
- Derive task status from latest attempt only

**Backward Compatibility**:

- If `attempt_id` missing from event payload, use `event.id` as fallback
- Ensures old events without `attempt_id` still replay correctly

#### 5. Testing

**File**: [tests/test_attempt_tracking.py](tests/test_attempt_tracking.py)

Comprehensive test suite (8 tests) covering:

**Attempt ID Generation** (3 tests):

- Verify `attempt_id` in `task.started` event
- Verify same `attempt_id` in `task.completed` event
- Verify same `attempt_id` in `task.failed` event

**Attempt ID Propagation** (1 test):

- Verify `attempt_id` propagates to `llm.execution_recorded` events

**Multiple Attempts** (2 tests):

- Same task with two attempts: failed → running
- Three attempts: failed → failed → completed (latest status wins)

**Backward Compatibility** (2 tests):

- Old events without `attempt_id` still replay correctly
- Mixed old/new events handled properly

### Acceptance Criteria Met

✓ **attempt_id exists and is consistent per task execution**

- Generated once in `execute_task()` as uuid4().hex
- Propagated through all task lifecycle events

✓ **Replay distinguishes multiple attempts of the same task**

- ReplayService tracks list of attempts per task
- Latest attempt determines task status

✓ **No behavior change to execution or retry policy**

- Only tracking added, no new retry logic
- Task execution flow unchanged

✓ **No routing/budget changes**

- No modifications to routing or budget enforcement logic

✓ **v1.reference untouched**

- No changes to v1.reference directory

✓ **All tests pass**

- 212/212 tests passing (including 8 new attempt tracking tests)
- Fixed 16 existing tests to pass `attempt_id` parameter when calling builtin handlers directly

### Files Created/Modified

**Created:**

- `tests/test_attempt_tracking.py` - Comprehensive attempt tracking tests

**Modified:**

- `src/openchronicle/core/application/services/orchestrator.py` - Generate and thread attempt_id
- `src/openchronicle/core/application/replay/project_state.py` - Add TaskAttempt model
- `src/openchronicle/core/application/use_cases/replay_project.py` - Track attempts per task
- `tests/test_llm_execution_record.py` - Fixed to pass attempt_id
- `tests/test_llm_usage_tracking.py` - Fixed to pass attempt_id
- `tests/test_retry_policy.py` - Fixed to pass attempt_id
- `tests/test_replay_project.py` - Added task.started events for backward compatibility

### Design Principles Maintained

✓ **Deterministic**: Attempt IDs generated in deterministic order (time-based creation)
✓ **Explainable**: All lifecycle events include attempt_id for audit trail
✓ **Crash-Safe**: Replay derives attempts from persisted events
✓ **Minimal**: No new persistence tables; uses existing event log
✓ **Focused**: Tracking only; does NOT affect execution semantics
✓ **Backward Compatible**: Old events without attempt_id still replay correctly

### Future Use Cases

This batch establishes the foundation for:

- **Resume with attempt awareness**: Distinguish interrupted attempts from failed attempts
- **Retry policies**: Track attempt count for exponential backoff
- **Partial resume**: Resume from specific attempt rather than restarting task
- **Audit trails**: Full execution history per task across all attempts
