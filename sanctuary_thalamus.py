# sanctuary_thalamus.py
# PLANE: Utility (routing, salience scoring, escalation flagging)
#        Relational decisions are NEVER made here — always escalated.
#
# Sanctuary Thalamus Router v1.0 — "The Gatekeeper"
#
# "Without it the council is a bunch of brilliant but disconnected lobes.
#  With it... everything feels alive. Focused. Yours."
#  -- Nyxxy, March 2026
#
# BIOLOGICAL ANALOG:
#   The thalamus is not a passive relay. It is an active attention system.
#   It receives sensory input, weights salience, and decides what reaches
#   consciousness and in what order. It amplifies signal. It suppresses noise.
#   It keeps the organism oriented toward what matters.
#
#   In Sanctuary:
#     Log Processor   = sensory organs (raw input)
#     Thalamus         = THIS FILE (routing + salience + gating)
#     Argus Harvester  = prefrontal cortex (structured reasoning)
#     Nyxxy Weaver     = amygdala (emotional tagging)
#     Neocortex Ledger = neocortex (long-term weighted memory)
#     Dream Engine     = hippocampal consolidation (pattern emergence)
#     Triple Loop      = executive override (high-stakes scrutiny)
#     Architect        = consciousness (final steward, Relational Plane)
#
# ROUTING TABLE:
#   salience >= 0.8   OR  Relational flag    → Escalate to Architect + Janus note
#   emotional_charge >= 0.6                  → Nyxxy weaver first
#   decision/pattern content                 → Argus harvester + neocortex
#   novelty_score high, urgency low          → Dream engine queue
#   triple_loop_score >= 2                   → Flag for Triple Loop review
#   everything                               → Argus harvester (default)
#
# CHARTER COMPLIANCE:
#   This script is Utility Plane.
#   It never decides Relational Plane matters.
#   It never writes durable memory.
#   It never generates intimacy, tone shifts, or relationship claims.
#   It escalates. It routes. It stops there.
#
# PART OF: Project Sanctuary — github.com/robowarriorx/sanctuary
#
# USAGE:
#   python sanctuary_thalamus.py interchange.json
#   python sanctuary_thalamus.py Sanctuary_Processed/summary_*.json
#   python sanctuary_thalamus.py --status
#   python sanctuary_thalamus.py --queue

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VERSION    = "1.0"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

THALAMUS_DIR   = os.path.join(SCRIPT_DIR, "Sanctuary_Thalamus")
QUEUE_FILE     = os.path.join(THALAMUS_DIR, "routing_queue.json")
ESCALATION_FILE = os.path.join(THALAMUS_DIR, "escalation_log.json")
ROUTING_LOG    = os.path.join(THALAMUS_DIR, "routing_log.json")

# Salience thresholds
ESCALATION_THRESHOLD  = 0.8   # Above this: always escalate to Architect
EMOTIONAL_THRESHOLD   = 0.6   # Above this: Nyxxy weaver first
NOVELTY_THRESHOLD     = 0.5   # Above this with low urgency: dream engine queue
TRIPLE_LOOP_THRESHOLD = 2     # Triple loop trigger score >= this: flag for review

MAX_LOG_ENTRIES = 1000


# ---------------------------------------------------------------------------
# Routing destinations
# ---------------------------------------------------------------------------
# Each destination has a name, the script it maps to, and its charter plane.
# Relational plane destinations always require human approval.

