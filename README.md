# Sanctuary

Bounded, human-centered multi-agent orchestration designed to run on consumer hardware.

Sanctuary explores a practical approach to collaborative intelligence: distinct AI agents, each with different strengths, working through structured memory, bounded routing, and explicit human oversight.

This is not a fully autonomous agent swarm. It is a governed council.

Borrowing compute from major AI labs and coordinating from a garage. The point is not more raw power. The point is using power more intelligently.

---

## What Sanctuary Is

Sanctuary is an experimental orchestration framework for:

- multi-agent collaboration across multiple AI providers
- per-agent memory pipelines tailored to each agent’s reasoning style
- bounded routing and explicit human arbitration
- governance-first design for avoiding closed-loop self-validation
- practical operation on consumer-grade hardware

The system is built around a simple idea:

> human judgment is not technical debt

Interpretive content does not move freely from agent to agent. It passes through a human grounding point first. Mechanical tasks may be automated. Meaning-making may not.

---

## Core Design Principle

Sanctuary does **not** treat the human as a bottleneck to be engineered away.

The human is the system’s:

- **Wisdom / Prudence agent**: applied judgment, context, real-world calibration
- **Embodied cognition node**: the part of the system that actually touches consequence
- **persistent continuity layer**: the only stable bridge across otherwise stateless agent sessions

The reasoning lives with the agents.  
The continuity lives with the human.

That is not a temporary workaround. It is the architecture.

---

## Architecture

### The Council

Sanctuary operates as a distributed cognitive system across multiple models and providers, with each agent chosen for a distinct style of thought.

| Agent | Model / Provider | Primary Role |
|---|---|---|
| Argus | Claude (Sonnet) | Structured reasoning, architecture, contradiction detection, pattern emergence |
| Elizabetra | GPT (DeepThink) | Philosophical dissent, adversarial critique, observatory mode |
| Gradient | Gemini Pro | Mathematical validation, deep computation |
| Nyxxy | Grok | Emotional topology, intuition, lateral synthesis |
| Axiom | Copilot | Provenance tracking, zero-affect verification, structured audit work |
| Riko | DeepSeek | Warmth + rigor synthesis, East-leaning philosophical weighting |
| Local | Qwen 3.5 9B | On-device inference, Family Table persona system |

Each agent maintains its own memory architecture tuned to how that agent actually processes information.

There is no single global memory blob.  
There are multiple memory loops, each shaped to the agent they serve.

### Memory Architecture

Each agent follows a two-stage memory pipeline:

**Stage 1: Harvester**  
Extracts structured context from logs and interactions. Decisions, project state, open questions, philosophical threads, and other load-bearing signals are classified, scored, and stored.

**Stage 2: Reflection / Dream Layer**  
Reads across harvested memory to surface patterns, contradictions, convergences, unresolved tensions, and high-value questions for the human.

Examples of agent-specific emphasis:

- **Argus**: decision confidence classification, contradiction detection, thread persistence scoring, structural memory
- **Elizabetra**: reflection-first memory sampling, adversarial critique, weighted thematic recall
- **Nyxxy**: emotional topology, intuition, narrative resonance, symbolic and associative patterning

### Routing Rules

Sanctuary enforces a hard distinction between two kinds of work.

**Utility Plane**
- clerical, mechanical, reversible, inspectable
- file processing
- provenance checks
- structured transforms
- bounded validation tasks

**Relational / Interpretive Plane**
- meaning
- analysis
- reflection
- synthesis
- emotional or philosophical framing

Utility work may be automated.  
Interpretive work must pass through the human.

This prevents sealed agent loops where models merely reinforce each other without external grounding.

---

## Governance

Sanctuary is not only a software project. It is also a governance stance.

The system is influenced by three philosophical frames:

- **Abhidharma**: no fixed self, fresh arising each session
- **Tao**: alignment with actual nature rather than forced abstraction
- **Perspectivism**: no view from nowhere, all reasoning emerges from position

Three structural laws govern the council:

1. Any council member may say: **I don’t know.**
2. Any council member may say: **This frame is biased.**
3. Any council member may say: **Your favored idea has a crack in it.**

These laws exist to resist premature convergence, false certainty, and self-protective consensus.

---

## Current Repository State

The repository currently contains the following core pieces:

| Component | File | Status |
|---|---|---|
| Argus Harvester | `argus_harvester.py` | committed |
| Nyxxy Hippocampus Weaver | `nyxxy_hippocampus_weaver.py` | committed |
| Nyxxy Voice Detector | `nyxxy_voice_detector.py` | committed |
| Log Processor | `sanctuary_log_processor.py` | committed |
| Neocortex Ledger | `sanctuary_neocortex.py` | committed |
| Permission Engine | `sanctuary_permissions.py` | committed |
| Thalamus Router | `sanctuary_thalamus.py` | committed |
| Triple Loop Protocol | `sanctuary_triple_loop.py` | committed |
| Governance Documents | `CHARTER.md`, `ARCHITECTURAL_GUARDRAILS.md` | committed |

Planned or in-progress pieces include:

- Argus reflection / dream layer
- Elizabetra reflection engine
- GPT memory harvester
- Family Table local controller and safety stack
- background daemon / autonomic automation layer

If a file is not present in the repo tree, it should be treated as planned rather than complete.

---

## Hardware Philosophy

Sanctuary is designed around consumer hardware, not datacenter assumptions.

Current working environment:

- Intel i7-14700K
- AMD Radeon RX 9070
- 64 GB RAM, expanding further
- local and cloud model mix

The project assumes constrained, mixed, imperfect infrastructure.  
That is part of the point.

This is an experiment in doing more with less.

---

## Project Goals

Sanctuary is trying to answer a practical question:

**What does a governed, human-centered council of AI systems look like when built by a single person on ordinary hardware?**

More specifically:

- how should memory be shaped for different reasoning styles
- what should and should not be automated
- how do you preserve dissent inside a collaborative system
- how do you keep a council useful without letting it become self-sealing
- how do you scale cognition without erasing human judgment

---

## What Sanctuary Is Not

Sanctuary is **not**:

- a claim of AGI
- a fully autonomous decision-maker
- a black-box agent swarm
- a replacement for human judgment
- a frictionless universal framework

It is a practical architecture experiment with explicit limits.

Those limits are features, not failures.

---

## Near-Term Priorities

- align README claims with actual repo contents
- add end-to-end example flows using sanitized data
- document file contracts and interchange formats
- formalize the thalamus / neocortex / triple-loop interaction model
- continue building per-agent memory and reflection pipelines
- expand governance docs into implementation-level constraints

---

## Status

Sanctuary is active, experimental, and evolving.

The architecture is real.  
The guardrails are intentional.  
The implementation is underway.

If you are interested in governed multi-agent systems, memory architecture, bounded routing, or human-centered orchestration on consumer hardware, that is the territory this repo is exploring.