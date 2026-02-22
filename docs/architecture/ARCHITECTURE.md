# OpenChronicle v2 Architecture

## Goals

- Manager/supervisor/worker-ready orchestration core
- Strongly typed task/event/resource model with hash-chained events
- Pluggable task handlers and agent templates via registry/loader
- Multi-provider LLM support with routing, fallback, and rate limiting
- Privacy-aware outbound request filtering
- No runtime dependency on v1; v1 is preserved on the `archive/openchronicle.v1` branch

## Layout

```text
src/openchronicle/
├── core/
│   ├── domain/
│   │   ├── errors/              # Error codes and exceptions
│   │   ├── models/              # Core dataclasses (Project, Conversation, Memory, etc.)
│   │   ├── ports/               # Abstract interfaces (LLMPort, StoragePort, etc.)
│   │   └── services/            # Domain services (replay, usage tracking, verification)
│   ├── application/
│   │   ├── config/              # Model configuration loaders
│   │   ├── models/              # Application-level models (diagnostics)
│   │   ├── observability/       # Execution indexing and telemetry
│   │   ├── policies/            # BudgetGate, RateLimiter, RetryController
│   │   ├── replay/              # Project state replay and usage derivation
│   │   ├── routing/             # Pool configuration, router policy, fallback execution
│   │   ├── runtime/             # Container, PluginLoader, TaskHandlerRegistry
│   │   ├── services/            # OrchestratorService, LLM execution
│   │   └── use_cases/           # All business operations (ask, convo, memory, tasks, etc.)
│   └── infrastructure/
│       ├── config/              # Settings and budget configuration
│       ├── llm/                 # Provider adapters (OpenAI, Ollama, Anthropic, Stub)
│       ├── logging/             # EventLogger with hash chaining
│       ├── persistence/         # SqliteStore and schema
│       ├── privacy/             # Rule-based privacy gate
│       ├── router_assist/       # ML-assisted routing (linear, ONNX backends)
│       └── routing/             # Rule-based and hybrid routers
└── interfaces/
    ├── cli/                     # argparse CLI + STDIO RPC protocol
    │   ├── commands/            # Dispatch tables + handler modules
    │   ├── chat.py              # Interactive chat REPL (oc chat)
    │   ├── main.py              # Argparse definitions + slim dispatch
    │   ├── rpc_handlers.py      # 24 RPC handler functions
    │   └── stdio.py             # STDIO server loop + utilities
    ├── discord/                 # Discord bot driver (optional [discord] extra)
    │   ├── bot.py               # commands.Bot subclass + message handling
    │   ├── commands.py          # Slash command definitions
    │   ├── config.py            # Three-layer config (env > core.json > default)
    │   ├── formatting.py        # Message splitting for 2000-char limit
    │   ├── session.py           # Session-to-conversation mapping
    │   └── pid_file.py          # PID file management
    ├── mcp/                     # MCP server (optional [mcp] extra, 20 tools)
    │   ├── server.py            # FastMCP setup + tool registration
    │   ├── config.py            # MCP server configuration
    │   ├── tracking.py          # Tool call statistics
    │   └── tools/               # Tool handler modules
    │       ├── memory.py        # memory_* tools
    │       ├── conversation.py  # conversation_* tools
    │       ├── context.py       # context_recent tool
    │       ├── system.py        # health, tool_stats, moe_stats tools
    │       ├── project.py       # project_* tools
    │       ├── onboard.py       # onboard_git tool
    │       └── asset.py         # asset_* tools
    └── api/                     # HTTP API stub (FastAPI placeholder)

plugins/
├── hello_plugin/                # Minimal example plugin
└── storytelling/                # Story generation plugin with domain/application layers
```

## Key Components

### Domain Layer

**Models:**

- `Project`: Container for conversations and resources
- `Conversation`: Thread of turns with mode (standard/focus/creative/nsfw)
- `MemoryItem`: Persistent memories with pinning and search
- `ExecutionRecord`: LLM call results with usage metrics
- `PrivacyReport`: PII detection results
- `BudgetPolicy`, `RetryPolicy`: Configuration models