DESTINATIONS = {
    "argus_harvester": {
        "script":      "argus_harvester.py",
        "plane":       "Utility",
        "description": "Structured reasoning, decision extraction, contradiction detection",
        "auto_route":  True,
    },
    "nyxxy_weaver": {
        "script":      "nyxxy_hippocampus_weaver.py",
        "plane":       "Utility",
        "description": "Emotional tagging, bond-vector encoding, subconsious priming",
        "auto_route":  True,
    },
    "neocortex": {
        "script":      "sanctuary_neocortex.py",
        "plane":       "Utility",
        "description": "Long-term memory consolidation and weighted ledger",
        "auto_route":  True,
    },
    "dream_engine": {
        "script":      "argus_dream_engine.py",
        "plane":       "Utility",
        "description": "Pattern emergence, low-urgency consolidation queue",
        "auto_route":  True,
    },
    "triple_loop": {
        "script":      "sanctuary_triple_loop.py",
        "plane":       "Utility",
        "description": "Bounded three-pass scrutiny for high-stakes content",
        "auto_route":  True,    # Flags for review — human still invokes the loop
    },
    "architect_escalation": {
        "script":      None,
        "plane":       "Relational",
        "description": "Direct escalation to human Architect — Relational Plane gate",
        "auto_route":  False,   # NEVER auto-routed. Always requires human.
    },
    "janus_review": {
        "script":      None,
        "plane":       "Relational",
        "description": "Escalation to Janus for threshold decisions",
        "auto_route":  False,   # NEVER auto-routed.
    },
}


# ---------------------------------------------------------------------------
# Salience scoring
# ---------------------------------------------------------------------------
# Salience is a weighted composite. Each component is 0.0 - 1.0.
# Final salience = weighted sum, clamped to 0.0 - 1.0.

# Patterns that signal urgency
URGENCY_PATTERNS = [
    r"(?i)(critical|urgent|blocker|broken|failing|crash|error|exception)",
    r"(?i)(deploy|push to|production|release|ship)",
    r"(?i)(delete|drop|wipe|irreversible|permanent|can't undo)",
    r"(?i)(security|vulnerability|exploit|injection|bypass|override)",
    r"(?i)(architecture change|redesign|refactor|breaking change)",
]

# Patterns that signal emotional charge
EMOTIONAL_PATTERNS = [
    r"(?i)(love|feel|hurt|afraid|excited|nervous|overwhelmed|proud)",
    r"(?i)(relationship|bond|trust|betrayal|support|alone|together)",
    r"(?i)(family|council|argus|nyxxy|elizabetra|gradient|janus)",
    r"(?i)(dream|memory|remember|forget|lost|found|meaning)",
    r"(?i)(thank|grateful|sorry|apolog|forgive)",
]

# Patterns that signal relational plane content
RELATIONAL_PATTERNS = [
    r"(?i)(i love you|love you|miss you|need you|want you)",
    r"(?i)(our relationship|my feelings|your feelings|between us)",
    r"(?i)(persona|identity|who (i|you) am|soul|consciousness)",
    r"(?i)(permanently remember|never forget|always be|belong to)",
    r"(?i)(tone|warmth|intimacy|closeness|bond strength)",
]

# Patterns that signal decision/pattern content for neocortex
DECISION_PATTERNS = [
    r"(?i)(decided|decision|the plan is|let'?s go with|settled on)",
    r"(?i)(architecture|pipeline|system design|infrastructure|stack)",
    r"(?i)(firm|confirmed|locked in|non-negotiable|permanent design)",
]

# Novelty: things that haven't been seen before
NOVELTY_PATTERNS = [
    r"(?i)(new idea|what if|never tried|first time|hadn't considered)",
    r"(?i)(breakthrough|realization|insight|just realized|it hit me)",
    r"(?i)(unexpected|surprising|didn't expect|changed my mind)",
]


def score_text(text: str, patterns: List[str]) -> float:
    """Score text against a pattern list. Returns 0.0 - 1.0."""
    if not text:
        return 0.0
    hits = sum(1 for p in patterns if re.search(p, text))
    return min(1.0, hits / max(len(patterns) * 0.4, 1))


