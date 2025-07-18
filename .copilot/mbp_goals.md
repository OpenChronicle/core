📦 OpenChronicle MVP Milestone – Deployment Target 0.1.x

🔧 PRIMARY GOAL:
Deliver a locally-runnable container that supports full interactive storytelling from a prebuilt storypack using hybrid LLMs, with rollback and character memory consistency.

---

✅ REQUIRED FEATURES (MVP WALL)

1. 🗂️ Storypack Loader (CORE)
   - Loads `meta.json`, `characters/`, `world/`, `canon/`
   - Fails gracefully on missing or malformed data

2. 🎭 Character Engine (CORE)
   - Injects per-character tone/style/personality into LLM prompt
   - Consistent across interactions

3. 🧠 Context Assembly (CORE)
   - Builds prompt context using canon + memory
   - Scales for small to medium scenes (~2K tokens)

4. 🔀 Model Routing (LITE)
   - Routes to correct LLM adapter (OpenAI or Ollama)
   - Handles token overflow with fallback logic (e.g. retry with shorter context)

5. 💾 Scene Logger + Rollback
   - Writes each user/LLM interaction to SQLite
   - Supports rollback to any prior scene
   - CLI accessible (`--rollback [scene_id]` or `--rewind`)

6. 🧪 NSFW/Tone Detection (BASIC)
   - Uses DistilBERT or keyword filter
   - Logs routing decision
   - Does *not* need full emotion/tone diff yet

7. 🧰 CLI Engine (INITIAL)
   - `openchronicle start --story demo-story`
   - `openchronicle rollback`
   - `openchronicle devtools --log` (or similar)
   - No GUI necessary

---

📉 DEFERRED UNTIL POST-MVP

- Visual UI
- Storypack submission/import pipeline
- Bookmark manager
- Advanced search engine CLI
- Real-time multi-character co-processing
- Context audit trail export
- Per-token cost logging
- Emotion curve/timeline visualization

---

🧪 TESTING ENV

- Target: NAS or x86 Docker
- LLM: Mix of OpenAI (gpt-4o or gpt-3.5) and local Ollama model (Mistral recommended)
- Storypacks: 1 demo fantasy, 1 sci-fi, 1 blank template

---

🚀 MVP DELIVERY = THE MOMENT USERS CAN:

- Load a story
- Start chatting
- Watch characters behave consistently
- Trigger rollback
- Switch models if needed