**Ports (Interfaces):**

- `LLMPort`: Async LLM generation with usage tracking and function calling (tool use)
- `StoragePort`: Project, task, event, conversation persistence
- `ConversationStorePort`: Conversation and turn storage
- `MemoryStorePort`: Memory CRUD operations
- `PluginPort`: Handler registration interface
- `PrivacyGatePort`: PII detection interface
- `InteractionRouterPort`: Routing decisions
- `RouterAssistPort`: ML-assisted routing

### Application Layer

**Policies:**

- `BudgetGate`: Per-task token budget enforcement
- `RateLimiter`: RPM/TPM rate limiting with token bucket algorithm
- `RetryController`: Exponential backoff with jitter

**Routing:**

- `PoolConfig`: Provider pools (fast, quality, NSFW)
- `RouterPolicy`: Mode selection and budget-aware downgrade
- `FallbackExecutor`: Automatic fallback on provider failures

**Runtime:**

- `Container`: Dependency injection and component wiring
- `PluginLoader`: Dynamic plugin discovery and loading
- `TaskHandlerRegistry`: Task type to handler mapping

**Use Cases:** Over 30 use cases including conversation management, memory operations, task execution, diagnostics, and selftest.

### Infrastructure Layer

**LLM Adapters:**

- `OpenAIAdapter`: Full OpenAI API integration with usage tracking
- `OllamaAdapter`: Local Ollama instance support
- `AnthropicAdapter`: Mock implementation (placeholder)
- `StubAdapter`: Deterministic responses for testing

**Persistence:**

- `SqliteStore`: SQLite backend with JSON payload storage
- Schema includes projects, conversations, turns, memories, tasks, events, usage

**Privacy:**

- `RulePrivacyGate`: Pattern-based PII detection (emails, phones, SSNs, API keys)
- Configurable modes: off, warn, block, redact

**Router Assist:**

- `LinearAssist`: Logistic regression-based content classification
- `OnnxAssist`: ONNX runtime for ML model inference

## Event Model

Events link via `prev_hash` → `hash`, enabling tamper-evident timelines per task. `EventLogger.append` fetches the latest event for a task, sets `prev_hash`, computes the hash, and persists.

## Routing System

The routing system selects providers and models based on:

1. **Mode**: fast, quality, or nsfw (affects model selection)
2. **Pools**: Configurable provider:model lists per mode
3. **Weights**: Provider preference weights for load distribution
4. **Fallback**: Automatic retry with different providers on failure
5. **Budget-aware**: Downgrade to cheaper models when budget is low

## Privacy Gate

Outbound LLM requests pass through a privacy gate that:

- Detects PII patterns (emails, phone numbers, SSNs, API keys)
- Configurable action: warn (log), block (reject), or redact (mask)
- External-only option: skip for local/stub providers
- Full event logging for audit trails

## Plugin System

Plugins are discovered from `plugins/` directory:

1. Each plugin exports `register(registry)` function
2. Handlers use `namespace.action` naming (e.g., `hello.echo`, `story.draft`)
3. Task type `plugin.invoke` routes to handlers via `payload.handler`
4. Plugins can define their own domain/application layers

## CLI and RPC

The `oc` CLI provides:

- Project and conversation management
- Memory operations (add, pin, search)
- Task submission and execution
- STDIO RPC protocol (JSON-RPC over stdin/stdout)
- Diagnostic and selftest commands

## Backlog

See `docs/BACKLOG.md` for planned features including:

- Security scanner plugin
- Dev agent runner (sandboxed)
- HTTP API implementation

Already implemented as core capabilities (not plugins — see Decision #4):

- Scheduler service (`application/services/scheduler.py`, 52+ tests)
- Discord interface (`interfaces/discord/`, 60 tests, optional `[discord]` extra)