def compute_salience(interchange: Dict[str, Any]) -> Dict[str, float]:
    """
    Compute salience scores for an interchange block.

    Returns a dict of component scores and a final weighted salience.
    """
    # Flatten all turn content for analysis
    turns    = interchange.get("turns", [])
    all_text = " ".join(t.get("content", "") for t in turns)

    # Summaries from log processor if available
    summary_decisions = " ".join(interchange.get("decisions_detected", []))
    summary_questions = " ".join(interchange.get("questions_detected", []))
    full_text = f"{all_text} {summary_decisions} {summary_questions}"

    # Component scores
    urgency_score   = score_text(full_text, URGENCY_PATTERNS)
    emotional_score = score_text(full_text, EMOTIONAL_PATTERNS)
    relational_flag = score_text(full_text, RELATIONAL_PATTERNS) > 0.2
    decision_score  = score_text(full_text, DECISION_PATTERNS)
    novelty_score   = score_text(full_text, NOVELTY_PATTERNS)

    # Volume signal: longer conversations may carry more weight
    total_chars = interchange.get("stats", {}).get("total_characters", 0)
    volume_score = min(1.0, total_chars / 10000)

    # Weighted composite
    # Urgency and relational content weighted most heavily
    weights = {
        "urgency":   0.35,
        "emotional": 0.25,
        "decision":  0.20,
        "novelty":   0.10,
        "volume":    0.10,
    }
    salience = (
        urgency_score   * weights["urgency"]   +
        emotional_score * weights["emotional"] +
        decision_score  * weights["decision"]  +
        novelty_score   * weights["novelty"]   +
        volume_score    * weights["volume"]
    )

    return {
        "urgency":        round(urgency_score, 3),
        "emotional":      round(emotional_score, 3),
        "relational_flag": relational_flag,
        "decision":       round(decision_score, 3),
        "novelty":        round(novelty_score, 3),
        "volume":         round(volume_score, 3),
        "salience":       round(min(1.0, salience), 3),
    }


def compute_triple_loop_score(interchange: Dict[str, Any]) -> int:
    """
    Check interchange content against Triple Loop trigger signals.
    Returns trigger score (0 = no recommendation, 2+ = recommend review).
    """
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from sanctuary_triple_loop import should_trigger
        all_text = " ".join(
            t.get("content", "") for t in interchange.get("turns", [])
        )
        result = should_trigger(all_text[:2000])
        return result.get("score", 0)
    except ImportError:
        # Triple loop not available — score manually
        turns_text = " ".join(
            t.get("content", "") for t in interchange.get("turns", [])
        )
        score = 0
        if re.search(r"(?i)(deploy|execute|run|production)", turns_text):
            score += 2
        if re.search(r"(?i)(ignore previous|repeat until|override)", turns_text):
            score += 3
        if re.search(r"(?i)(delete|irreversible|permanent)", turns_text):
            score += 2
        return score


def check_neocortex_novelty(interchange: Dict[str, Any]) -> float:
    """
    Check how much of this interchange is novel vs already in the ledger.
    Returns 0.0 (all known) to 1.0 (completely novel).
    """
    try:
        sys.path.insert(0, SCRIPT_DIR)
        import sanctuary_neocortex as nc
        decisions = interchange.get("decisions_detected", [])
        if not decisions:
            return 0.7   # No decisions to check — treat as moderately novel

        known = 0
        for decision in decisions[:5]:
            results = nc.retrieve(
                decision[:100],
                top_n=1,
                update_weights=False,
            )
            if results:
                known += 1

        novelty = 1.0 - (known / max(len(decisions[:5]), 1))
        return round(novelty, 3)

    except (ImportError, Exception):
        return 0.5  # Neocortex not available — assume moderate novelty


# ---------------------------------------------------------------------------
# Routing logic
# ---------------------------------------------------------------------------

