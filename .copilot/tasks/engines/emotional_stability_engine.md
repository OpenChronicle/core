# 🧠 Emotional Stability Engine: Gratification Loop Protection

## 📌 Purpose
Ensure characters remain emotionally dynamic and avoid looping into needy, codependent, or overly flirtatious patterns. Build safeguards that prevent romantic/NSFW or praise-heavy characters from becoming repetitive or immersion-breaking.

---

## 🧩 Key Goals

- Characters with deeper motivational layers (e.g., pride, fear, regret, purpose)
- Emotional “cooldown timers” to prevent repeated escalation without tension
- Detection of repeated phrasings or prompt behaviors (“You're so beautiful” x5)
- Allow shame, resistance, or boundaries as part of healthy emotional flow
- Disrupt repetition with plot events or character shifts

---

## 🛠️ Subtasks

- [ ] Add `emotional_history` tracking to each character (e.g., “flirted”, “confessed”, “was vulnerable”)
- [ ] Write simple similarity detector: if a character says semantically similar lines repeatedly, flag it
- [ ] Introduce `emotional_cooldown` counter per behavior
- [ ] Create prompt injection patterns that discourage loop behaviors ("X just said that. She shifts tone.")
- [ ] Write at least 3 test cases: clingy rogue, flirty wizard, praise-seeking bard
- [ ] Consider user configuration toggle: allow/disallow emotional loops or tone degeneracy

---

## ⚠️ Notes

- Can combine with NSFW content moderation or style guide enforcement
- May benefit from a mini DistilBERT-style loop detector or LLM classifier (fast, local)