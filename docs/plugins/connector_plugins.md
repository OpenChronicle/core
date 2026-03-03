# Connector Plugins

Connector plugins bridge external services with OC's memory system. They
use the enriched handler context to store, search, and update memories
without importing core internals. All capabilities are injected at
invocation time.

**Repository:** Connector plugins are developed in
[openchronicle/plugins](https://github.com/OpenChronicle/plugins) and
deployed into core's plugin directory via symlink or copy. Core's
`plugins/` directory works via `OC_PLUGIN_DIR`.

---

## Available Connectors

| Plugin | Service | Handlers | Status |
| ------ | ------- | -------- | ------ |
| `plex_connector` | Plex Media Server | `plex.sync`, `plex.webhook`, `plex.query` | Done |
| `plaid_connector` | Plaid (banking) | `plaid.sync`, `plaid.categorize`, `plaid.query` | Done (needs sandbox credentials for live testing) |

---

## Plex Connector

Syncs Plex media library metadata and watch history into OC memory.

### Setup

1. Copy or symlink `plex_connector/` into your plugin directory.

2. Edit `plex_connector/config.json`:

   ```json
   {
     "plex_url": "http://your-plex-server:32400",
     "plex_token": "your_key_here",
     "sync_libraries": [],
     "sync_history_days": 30
   }
   ```

3. Authenticate:

   ```bash
   oc plex auth
   ```

   This opens your browser for Plex sign-in, polls for the token, and
   saves it to `config.json`.

### Handlers

#### `plex.sync`

Poll-based library sync. Fetches new items and watch history since the
last watermark, saves each as a memory item.

- **Tags:** `plex-item`, `media`, `<library_name>` for library items;
  `plex-watch`, `media` for watch events
- **Watermark:** Stored as a pinned memory with tag `plex-sync-state`
- **Config:** `sync_libraries` (filter to specific libraries),
  `sync_history_days` (lookback on first sync)

#### `plex.webhook`

Real-time push handler for Plex webhooks. Receives events via the
generic hooks endpoint:

```text
POST /api/v1/hooks/plex.webhook?project_id=<uuid>
```

Plex sends multipart form-data with a `payload` JSON field. The hooks
endpoint parses both JSON and multipart automatically.

**Events handled:**

- `media.scrobble`, `media.stop` — saves watch memory
- `library.new` — saves library item memory
- All other events — ignored (returns `{"ignored": true}`)

To configure in Plex: Settings > Webhooks > Add Webhook > paste the URL.

#### `plex.query`

Search Plex items in memory with optional LLM summary.

- **Payload:** `{"query": "Inception", "summarize": true}`
- **Tags filter:** Searches only `plex-item` tagged memories
- **Summary:** When `summarize: true`, passes results through
  `llm_complete` for a natural language answer

### Memory Format

```text
[Plex] Title: Inception | Type: movie | Year: 2010 | Rating: 8.8 | Added: 2026-01-15 | Duration: 148min | Library: Movies
Genres: Action, Sci-Fi, Thriller
```

```text
[Plex Watch] Title: Inception | Type: movie | Watched: 2026-03-01T20:30:00+00:00
```

---

## Plaid Connector

Syncs Plaid financial transaction data into OC memory. Designed for
append-only financial integrity — removed transactions are tagged, never
deleted.

### Setup

1. Copy or symlink `plaid_connector/` into your plugin directory.

2. Get Plaid API credentials from
   [dashboard.plaid.com](https://dashboard.plaid.com).

3. Edit `plaid_connector/config.json`:

   ```json
   {
     "plaid_client_id": "your_key_here",
     "plaid_secret": "your_key_here",
     "plaid_env": "sandbox",
     "access_tokens": {},
     "sync_days_initial": 90
   }
   ```

4. Authenticate (sandbox — no browser needed):

   ```bash
   oc plaid auth --sandbox
   ```

   This uses Plaid's `/sandbox/public_token/create` endpoint to generate
   a test token for First Platypus Bank (`ins_109508`) instantly, then
   exchanges it for an `access_token` and saves it to `config.json`.

5. Authenticate (production — browser required):

   ```bash
   oc plaid auth
   ```

   This creates a Plaid Link token, prints the URL, and waits for you to
   paste the `public_token` after completing Link in your browser.

6. Name the institution when prompted (e.g., "Chase"). Multiple
   institutions are supported — run `oc plaid auth` once per bank.

### Handlers

#### `plaid.sync`

Incremental transaction sync using Plaid's `/transactions/sync` cursor
API. Each institution gets its own cursor.

- **Tags:** `plaid-txn`, `finance`, `<category-slug>` for new
  transactions (e.g., `food-and-drink`, `transportation`)
- **Modified transactions:** Found by Plaid ID in memory, updated
  via `memory_update`
- **Removed transactions:** Tagged `["plaid-txn", "removed"]` — never
  deleted from memory (append-only for financial data integrity)
- **Sync state:** Stored as a pinned memory with tag `plaid-sync-state`,
  containing JSON with per-institution cursors:

  ```json
  {"cursors": {"Chase": "cur_abc123", "Wells Fargo": "cur_xyz789"}}
  ```

#### `plaid.categorize`

LLM-assisted categorization of uncategorized transactions.

1. Searches for transactions tagged `UNCATEGORIZED`
2. Sends a batch to `llm_complete` with a categorization prompt
3. Updates each transaction's content and tags with the assigned category

**Categories:** `FOOD_AND_DRINK`, `TRANSPORTATION`, `SHOPPING`,
`ENTERTAINMENT`, `HEALTHCARE`, `UTILITIES`, `HOUSING`, `INCOME`,
`TRANSFER`, `OTHER`

#### `plaid.query`

Search transactions in memory with optional LLM summary.

- **Payload:** `{"query": "How much did I spend on food?", "summarize": true}`
- **Tags filter:** Searches only `plaid-txn` tagged memories
- **Summary:** When `summarize: true`, passes results through
  `llm_complete` for a natural language answer

### Memory Format

```text
[Transaction] 2026-03-01 | Starbucks | $4.50 | FOOD_AND_DRINK
Account: Checking (****0123) | Plaid ID: txn_abc123
Pending: False
```

### Auth Flow Options

| Method | Command | When to Use |
| ------ | ------- | ----------- |
| Sandbox | `oc plaid auth --sandbox` | Testing (instant, no browser) |
| Production | `oc plaid auth` | Real bank connections (browser required) |

The `--sandbox` flag calls `/sandbox/public_token/create` directly,
bypassing Plaid Link entirely. It uses `ins_109508` (First Platypus
Bank) which comes pre-loaded with test transactions.

The `--institution-name` flag lets you name the institution on the
command line instead of being prompted:

```bash
oc plaid auth --sandbox --institution-name "Test Bank"
```

---

## Enriched Handler Context

Both connectors rely on the enriched handler context injected by the
orchestrator. When a `plugin.invoke` task is dispatched, the handler
receives these closures in the `context` dict:

| Key | Type | Purpose |
| --- | ---- | ------- |
| `memory_save` | `(content, tags?, pinned?) -> MemoryItem` | Save a new memory |
| `memory_search` | `(query, tags?, top_k?) -> list[MemoryItem]` | Search memories |
| `memory_update` | `(memory_id, content?, tags?) -> MemoryItem` | Update an existing memory |
| `llm_complete` | `async (messages, max_output_tokens?, temperature?) -> LLMResponse` | Call the LLM (auto-routed) |
| `plugin_config` | `dict` | Plugin's `config.json` contents |

Handlers never import core internals. All capabilities are dependency-injected.

---

## Writing a New Connector

Follow the Plex/Plaid patterns:

1. **API client** (`<service>_api.py`) — async httpx wrapper for the
   external service. Each method opens its own `httpx.AsyncClient`
   context manager.

2. **Auth flow** (`<service>_auth.py`) — sync httpx for CLI context.
   Handles credential exchange and saves to `config.json`.

3. **Plugin handlers** (`plugin.py`) — three standard handlers:
   - `<service>.sync` — incremental data sync with watermark/cursor
   - `<service>.query` — search memories with optional LLM summary
   - Third handler varies (webhook, categorize, etc.)

4. **CLI** (`cli.py`) — plugin CLI protocol with `COMMAND`, `HELP`,
   `setup_parser()`, `run()`. Discovered automatically by the core CLI.

5. **Config** (`config.json`) — credentials as `your_key_here`
   placeholders (detected by `test_no_secrets_committed.py`).

6. **Tests** — unit tests with mocked httpx and mocked context closures.
   Integration tests skipped without environment variables.