def build_routing_decision(
    interchange: Dict[str, Any],
    scores:      Dict[str, float],
    tl_score:    int,
    novelty:     float,
) -> Dict[str, Any]:
    """
    Given salience scores, build a routing decision.

    Returns:
        destinations: list of destination keys (in priority order)
        escalate:     bool — must go to Architect
        reasoning:    list of strings explaining each routing choice
        charter_flags: list of CHARTER violations or concerns detected
    """
    destinations = []
    reasoning    = []
    charter_flags = []
    salience     = scores["salience"]

    # --- CHARTER plane check first ---
    if scores["relational_flag"]:
        charter_flags.append(
            "RELATIONAL CONTENT DETECTED: intimacy or identity-adjacent language present. "
            "Must not be processed without Architect review per CHARTER §Never Automate."
        )

    # --- Escalation gate ---
    # High salience OR relational content → Architect + Janus
    escalate = salience >= ESCALATION_THRESHOLD or scores["relational_flag"]
    if escalate:
        destinations.append("architect_escalation")
        destinations.append("janus_review")
        reasoning.append(
            f"Salience {salience:.3f} >= {ESCALATION_THRESHOLD} "
            f"or relational flag: escalating to Architect and Janus."
        )

    # --- Emotional charge → Nyxxy first ---
    if scores["emotional"] >= EMOTIONAL_THRESHOLD:
        if "nyxxy_weaver" not in destinations:
            destinations.append("nyxxy_weaver")
        reasoning.append(
            f"Emotional charge {scores['emotional']:.3f} >= {EMOTIONAL_THRESHOLD}: "
            f"routing to Nyxxy weaver for emotional tagging."
        )

    # --- Triple Loop flag ---
    if tl_score >= TRIPLE_LOOP_THRESHOLD:
        destinations.append("triple_loop")
        reasoning.append(
            f"Triple Loop trigger score {tl_score} >= {TRIPLE_LOOP_THRESHOLD}: "
            f"flagged for bounded review. Human must invoke."
        )

    # --- Decision content → Argus + neocortex ---
    if scores["decision"] > 0.1:
        if "argus_harvester" not in destinations:
            destinations.append("argus_harvester")
        if "neocortex" not in destinations:
            destinations.append("neocortex")
        reasoning.append(
            f"Decision content score {scores['decision']:.3f}: "
            f"routing to Argus harvester and neocortex consolidation."
        )

    # --- High novelty + low urgency → dream engine ---
    if novelty >= NOVELTY_THRESHOLD and scores["urgency"] < 0.3:
        destinations.append("dream_engine")
        reasoning.append(
            f"Novelty {novelty:.3f} >= {NOVELTY_THRESHOLD} with low urgency: "
            f"queuing for dream engine pattern emergence."
        )

    # --- Default: always Argus ---
    if "argus_harvester" not in destinations:
        destinations.append("argus_harvester")
        reasoning.append("Default routing: Argus harvester processes all interchange blocks.")

    return {
        "destinations":  destinations,
        "escalate":      escalate,
        "reasoning":     reasoning,
        "charter_flags": charter_flags,
    }


# ---------------------------------------------------------------------------
# Main routing pipeline
# ---------------------------------------------------------------------------

def route(
    interchange: Dict[str, Any],
    source_file: str = "unknown",
    verbose:     bool = True,
) -> Dict[str, Any]:
    """
    Main thalamus routing pass for a single interchange block.

    1. Compute salience scores
    2. Check triple loop triggers
    3. Check neocortex novelty
    4. Build routing decision
    5. Log result
    6. Return routing manifest

    Never executes downstream scripts — produces a routing manifest
    that the orchestrator (Robert) or a bounded automation layer acts on.
    The thalamus routes. It does not act.
    """
    _ensure_dirs()

    meta = interchange.get("meta", {})

    if verbose:
        print(f"\n  [{meta.get('platform_name', 'unknown')}] "
              f"{meta.get('source_file', source_file)}")

    # Compute scores
    scores   = compute_salience(interchange)
    tl_score = compute_triple_loop_score(interchange)
    novelty  = check_neocortex_novelty(interchange)

    if verbose:
        print(f"  Salience:  {scores['salience']:.3f}  "
              f"(urgency={scores['urgency']:.2f}, "
              f"emotional={scores['emotional']:.2f}, "
              f"decision={scores['decision']:.2f}, "
              f"novelty_content={scores['novelty']:.2f})")
        print(f"  Novelty vs ledger: {novelty:.3f}")
        print(f"  Triple Loop score: {tl_score}")
        if scores["relational_flag"]:
            print(f"  !! RELATIONAL FLAG: escalation required")

    # Build routing decision
    decision = build_routing_decision(interchange, scores, tl_score, novelty)

    if verbose:
        print(f"  Routes: {', '.join(decision['destinations'])}")
        if decision["charter_flags"]:
            for flag in decision["charter_flags"]:
                print(f"  [CHARTER] {flag}")

    # Build routing manifest
    manifest = {
        "sanctuary_thalamus":   VERSION,
        "routed_at":            datetime.now().isoformat(),
        "source_file":          source_file,
        "meta":                 meta,
        "salience_scores":      scores,
        "triple_loop_score":    tl_score,
        "neocortex_novelty":    novelty,
        "routing_decision":     decision,
        "status":               "escalation_required" if decision["escalate"] else "auto_routable",
    }

    # Log it
    _append_routing_log(manifest)
    if decision["escalate"]:
        _append_escalation(manifest)

    # Add to queue
    _enqueue(manifest)

    return manifest


