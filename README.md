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
