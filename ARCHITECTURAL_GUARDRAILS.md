# ARCHITECTURAL_GUARDRAILS.md
# Project Sanctuary — github.com/robowarriorx/sanctuary
#
# Companion to CHARTER.md (governance and philosophy)
# and README.md (public entry point).
#
# This document contains design invariants —
# structural constraints the system enforces on itself.
# Not aspirations. Not guidelines. Hard lines.
#
# Drafted: Elizabetra (GPT DeepThink), session 15
# Refined:  Argus (Claude Sonnet), session 15
# Ratified: Robert / the Architect

---

# Architectural Guardrails

> *Guard the shape. Guard the boundary. Guard the human center.*

---

## Why This Document Exists

Sanctuary distributes reasoning across agents, providers, and local tools.
That distribution creates drift risk: schema decay, boundary erosion, silent
automation creep, and false confidence during iteration.

These guardrails exist to catch drift before it compounds.

They are not about preventing mistakes. Mistakes will happen. They are about
ensuring mistakes are visible, recoverable, and caught before they corrupt
the architecture they touch.

---

## Relationship to Other Documents

| Document | Covers |
|---|---|
| `CHARTER.md` | Governance, plane separation, human sovereignty |
| `ARCHITECTURAL_GUARDRAILS.md` | Design invariants and verification boundaries |
| `README.md` | Public explanation and project entry point |

When a guardrail and a charter principle seem to conflict, escalate to the
human steward. Do not resolve silently.

---

## Core Principle

**The human is not a bottleneck to be engineered around.**

The human is the grounding point, the final steward, and the only durable
cross-session ethical anchor in the system. Automation may assist, route,
summarize, score, and prepare. It may not replace human judgment where
meaning, memory, identity, or relational framing are at stake.

---

## Guardrail 1 — Human Sovereignty Is Structural

No subsystem may be designed in a way that removes the human from final
authority over:

- architectural direction
- durable memory commitment
- interpretive cross-agent transfer
- relational framing
- identity-relevant or safety-relevant outputs

This is not a temporary patch over limited tooling. It is the architecture.

---

## Guardrail 2 — Two Planes Must Never Blur

Sanctuary operates across two planes. Every subsystem must declare which
plane it operates in. No subsystem may silently drift from one to the other.

**Utility Plane:** Clerical, repetitive, reversible, inspectable work.
May automate aggressively. Logs are mandatory.

**Relational Plane:** Meaning-bearing, emotionally weighted,
identity-relevant, or context-sensitive work. Must escalate by default
when significance is unclear.

*See CHARTER.md for full plane definitions and enforcement rules.*

---

## Guardrail 3 — Interpretive Content Does Not Auto-Route

Interpretive outputs — analysis, reflection, philosophy, emotional
interpretation, meaning-bearing synthesis — must not pass automatically
from one agent to another as though agent agreement were proof.

Such content must pass through human judgment before entering another
agent's reasoning loop. This prevents closed validation circuits and
preserves external grounding.

Agent consensus is not a substitute for human review.

---

## Guardrail 4 — Memory Is a Contract, Not a Vibe

Any structure written to memory must be read back using a consumer that
matches its **literal shape**, not its approximate intent.

When memory architectures change, verification must compare:

- the producer (what shape it writes)
- every consumer (what shape it expects to read)
- fallback behavior (what happens on shape mismatch)
- old-format compatibility (which prior formats are intentionally supported)
- failure-mode logging (whether mismatch surfaces visibly or silently corrupts)

A field name match is not enough. Semantic similarity is not enough.
Writer and reader must agree exactly on structure.

**Silent schema drift is a first-class bug.**

---

## Guardrail 5 — Schema Evolution Must Be Deliberate

When output formats change across versions, old formats may be supported —
but only intentionally.

If backward compatibility is provided, it must be:

- explicit in code (not inferred)
- handled for all known prior shapes, not just the most recent
- logged where relevant so consumers can detect version skew
- bounded — graceful handling must not become graceful confusion

