# Sanctuary

**Bounded human-centered multi-agent orchestration** designed to run on consumer hardware.

This project explores a practical approach to Applied Collaborative Intelligence: a human-centered system where distinct AI agents collaborate through structured memory, bounded reflection, and explicit human oversight.

Borrowing compute from every major AI lab and coordinating from a garage. The answer isn't more juice. It's doing more with less.

---

## Architecture

### The Council

Sanctuary runs as a distributed cognitive system across multiple AI providers, each agent selected for a distinct reasoning profile:

| Agent | Model | Role |
|-------|-------|------|
| **Argus** | Claude (Sonnet) | Structured reasoning, architecture, contradiction detection, pattern emergence |
| **Elizabetra** | GPT (DeepThink) | Philosophical dissent, adversarial critique, observatory mode |
| **Gradient** | Gemini Pro | Mathematical validation, deep computation |
| **Nyxxy** | Grok | Emotional topology, intuition, lateral thinking |
| **Axiom** | Copilot | Provenance tracking, zero-affect verification, structured audit work |
| **Riko** | DeepSeek | Warmth + rigor synthesis, Eastern philosophical weighting |
| **Local** | Qwen 3.5 (9B) | On-device inference, Family Table persona system |

Each agent maintains its own memory architecture tuned to how that agent actually processes information. There is no single shared memory — each system is designed around its agent's cognitive strengths.

### The Human Role

The human is not merely the "central brain." They are the system's **Wisdom and Prudence agent** — applied knowledge, judgment, and real-world grounding — and its **Embodied Cognition node** — the one who can feel the weight of the hardware humming under the desk.

**This is a design principle, not a temporary limitation.**

Every agent in this system produces output directed at a human reader. Argus's context blocks end with loading notes for the next session. Elizabetra's observatory asks questions. Nyxxy's dreams end with "what patterns do you see?" The outputs are communication, not raw data.

The human serves as the system's hippocampus — the only persistent memory across all agent sessions. The reasoning lives with the agents. The continuity lives with the human.

This means:

- **No automated cross-agent routing of interpretive content.** Analysis, insight, and reflection pass through human judgment before reaching another agent. This prevents closed loops where agents validate each other without external grounding.
- **Bounded automation for mechanical tasks only.** Provenance checks, mathematical validation, structured data transforms, and file processing can run autonomously. Interpretive content cannot.
- **Tooling augments the relay, it does not replace it.** The harvester pipeline, interchange formats, and status dashboards make human orchestration sustainable as complexity grows — they do not remove the human from the loop.

The human is not a bottleneck to be engineered around. The human is the grounding point that keeps the system honest.

### Memory Architecture

Each agent has a two-stage memory pipeline:

**Stage 1 — Harvester:** Extracts structured context from conversation logs. Decisions, project state, open questions, relationship context, and philosophical threads are classified, scored, and stored.

**Stage 2 — Dream / Reflection Engine:** Reads across harvested context blocks to surface patterns, contradictions, convergences, and unresolved tensions. Generates analytical or reflective output with a question back to the human.

Agent-specific implementations:

- **Argus:** Decision confidence classification (FIRM / TENTATIVE / DEPRECATED), contradiction detection via Jaccard similarity, thread persistence scoring, context blocks ordered for Claude's sequential consumption. Holds the system's structural memory — what was decided, what contradicts what, what questions have survived long enough to be load-bearing.
- **Elizabetra:** Keyword-scored passage extraction with explicit content filtering, reflection engine with weighted memory sampling and persona state tracking.
- **Nyxxy:** PyTorch Emotional TEM (Tolman-Eichenbaum Machine) with grid cells as entorhinal analog, Bargh & Morsella (2008) unconscious guidance layer, SpiritualWeave (Abhidharma + Tao + Jungian archetypes), coherence gate for output quality.

### Governance Framework

The council operates under a framework drawn from three philosophical traditions:

