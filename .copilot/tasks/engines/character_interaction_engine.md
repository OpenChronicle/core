# 🧠 Character Interaction Engine

## 📌 Purpose
Enable dynamic, believable conversations and emotional interactions between characters — not just between character and user. This is essential for immersive storytelling and drama that feels reactive, not scripted.

---

## 🧩 Key Goals

- Characters can **respond to each other**, not just the user
- Track **relational state** (trust, suspicion, fear, etc.) between characters
- Simulate **emotion-driven behavior shifts** (anger, grief, sarcasm, affection)
- Maintain individual **memory/state contexts** per character
- Detect and support **multi-speaker conversation flows**
- Allow **hidden thoughts**, deception, and motives not spoken aloud
- Structure a “scene controller” to **orchestrate timing and turns**

---

## 🛠️ Subtasks

- [ ] Create emotion/state data structure for each character in-scene
- [ ] Add scene history threading to pass structured dialog history into LLM prompts
- [ ] Design context merging strategy that injects relevant past events
- [ ] Enable whisper/private thought processing separate from spoken dialogue
- [ ] Allow post-turn state updates (e.g., Alric’s trust in Vesh drops by 20%)
- [ ] Add character “motivations” that push their next move (e.g., defend Kara, betray Vesh)
- [ ] Support alternating response turns, not just sequential monologue blocks
- [ ] Write prompt templates that reflect character A responding to character B’s prior statement with tone/memory awareness

---

## ⚠️ Notes

- Must avoid verbosity loops (characters shouldn’t all monologue every turn)
- Emotional escalation must be bounded by tone/style guide
- Test with 3+ character scenes under stress conditions (e.g., betrayal + rescue)
- May require LLM-level “backchannel” communication between characters to fake NPC plotting

---

## 🔮 Optional Stretch Goals

- Implement a “Whispers” feature: secret messages or intentions visible only to select characters
- Build a UI visualization of trust/hostility shifting in real time
- Build quick-start templates like “heist team falling apart” or “courtroom drama” to test dynamics