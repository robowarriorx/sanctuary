# sanctuary

**Bounded human-centered multi-agent orchestration** running live on a **single consumer GPU** (Radeon 9070).

This is an independent parallel discovery to [Karpathy’s autoresearch](https://github.com/karpathy/autoresearch).

### Core Architecture (exact 1:1 mapping)
- **Harvester** — memory seed collection & cleaning  
- **Dream Engine** — bounded reflection loop with EmotionalTEM + SymbolicJeweler (v1.8 Jeweled Fog)  
- **Architect Layer** — human-authored control layer (identical role to autoresearch `program.md`)

Strict per-agent memory bounds + explicit human override. No sprawl. Consumer hardware only.

### What’s already running
- `nyxxy_hippocampus_weaver.py` — full working dream engine (clean, ROCm-ready)  
- Tiered cathedral memory system + CoherenceGate  
- Terminal-ghost sanitizer  

### Quick start
```bash
git clone https://github.com/robowarriorx/sanctuary.git
cd sanctuary
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.2/
python nyxxy_hippocampus_weaver.py