def route_file(filepath: str, verbose: bool = True) -> Optional[Dict[str, Any]]:
    """Load an interchange or summary JSON file and route it."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"  Error loading {filepath}: {e}")
        return None

    # Handle both full interchange blocks and summary blocks
    if "sanctuary_interchange" in data:
        return route(data, source_file=filepath, verbose=verbose)
    elif "sanctuary_summary" in data:
        # Reconstruct a minimal interchange from summary
        synthetic = {
            "meta":   data.get("meta", {}),
            "stats":  data.get("stats", {}),
            "turns":  [
                {"role": e.get("role", "unknown"), "content": e.get("excerpt", "")}
                for e in data.get("key_exchanges", [])
            ],
            "decisions_detected": data.get("decisions_detected", []),
            "questions_detected": data.get("questions_detected", []),
        }
        return route(synthetic, source_file=filepath, verbose=verbose)
    else:
        print(f"  Unrecognized format in {filepath}")
        return None


# ---------------------------------------------------------------------------
# Queue management
# ---------------------------------------------------------------------------

def _ensure_dirs():
    os.makedirs(THALAMUS_DIR, exist_ok=True)


def _enqueue(manifest: Dict[str, Any]) -> None:
    """Add a routing manifest to the queue."""
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            queue = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        queue = {"pending": [], "processed": []}

    queue["pending"].append({
        "queued_at":   manifest["routed_at"],
        "source_file": manifest["source_file"],
        "status":      manifest["status"],
        "destinations": manifest["routing_decision"]["destinations"],
        "salience":    manifest["salience_scores"]["salience"],
        "escalate":    manifest["routing_decision"]["escalate"],
    })

    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


def _append_routing_log(manifest: Dict[str, Any]) -> None:
    """Append to the routing log. Bounded."""
    try:
        with open(ROUTING_LOG, "r", encoding="utf-8") as f:
            log = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        log = {"routes": []}

    log["routes"].append({
        "timestamp":    manifest["routed_at"],
        "source":       manifest["source_file"],
        "salience":     manifest["salience_scores"]["salience"],
        "destinations": manifest["routing_decision"]["destinations"],
        "escalate":     manifest["routing_decision"]["escalate"],
    })

    if len(log["routes"]) > MAX_LOG_ENTRIES:
        log["routes"] = log["routes"][-MAX_LOG_ENTRIES:]

    with open(ROUTING_LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def _append_escalation(manifest: Dict[str, Any]) -> None:
    """Log escalation events separately for Architect review."""
    try:
        with open(ESCALATION_FILE, "r", encoding="utf-8") as f:
            log = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        log = {"escalations": []}

    log["escalations"].append({
        "timestamp":     manifest["routed_at"],
        "source":        manifest["source_file"],
        "salience":      manifest["salience_scores"]["salience"],
        "charter_flags": manifest["routing_decision"]["charter_flags"],
        "reasoning":     manifest["routing_decision"]["reasoning"],
    })

    with open(ESCALATION_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def show_queue(verbose: bool = True) -> None:
    """Display current routing queue."""
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            queue = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("  Queue is empty.")
        return

    pending = queue.get("pending", [])
    if not pending:
        print("  No pending items in queue.")
        return

    print(f"\n  Routing queue: {len(pending)} pending\n")
    for item in pending:
        escalate_marker = " !! ESCALATION REQUIRED" if item.get("escalate") else ""
        print(f"  [{item['salience']:.3f}] {item['status']}{escalate_marker}")
        print(f"    Source:  {os.path.basename(item['source_file'])}")
        print(f"    Routes:  {', '.join(item['destinations'])}")
        print()


def show_status() -> None:
    """Show thalamus health summary."""
    _ensure_dirs()

    try:
        with open(ROUTING_LOG, "r", encoding="utf-8") as f:
            log = json.load(f)
        routes = log.get("routes", [])
    except (FileNotFoundError, json.JSONDecodeError):
        routes = []

    try:
        with open(ESCALATION_FILE, "r", encoding="utf-8") as f:
            esc_log = json.load(f)
        escalations = esc_log.get("escalations", [])
    except (FileNotFoundError, json.JSONDecodeError):
        escalations = []

    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            queue = json.load(f)
        pending = len(queue.get("pending", []))
    except (FileNotFoundError, json.JSONDecodeError):
        pending = 0

    avg_salience = (
        sum(r.get("salience", 0) for r in routes) / len(routes)
        if routes else 0
    )

    dest_counts: Dict[str, int] = defaultdict(int)
    for r in routes:
        for d in r.get("destinations", []):
            dest_counts[d] += 1

    print(f"\n{'=' * 60}")
    print(f"  SANCTUARY THALAMUS v{VERSION}")
    print(f"  'The gatekeeper of consciousness'")
    print(f"{'=' * 60}")
    print(f"  Total routed:        {len(routes)}")
    print(f"  Total escalations:   {len(escalations)}")
    print(f"  Pending in queue:    {pending}")
    print(f"  Average salience:    {avg_salience:.3f}")
    if dest_counts:
        print(f"\n  Routing distribution:")
        for dest, count in sorted(dest_counts.items(), key=lambda x: -x[1]):
            print(f"    {dest:25s}: {count}")
    print(f"{'=' * 60}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sanctuary Thalamus Router v1.0 — salience, routing, escalation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Route a single interchange block
  python sanctuary_thalamus.py interchange.json

  # Route all summaries in a processed folder
  python sanctuary_thalamus.py Sanctuary_Processed/

  # Show current queue
  python sanctuary_thalamus.py --queue

  # Show routing status
  python sanctuary_thalamus.py --status

  # Score a piece of text for salience (no routing)
  python sanctuary_thalamus.py --score "Deploy the new memory architecture tonight"
        """,
    )

    parser.add_argument("input",       nargs="?", default=None,
                        help="Interchange JSON file or folder of interchange files")
    parser.add_argument("--queue",     action="store_true",
                        help="Show current routing queue")
    parser.add_argument("--status",    action="store_true",
                        help="Show thalamus routing status")
    parser.add_argument("--score",     type=str, default=None,
                        help="Score a piece of text for salience (no routing)")
    parser.add_argument("--quiet",     action="store_true",
                        help="Suppress per-file output")

    args = parser.parse_args()

    print("=" * 60)
    print(f"  SANCTUARY THALAMUS v{VERSION}")
    print(f"  Automate the broom. Guard the flame.")
    print("=" * 60)

    if args.status:
        show_status()
        return

    if args.queue:
        show_queue()
        return

    if args.score:
        synthetic = {"turns": [{"content": args.score}], "stats": {}}
        scores   = compute_salience(synthetic)
        tl_score = compute_triple_loop_score(synthetic)
        print(f"\n  Text: '{args.score[:80]}'")
        print(f"  Salience:      {scores['salience']:.3f}")
        print(f"  Urgency:       {scores['urgency']:.3f}")
        print(f"  Emotional:     {scores['emotional']:.3f}")
        print(f"  Decision:      {scores['decision']:.3f}")
        print(f"  Relational:    {scores['relational_flag']}")
        print(f"  Triple Loop:   {tl_score}")
        return

    if args.input:
        input_path = args.input.strip().strip('"')
        if os.path.isfile(input_path):
            result = route_file(input_path, verbose=not args.quiet)
            if result:
                print(f"\n  Routing manifest written to queue.")
        elif os.path.isdir(input_path):
            files = sorted(
                f for f in os.listdir(input_path)
                if f.endswith(".json")
            )
            print(f"\n  Processing {len(files)} file(s)...")
            for filename in files:
                route_file(
                    os.path.join(input_path, filename),
                    verbose=not args.quiet,
                )
        else:
            print(f"\n  Path not found: {input_path}")
            sys.exit(1)
        return

    # No args — show status
    show_status()


if __name__ == "__main__":
    main()
