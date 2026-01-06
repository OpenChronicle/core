# OpenChronicle Core v2 (clean slate)

This branch introduces a fresh orchestration core intended for a manager/supervisor/worker LLM system. The prior implementation now lives in `v1.reference/` as a frozen snapshot.

Key points:

- New source root: `src/openchronicle/`
- Plugins root: `plugins/`
- V1 snapshot: `v1.reference/` (read-only reference)

Use `oc --help` after installing in editable mode (`pip install -e .`) to explore the minimal CLI.

## LLM Provider Configuration

OpenChronicle supports multiple LLM providers via explicit configuration:

### Installation

Base installation (includes stub provider):

```bash
pip install -e .
```

With OpenAI support:

```bash
pip install -e ".[openai]"
```

### Provider Selection

Control which LLM provider to use via the `OC_LLM_PROVIDER` environment variable:

- **`stub` (default)**: Uses a simple stub adapter for testing/demos
- **`openai`**: Uses OpenAI API (requires `OPENAI_API_KEY`)

```bash
# Default behavior (uses stub)
oc demo-summary <project_id> "Your text here"

# Explicitly use OpenAI
export OC_LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
oc demo-summary <project_id> "Your text here"

# Override provider for a single command
export OC_LLM_PROVIDER=stub  # or unset
oc demo-summary <project_id> "Your text here" --use-openai
```

### Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `OC_LLM_PROVIDER` | `stub`, `openai` | `stub` | Selects LLM provider |
| `OPENAI_API_KEY` | API key string | - | Required when using OpenAI provider |
| `OPENAI_MODEL` | Model name | `gpt-4o-mini` | OpenAI model to use |
| `OPENAI_BASE_URL` | URL string | - | Optional custom API endpoint |
| `OC_MAX_TOKENS_PER_TASK` | Integer | - | Budget limit: blocks LLM calls if task exceeds this total token count |
| `OC_MAX_OUTPUT_TOKENS_PER_CALL` | Integer | - | Clamps max_output_tokens for each LLM request to this value |

## Usage Tracking and Token Budgets

OpenChronicle automatically tracks LLM usage metrics (input/output/total tokens, latency) for all API calls and stores them in the database.

### View Usage Statistics

```bash
# Show usage for a project
oc usage <project_id>

# Show only the N most recent calls
oc usage <project_id> --limit 10
```

The usage command displays:

- Total token counts (input/output/total)
- Breakdown by provider and model
- List of recent API calls with timestamps and latency

### Token Budgets

Set budget limits to control LLM costs and prevent runaway token usage:

#### Per-Task Budget

Prevents a single task from exceeding a total token limit:

```bash
export OC_MAX_TOKENS_PER_TASK=10000
oc demo-summary <project_id> "Your text"
```

If the task has already consumed 10,000+ tokens, subsequent LLM calls will:

- Raise a `BudgetExceededError`
- Emit an `llm.budget_exceeded` event
- Mark the task as failed

#### Per-Call Output Clamping

Limits the maximum output tokens for each individual LLM request:

```bash
export OC_MAX_OUTPUT_TOKENS_PER_CALL=500
oc demo-summary <project_id> "Your text"
```

Any LLM request with `max_output_tokens > 500` will be clamped to 500. The system emits an `llm.request_clamped` event when this occurs.

### Budget Events

Budget enforcement emits the following events for observability:

- `llm.budget_exceeded`: Task exceeded `OC_MAX_TOKENS_PER_TASK` limit
- `llm.request_clamped`: Output tokens were clamped due to `OC_MAX_OUTPUT_TOKENS_PER_CALL`