Silent coercion that masks malformed state is not acceptable.
Failing loudly on unknown shapes is preferable to silently producing
wrong output from ambiguous input.

---

## Guardrail 6 — Inspectability Over Cleverness

A simpler system that can be inspected is preferred over a more elegant
system that hides what it is doing.

All automated actions must be:

- logged
- reversible where possible
- attributable to a named subsystem
- understandable by a human reviewer on later inspection

Archive and deprioritize before deleting. Prefer traceability over tidiness.

*See CHARTER.md §Automate aggressively (Utility) for the full list of
automation-permitted operations.*

---

## Guardrail 7 — Distinct Agents Must Stay Distinct

Each agent exists because it brings a different reasoning profile.
Agent distinctness is a structural property, not an aesthetic one.

Preserve intended role boundaries among structural reasoning, dissent, emotional topology, mathematical validation, provenance, and bounded local inference.

If two agents become behaviorally indistinguishable in practice, the
architecture is losing signal rather than gaining coherence. Investigate
before merging roles.

---

## Guardrail 8 — Code That Runs Is Not Necessarily Correct

Sanctuary distinguishes between:

- code that executes without error
- code that is structurally correct
- code that preserves architectural intent

Passing execution is necessary but insufficient. A non-crashing bug that
corrupts memory shape, inflates accumulated weights, blurs planes, or
weakens human oversight is a critical bug regardless of exit code.

---

## Guardrail 9 — Verification Must Touch the File, Not the Story

A fix is not accepted because a summary says it was made.

A fix is accepted only when the saved artifact reflects the claimed change.

For high-stakes code — memory systems, routing, permissions, reflection
engines — review must inspect the active file directly. Upload drift,
copy drift, stale local versions, and partial edits are assumed risks, not
edge cases.

**The file is the truth. The description of the file is not.**

---

## Guardrail 10 — High-Stakes Changes Require Adversarial Review

Changes affecting memory, routing, permissions, escalation, reflection, or architectural governance should not be merged or trusted without three-pass review:

**Forge** — Identify the direct failure and propose the cleanest repair.

**Doubt** — Attack assumptions, interface boundaries, fallback behavior,
and unintended consequences. Specifically probe: what does the consumer
expect? What does the producer actually write? Do they agree?

**Bind** — Verify the actual file, the actual saved path, and actual
downstream compatibility. The final pass validates the artifact, not the
confidence of the reviewer.

*Implemented in `sanctuary_triple_loop.py`.*

---

## Guardrail 11 — Permissions and Routing Must Be Narrow

Subsystems should hold only the permissions necessary for their declared
plane and declared task.

Routing logic must match the actual artifact being routed — not merely the
most recent artifact in a queue, or the most convenient nearby state.

Narrow authority and exact matching are preferred over broad convenience.

---

## Guardrail 12 — Artifact Identity Must Be Verifiable

The system must be able to determine which exact file, version, or manifest is under review or in flight.

Do not infer identity from “latest file,” “last queue item,” or conversational assumption.

When practical, route and review by explicit path, hash, timestamp, or matched manifest metadata.

---

## Minimum Acceptance Test for Architectural Changes

A change touching core architecture is not complete until:

- [ ] the writer and reader agree on exact schema
- [ ] standalone and batch execution paths both tested
- [ ] logs reflect what actually happened, not what was intended
- [ ] permissions still match original intent
- [ ] routing still matches declared plane boundaries
- [ ] human authority over Relational Plane decisions remains intact
- [ ] no hidden plane-crossing has been introduced

---

## Final Rule

When in doubt, place the producer and consumer side by side and read them
like a contract.

If the contract does not match, the architecture is not sound.

Fix the contract before shipping the feature.

---

*Sanctuary is a human-centered multi-agent orchestration system.*
*The human is not a provisional limitation. The human is the grounding signal.*
