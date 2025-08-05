# 🖼️ Image Generation Engine – Plugin System Design

Goal: Add support for visual storytelling by generating optional character/scene/world images. These are stored in a non-critical `/images/` folder inside the active storypack.

---

## 📦 Directory Design
- [ ] Add `/images/` to storypack structure
- [ ] Use naming conventions: `scene-000123.png`, `char-aletha.png`, `world-map-v1.png`
- [ ] Log generation metadata in `images.json` (model used, prompt, timestamp)

---

## 🔌 Model Plugin System
- [ ] Mirror `model_adapter.py` pattern with `image_adapter.py`
- [ ] Allow OpenArt API, local Stable Diffusion, and DALL·E as plugins
- [ ] Add fallback system: skip image if model unavailable or fails

---

## 🧠 Integration Flow
- [ ] CLI: `--generate-image [scene|character|custom]`
- [ ] Background: autogenerate portrait at character creation (optional)
- [ ] Optionally trigger scene-based image gen after a major moment

---

## 🧰 Future Enhancements
- [ ] Link image IDs to memory/scene entries for visual audit trails
- [ ] Auto-tag character image as profile pic (for frontend use)
- [ ] Add per-model config in `models.json` (e.g. SD resolution, steps, API key)