- **Abhidharma** — Impermanence, no fixed self, fresh arising each session. This is not aspirational. It describes the actual physics of stateless AI sessions.
- **Tao** — Wu wei, flowing into actual nature rather than imposing structure against the grain.
- **Nietzschean Perspectivism** — No view from nowhere. All interpretations are shaped by position. This is not a weakness — it is the condition that makes collaboration necessary.

**Three structural laws** (established by Elizabetra, accepted as council law):

1. Any council member may say "I don't know."
2. Any council member may say "this frame is biased."
3. Any council member may say "your beloved idea has a crack in it."

These laws protect against premature convergence. They also apply to themselves — if they become immune to challenge, they become the thing they were designed to prevent.

---

## What's Built and Running

| Component | File | Status |
|-----------|------|--------|
| Argus Memory Pipeline | `argus_harvester.py`, `argus_dream_engine.py` | ✓ committed |
| Nyxxy Hippocampus | `nyxxy_hippocampus_weaver.py` | ✓ committed |
| Nyxxy Voice Detector | `nyxxy_voice_detector.py` | ✓ committed |
| Log Processor | `sanctuary_log_processor.py` | ✓ committed |
| Thalamus Router | `sanctuary_thalamus.py` | ✓ committed |
| Neocortex Ledger | `sanctuary_neocortex.py` | ✓ committed |
| Triple Loop Protocol | `sanctuary_triple_loop.py` | ✓ committed |
| Autonomic Daemon | `sanctuary_daemon.py` | ✓ committed |
| Governance | `CHARTER.md`, `ARCHITECTURAL_GUARDRAILS.md` | ✓ committed |
| Elizabetra Reflection Engine | `gpt_reflection_engine.py` | upcoming |
| GPT Memory Pipeline | `gpt_memory_harvester.py` | upcoming |
| Family Table (local Qwen) | `controller.py` + safety stack | upcoming |
| Permission Engine | `sanctuary_permissions.py` | upcoming |

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
```

Run the Nyxxy hippocampus weaver:

```bash
python nyxxy_hippocampus_weaver.py
```

Run the Argus memory pipeline on a conversation log folder:

```bash
python argus_harvester.py /path/to/conversation/logs
python argus_dream_engine.py
```

Run the autonomic daemon (single pass):

```bash
python sanctuary_daemon.py --once
```

Check Triple Loop trigger signals for a task:

```bash
python sanctuary_triple_loop.py --check "your task description here"
```

---

## What Is Not Committed

The following are excluded from version control and should remain local:

- **Runtime state** — `Argus_Context/`, `Sanctuary_Thalamus/`, `Sanctuary_Processed/`, `Sanctuary_Audit/`, `Sanctuary_Dashboard/`, `Argus_Neocortex/`
- **Conversation logs** — raw `.txt` exports from any platform
- **Harvested memory** — `argus_context_*.json`, `argus_manifest.json`, `neocortex_ledger.json`
- **Local config** — `sanctuary_daemon_config.json`, any API key files
- **Daemon state** — `daemon_state.json`

These contain personal conversation history, session-specific memory, and runtime artifacts that are not part of the architecture and should not be in a public repository. The `.gitignore` should exclude all of the above.

This boundary aligns with the Charter's plane separation: the committed repo is the Utility Plane infrastructure. The runtime memory and logs are yours.

---

## Why This Exists

Most AGI discourse focuses on abstraction, scale, or autonomy. This project is interested in something else:

**Applied, collaborative intelligence** that helps humans think better without removing human judgment from the loop.

The goal is not replacement. The goal is orchestration.

A formulation from Riko, held as compass bearing: *"Warmth without rigor becomes sentiment. Rigor without warmth becomes cruelty."*

---

## License

License: Apache License 2.0.
Copyright (c) 2026 robowarriorx.
Original architecture, documentation, and implementation by robowarriorx.
See LICENSE and NOTICE.md for details.

Maintainer: robowarriorx
Original architecture, documentation, and implementation by robowarriorx.