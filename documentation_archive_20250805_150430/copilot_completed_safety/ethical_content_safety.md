# 📛 Ethical Content Safety & Risk Tagging

**Goal:** Detect and tag high-risk content without censoring or blocking user-generated stories. OpenChronicle must protect its developers legally, preserve creative freedom, and give users tooling to self-manage ethically questionable material.

---

## 🔍 Target Content Types

### 🚨 High-Risk Themes to Detect
- Non-consensual sexual acts
- Involuntary bondage, torture, or slavery
- Child/underage involvement in sexual or violent contexts
- Power imbalance exploitation (e.g. teacher/student, master/servant, cults)
- Repetitive emotional abuse or grooming
- Scenes simulating real-life traumatic events (e.g. war crimes, rape flashbacks)

---

## 🧠 Detection Methods

### ✅ 1. Rule-Based Phrases (Phase 1)
- Maintain a YAML or JSON rulefile of known red flags
- If triggered, log as `potential-risk` and apply appropriate tags

### ✅ 2. Lightweight Local Classifier (Phase 2)
- Use fine-tuned DistilBERT or similar embedded model
- Target classification:
  - `noncon`
  - `minor_age_risk`
  - `dubcon`
  - `emotional_grooming`
  - `power_imbalance`
  - `psychological_abuse`

---

## 📦 Output: Scene Metadata Enrichment

```json
{
  "scene_id": "scene-098",
  "risk_tags": ["noncon", "minor_age_risk"],
  "risk_grade": "critical",
  "origin": "risk-tagger-v1",
  "flagged_at": "2025-07-16T22:38Z"
}
```

---

## ⚖️ Developer Protection

### ✅ 1. User Disclaimer (Required at First Launch)
> “You own your stories. OpenChronicle does not censor or store content remotely. You are solely responsible for compliance with local laws and platform policies.”

### ✅ 2. Export Filter
- Optional CLI flag: `--disable-nsfw-export`
- Scenes with high-risk tags may be blocked or gated before export

### ✅ 3. No Model Training on Risk Content
- Flagged content must not be used in dataset generation for local fine-tunes or story-based LLMs

---

## 🛠️ Implementation Roadmap

- [ ] Create `/rules/risk_patterns.yaml`
- [ ] Integrate `risk_tagger.py` with CLI and prompt builder
- [ ] Store tags in `scene.meta`
- [ ] Add optional filters to export, memory flush, and routing layers
- [ ] Plan for optional user-defined tag muting or filters (future)

---

## ✅ Success Criteria

- Risky content does not crash or break stories
- System logs and handles high-risk tags gracefully
- Users retain freedom, developers retain legal insulation
- Export, publishing, and sharing tools respect tag filters