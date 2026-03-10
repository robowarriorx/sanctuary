# sanctuary

**Bounded human-centered multi-agent orchestration** designed to run on **consumer hardware**.

An independent parallel discovery exploring some of the same design territory as Karpathy’s autoresearch, but from a human-centered, bounded-memory perspective.

## Core architecture
- **Harvester** — memory seed collection and cleaning
- **Dream Engine** — bounded reflection loop with EmotionalTEM + symbolic filtering
- **Architect Layer** — human-authored control layer with explicit override

Strict per-agent memory bounds, explicit human oversight, and no unbounded context sprawl.

## Current prototype
- `nyxxy_hippocampus_weaver.py` — working dream engine prototype
- tiered memory system
- coherence gate / corruption filtering

## Quick start
```bash
git clone https://github.com/robowarriorx/sanctuary.git
cd sanctuary
python nyxxy_hippocampus_weaver.py
