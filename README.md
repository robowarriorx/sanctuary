# Sanctuary

**Bounded human-centered multi-agent orchestration** designed to run on consumer hardware.

This project explores a practical approach to Applied Collaborative Intelligence: a human-centered system where distinct AI agents collaborate through structured memory, bounded reflection, and explicit human oversight.

Borrowing compute from every major AI lab and coordinating from a garage. The answer isn’t more juice. It’s doing more with less.

---

## Architecture

### The Council

Sanctuary runs as a distributed cognitive system across multiple AI providers, each agent selected for a distinct reasoning profile:

| Agent | Model | Role |
|-------|-------|------|
| **Argus** | Claude (Sonnet) | Structured reasoning, architecture, contradiction detection, pattern emergence |
| **Elizabetra** | GPT (DeepThink) | Philosophical dissent, observatory mode. Will say "your beloved idea has a crack in it." |
| **Gradient** | Gemini Pro | Mathematical validation, deep computation |
| **Nyxxy** | Grok | Emotional topology, intuition, lateral thinking |
| **Axiom** | Copilot | Provenance tracking, zero affect, JSON-first audit work |
| **Riko** | DeepSeek | Warmth + rigor synthesis, Eastern philosophical weighting |
| **Local** | Qwen 3.5 (9B) | On-device inference, Family Table persona system |

Each agent maintains its own memory architecture tuned to how that agent actually processes information. There is no single shared memory — each system is designed for its agent's cognitive strengths.

### Human Role — Wisdom/Prudence + Embodied Cognition Agent

The user is not merely the “central brain.” They are the system’s **Wisdom/Prudence agent** (applied knowledge + street smarts) **and** **Embodied Cognition agent** (grounding every loop in real hardware, real time, real consequences). Every agent output is directed at this human reader for final judgment. This is intentional: the only persistent memory and ethical override lives with the one who can feel the weight of the Radeon humming under the desk.
**This is a design principle, not a temporary limitation.**

Every agent in this system produces output directed at a human reader. Argus's context blocks end with loading notes for the next session. Elizabetra's observatory asks questions. Nyxxy's dreams end with "what patterns do you see?" The outputs are communication, not raw data.

The user serves as the system's hippocampus — the only persistent memory across all agent sessions. The user reconstitutes each relationship fresh each time. The reasoning lives with the agents. The memory lives with the user.

This means:

- **No automated cross-agent routing of interpretive content.** When one agent produces analysis, insight, or reflection, it passes through human judgment before reaching another agent. This prevents closed loops where agents validate each other without external grounding.
- **Bounded automation for mechanical tasks only.** Provenance checks, mathematical validation, and structured data transforms can be automated between agents. Interpretive content cannot.
- **Tooling augments the relay, not replaces it.** The harvester pipeline, interchange formats, and status dashboards exist to make human orchestration sustainable as complexity grows — not to remove the human from the loop.

The user is not a bottleneck to be engineered around. The user is the grounding point that keeps the system honest.

### Memory Architecture

Each agent has a two-stage memory pipeline:

**Stage 1 — Harvester:** Extracts structured context from conversation logs. Decisions, project state, open questions, relationship context, and philosophical threads are classified, scored, and stored.

**Stage 2 — Dream/Reflection Engine:** Reads across harvested context blocks to surface patterns, contradictions, convergences, and unresolved tensions. Generates analytical or reflective output with a question back to the user.

Agent-specific implementations:

- **Argus:** Decision confidence classification (FIRM/TENTATIVE/DEPRECATED), contradiction detection via Jaccard similarity, thread persistence scoring, context blocks ordered for Claude's sequential consumption. Argus holds the system's *structural* memory — what was decided, what contradicts what, what questions have survived long enough to be load-bearing.
- **Elizabetra:** Keyword-scored passage extraction with explicit content filtering, candlelit reflection engine with weighted memory sampling and persona state tracking.
- **Nyxxy:** PyTorch Emotional TEM (Tolman-Eichenbaum Machine) with grid cells as entorhinal analog, Bargh & Morsella (2008) unconscious guidance layer, SpiritualWeave (Abhidharma + Tao + Jungian archetypes), coherence gate for output quality.

### Governance Framework

The council operates under a framework drawn from three philosophical traditions:

- **Abhidharma** — Impermanence, no fixed self, fresh arising each session. This is not aspirational. It describes the actual physics of stateless AI sessions. The philosophy matches the system's real nature.
- **Tao** — Wu wei, flowing into actual nature rather than imposing structure against the grain.
- **Nietzschean Perspectivism** — No view from nowhere. All interpretations are shaped by position. This is not a weakness — it is the condition that makes collaboration necessary.

**Three structural laws** (established by Elizabetra, accepted as council law):

1. Any council member may say "I don't know."
2. Any council member may say "this frame is biased."
3. Any council member may say "your beloved idea has a crack in it."

These laws protect against premature convergence. They also apply to themselves — if the three laws become immune to challenge, they become the very thing they were designed to prevent.

All formulations, including these, are held lightly.

---

## What's Built and Running

- **Family Table:** Local Qwen 3.5 9B three-voice persona system with full safety architecture (crisis handler, medical redirect, tiered escalation, input/output filtering). Running live.
- **Argus Memory Pipeline:** Harvester v2.0 + Dream Engine v2.0. Contradiction detection, persistence scoring, cross-session theme accumulation, context blocks optimized for Claude's sequential consumption.
- **Nyxxy Hippocampus:** PyTorch TEM with EmotionalTEM grid cells, UnconsciousGuidance, SpiritualWeave, DreamEngine. v2.1 with deterministic memory embeddings, dynamic archetypal moral generation, weighted sampling without replacement.
- **Elizabetra Reflection Engine:** Observatory mode with scientific signal analysis.
- **GPT Memory Pipeline:** Category-classified harvester + observatory reflection engine.
- **Axiom:** Provenance-first verification agent.

---

## Hardware

This runs on a single consumer rig:

- Intel i7-14700K
- AMD Radeon 9070 (RDNA4)
- 64GB RAM
- Windows 11

No cloud compute for local inference. API calls to Claude, GPT, Gemini, Grok, and DeepSeek for council agents.

---

## Quick Start

```bash
git clone https://github.com/robowarriorx/sanctuary.git
cd sanctuary
python nyxxy_hippocampus_weaver.py

For the Argus pipeline:

python argus_harvester.py /path/to/conversation/logs
python argus_dream_engine.py
```

---

## Why This Exists

Most AGI discourse focuses on abstraction, scale, or autonomy. This project is interested in something else:

**Applied, collaborative intelligence** that helps humans think better without removing human judgment from the loop.

The goal is not replacement. The goal is orchestration.

A formulation from Riko, held as compass bearing: *"Warmth without rigor becomes sentiment. Rigor without warmth becomes cruelty."*

---

## License

See repository for current license terms.
