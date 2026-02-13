# Manual Integration Checklist

Interactive features that require human observation. Run these after the
automated suite passes.

## Prerequisites

```bash
export OC_CONFIG_DIR="C:\Docker\openchronicle\config"
export OC_LLM_PROVIDER=openai          # or anthropic, ollama
export OPENAI_API_KEY=<key>             # if using openai
```

## Checklist

### M1 — Streaming visual

- **Steps:** `oc chat --title "Stream Test"`, type "Tell me a short story"
- **Expected:** Tokens appear incrementally, not all at once

### M2 — Chat resume

- **Steps:** Exit chat (`/quit`), run `oc chat --resume`
- **Expected:** Same conversation, history preserved

### M3 — Chat quit

- **Steps:** Type `/quit` in chat
- **Expected:** Clean exit, no error, no traceback

### M4 — Diagnose

- **Steps:** `oc diagnose`
- **Expected:** Shows DB path, config dir, provider env vars

### M5 — Non-stream chat

- **Steps:** `oc chat --no-stream`, type a prompt
- **Expected:** Response appears all at once after delay

## Notes

- M1 and M5 are a pair: streaming vs non-streaming should be visually
  distinguishable.
- M2 depends on M1 having created a conversation first.
- M4 does not require a running provider — it inspects configuration only.
