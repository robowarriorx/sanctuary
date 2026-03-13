# sanctuary_neocortex.py
# Sanctuary Neocortex Ledger v1.0 -- "The Long Memory"
#
# "The filing cabinet retrieves exactly what was stored.
#  A living system retrieves a reconstruction influenced by
#  everything that has happened since." -- Janus, session 14
#
# This is the long-term memory layer for Project Sanctuary.
# The harvesters are the hippocampus -- session-level, fast, raw.
# The dream engine does primitive consolidation -- pattern recognition.
# This is the neocortex -- compressed, weighted, persistent, reconstructive.
#
# BIOLOGICAL ANALOG:
#   Encoding:      sanctuary_log_processor.py  (sensory input)
#   Hippocampus:   argus_harvester.py           (new memory formation)
#   Consolidation: argus_dream_engine.py        (sleep / pattern transfer)
#   Neocortex:     THIS FILE                    (long-term weighted store)
#   Amygdala:      nyxxy_hippocampus_weaver.py  (emotional tagging)
#
# DESIGN PRINCIPLES (Janus, session 14):
#   1. Archive and deprioritize. Never delete.
#      Raw context blocks move to cold storage after consolidation.
#      The ledger is the primary retrieval layer. Cold archive is auditable.
#   2. Reconstructive retrieval.
#      Accessing a memory updates it. Every retrieval appends context
#      from HOW it was used, not just THAT it was accessed.
#   3. Exponential decay, not deletion.
#      Entries below threshold move to subthreshold. Still queryable.
#      Noise fades. Signal persists through access.
#   4. Build order: Ledger → Consolidation → Decay → Retrieval hooks.
#      Reconstructive update comes last, after the others run for weeks.
#
# FILE STRUCTURE:
#   Argus_Neocortex/
#     neocortex_ledger.json       -- primary weighted ledger
#     neocortex_cold.json         -- subthreshold + archived raw context refs
#     neocortex_audit_log.json    -- every consolidation and retrieval event
#
# PART OF: Project Sanctuary -- github.com/robowarriorx/sanctuary
#
# USAGE:
#   python sanctuary_neocortex.py --consolidate    # Run consolidation pass
#   python sanctuary_neocortex.py --decay          # Run nightly decay
#   python sanctuary_neocortex.py --query "memory architecture"
#   python sanctuary_neocortex.py --audit          # Show recent events
#   python sanctuary_neocortex.py --status         # Ledger health summary

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VERSION = "1.0"

SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
NEOCORTEX_DIR  = os.path.join(SCRIPT_DIR, "Argus_Neocortex")
CONTEXT_DIR    = os.path.join(SCRIPT_DIR, "Argus_Context")
COLD_DIR       = os.path.join(NEOCORTEX_DIR, "cold_archive")

LEDGER_FILE    = os.path.join(NEOCORTEX_DIR, "neocortex_ledger.json")
COLD_FILE      = os.path.join(NEOCORTEX_DIR, "neocortex_cold.json")
AUDIT_FILE     = os.path.join(NEOCORTEX_DIR, "neocortex_audit_log.json")

# Weight thresholds
INITIAL_WEIGHT          = 1.0   # Starting weight for new ledger entries
DECAY_RATE              = 0.05  # Per-day exponential decay
SUBTHRESHOLD_CUTOFF     = 0.15  # Below this: move to subthreshold (not deleted)
RETRIEVAL_BOOST         = 0.25  # Weight boost when an entry is accessed
CONSOLIDATION_THRESHOLD = 2     # Minimum sessions a pattern must appear in

# Consolidation: how many dream cycles before a pattern earns a ledger entry
MIN_DREAM_CYCLES = 1   # For now: any dream output can consolidate
                        # Raise this after the system has been running for weeks

MAX_AUDIT_ENTRIES = 500  # Keep audit log bounded


# ---------------------------------------------------------------------------
# Ledger entry schema
# ---------------------------------------------------------------------------
# A ledger entry represents a consolidated, persistent piece of knowledge.
# It knows its own history: where it came from, how often it's been used,
# and what context each access added to its meaning.

def make_entry(
    content:        str,
    entry_type:     str,        # "decision", "pattern", "tension", "question", "insight"
    tags:           List[str],
    source_session: str,
    source_file:    str,
    confidence:     str = "TENTATIVE",   # FIRM / TENTATIVE
) -> Dict[str, Any]:
    return {
        "id":               _make_id(content),
        "content":          content,
        "type":             entry_type,
        "tags":             tags,
        "confidence":       confidence,
        "weight":           INITIAL_WEIGHT,
        "created_at":       datetime.now().isoformat(),
        "created_session":  source_session,
        "source_file":      source_file,
        "last_accessed":    None,
        "access_count":     0,
        "retrieval_history": [],  # Reconstructive layer: appended on each access
        "decay_log":        [],   # Record of decay events
        "consolidated_from": source_file,
    }


def _make_id(content: str) -> str:
    """Stable short ID from content hash."""
    import hashlib
    return hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Ledger I/O
# ---------------------------------------------------------------------------

def _ensure_dirs():
    os.makedirs(NEOCORTEX_DIR, exist_ok=True)
    os.makedirs(COLD_DIR, exist_ok=True)


def load_ledger() -> Dict[str, Any]:
    """Load the primary ledger. Returns empty structure if not yet created."""
    _ensure_dirs()
    try:
        with open(LEDGER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "sanctuary_neocortex": VERSION,
            "created_at": datetime.now().isoformat(),
            "last_decay": None,
            "last_consolidation": None,
            "entries": {},          # id -> entry dict
            "subthreshold": {},     # id -> entry dict (weight below cutoff)
            "stats": {
                "total_consolidated": 0,
                "total_decayed_to_cold": 0,
                "total_retrievals": 0,
            },
        }


def save_ledger(ledger: Dict[str, Any]) -> None:
    _ensure_dirs()
    with open(LEDGER_FILE, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)


def load_cold() -> Dict[str, Any]:
    """Load cold archive (subthreshold + raw context references)."""
    _ensure_dirs()
    try:
        with open(COLD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "sanctuary_neocortex_cold": VERSION,
            "entries": {},
            "archived_context_refs": [],  # Paths to raw context blocks moved cold
        }


def save_cold(cold: Dict[str, Any]) -> None:
    _ensure_dirs()
    with open(COLD_FILE, "w", encoding="utf-8") as f:
        json.dump(cold, f, indent=2, ensure_ascii=False)


def append_audit(event_type: str, detail: dict) -> None:
    """Append an event to the audit log. Keeps log bounded."""
    _ensure_dirs()
    try:
        with open(AUDIT_FILE, "r", encoding="utf-8") as f:
            log = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        log = {"events": []}

    log["events"].append({
        "timestamp":  datetime.now().isoformat(),
        "event_type": event_type,
        "detail":     detail,
    })

    # Keep bounded
    if len(log["events"]) > MAX_AUDIT_ENTRIES:
        log["events"] = log["events"][-MAX_AUDIT_ENTRIES:]

    with open(AUDIT_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Consolidation
# ---------------------------------------------------------------------------
# Reads harvester context blocks and dream engine output.
# Extracts patterns that have survived long enough to earn a ledger entry.
# Writes to ledger. Moves raw context to cold archive.

def load_context_blocks() -> List[Dict[str, Any]]:
    """Load all harvester context blocks, sorted chronologically."""
    blocks = []
    if not os.path.exists(CONTEXT_DIR):
        return blocks
    for filename in sorted(os.listdir(CONTEXT_DIR)):
        if filename.startswith("argus_context_") and filename.endswith(".json"):
            filepath = os.path.join(CONTEXT_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    block = json.load(f)
                    block["_filepath"] = filepath
                    block["_filename"] = filename
                    blocks.append(block)
            except (json.JSONDecodeError, IOError):
                continue
    return blocks


def extract_consolidation_candidates(
    blocks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Scan context blocks for content worth consolidating into the ledger.
    
    Candidates:
      - FIRM decisions (high confidence, appeared in multiple sessions)
      - Persistent questions (survived N sessions without resolution)
      - Elevated signal entries (multi-category hits in harvester)
      - Contradictions that were resolved
      - Theme patterns above recurrence threshold
    """
    candidates = []

    # Track what appeared across how many sessions
    decision_sessions:  Dict[str, List[str]] = defaultdict(list)
    question_sessions:  Dict[str, List[str]] = defaultdict(list)
    theme_sessions:     Dict[str, int]        = defaultdict(int)

    for block in blocks:
        session_id = block.get("_filename", "unknown")

        # --- FIRM decisions ---
        decisions = block.get("decisions", {})
        if isinstance(decisions, dict):
            for item in decisions.get("firm", []):
                decision_sessions[item].append(session_id)
        elif isinstance(decisions, list):
            for item in decisions:
                decision_sessions[item].append(session_id)

        # --- Persistent questions ---
        oq = block.get("open_questions", {})
        if isinstance(oq, dict):
            for q in oq.get("persistent", []):
                text = q["question"] if isinstance(q, dict) else q
                question_sessions[text].append(session_id)
        elif isinstance(oq, list):
            for q in oq:
                question_sessions[q].append(session_id)

        # --- Elevated signal ---
        for e in block.get("elevated_signal", []):
            line = e["line"] if isinstance(e, dict) else e
            candidates.append({
                "content":    line,
                "type":       "insight",
                "confidence": "TENTATIVE",
                "tags":       ["elevated_signal"],
                "session":    session_id,
                "source":     block.get("_filepath", ""),
            })

        # --- Theme accumulator ---
        for theme, weight in block.get("theme_accumulator", {}).items():
            theme_sessions[theme] += weight

    # Decisions that appeared in multiple sessions -> FIRM ledger entries
    for decision, sessions in decision_sessions.items():
        if len(sessions) >= CONSOLIDATION_THRESHOLD:
            candidates.append({
                "content":    decision,
                "type":       "decision",
                "confidence": "FIRM",
                "tags":       ["decision", "firm", "multi-session"],
                "session":    sessions[-1],
                "source":     sessions[0],
            })
        elif sessions:
            candidates.append({
                "content":    decision,
                "type":       "decision",
                "confidence": "TENTATIVE",
                "tags":       ["decision", "tentative"],
                "session":    sessions[-1],
                "source":     sessions[0],
            })

    # Persistent questions -> open thread entries
    for question, sessions in question_sessions.items():
        if sessions:
            candidates.append({
                "content":    question,
                "type":       "question",
                "confidence": "TENTATIVE",
                "tags":       ["open_question", "persistent"],
                "session":    sessions[-1],
                "source":     sessions[0],
            })

    # Strong themes -> pattern entries
    for theme, total_weight in theme_sessions.items():
        if total_weight >= CONSOLIDATION_THRESHOLD:
            candidates.append({
                "content":    f"Recurring architectural theme: {theme.replace('_', ' ')}",
                "type":       "pattern",
                "confidence": "TENTATIVE",
                "tags":       ["theme", theme],
                "session":    "multi-session",
                "source":     "theme_accumulator",
            })

    return candidates


def run_consolidation(
    archive_raw: bool = True,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Main consolidation pass.
    
    1. Load all context blocks
    2. Extract consolidation candidates
    3. Write new entries to ledger (skip duplicates by content hash)
    4. Optionally move raw context blocks to cold archive
    
    Returns summary of what was consolidated.
    """
    ledger    = load_ledger()
    cold      = load_cold()
    blocks    = load_context_blocks()

    if not blocks:
        if verbose:
            print("  No context blocks found. Run the harvester first.")
        return {"consolidated": 0, "skipped_duplicate": 0, "blocks_archived": 0}

    if verbose:
        print(f"  Loaded {len(blocks)} context block(s)")

    candidates = extract_consolidation_candidates(blocks)

    if verbose:
        print(f"  Candidates for consolidation: {len(candidates)}")

    new_count  = 0
    dup_count  = 0
    existing_ids = set(ledger["entries"].keys()) | set(ledger["subthreshold"].keys())

    for cand in candidates:
        content = cand["content"].strip()
        if not content or len(content) < 15:
            continue

        entry_id = _make_id(content)

        if entry_id in existing_ids:
            # Already in ledger — boost weight slightly (memory strengthening)
            if entry_id in ledger["entries"]:
                ledger["entries"][entry_id]["weight"] = min(
                    2.0, ledger["entries"][entry_id]["weight"] + 0.1
                )
            dup_count += 1
            continue

        entry = make_entry(
            content        = content,
            entry_type     = cand["type"],
            tags           = cand.get("tags", []),
            source_session = cand.get("session", "unknown"),
            source_file    = cand.get("source", "unknown"),
            confidence     = cand.get("confidence", "TENTATIVE"),
        )

        ledger["entries"][entry_id] = entry
        existing_ids.add(entry_id)
        new_count += 1

        if verbose:
            conf = cand.get("confidence", "?")
            print(f"  + [{conf:9s}] {content[:70]}")

    # Archive raw context blocks to cold storage
    archived_count = 0
    if archive_raw:
        for block in blocks:
            filepath = block.get("_filepath")
            if not filepath or not os.path.exists(filepath):
                continue
            # Move to cold directory
            dest = os.path.join(COLD_DIR, os.path.basename(filepath))
            try:
                os.rename(filepath, dest)
                cold["archived_context_refs"].append({
                    "original_path": filepath,
                    "cold_path":     dest,
                    "archived_at":   datetime.now().isoformat(),
                })
                archived_count += 1
            except OSError as e:
                if verbose:
                    print(f"  [WARN] Could not archive {filepath}: {e}")

    # Update ledger stats
    ledger["stats"]["total_consolidated"] += new_count
    ledger["last_consolidation"] = datetime.now().isoformat()

    save_ledger(ledger)
    save_cold(cold)

    summary = {
        "consolidated":      new_count,
        "skipped_duplicate": dup_count,
        "blocks_archived":   archived_count,
        "total_in_ledger":   len(ledger["entries"]),
    }

    append_audit("consolidation", summary)

    if verbose:
        print(f"\n  Consolidation complete:")
        print(f"    New entries:       {new_count}")
        print(f"    Duplicates (boosted): {dup_count}")
        print(f"    Raw blocks archived:  {archived_count}")
        print(f"    Total in ledger:   {len(ledger['entries'])}")

    return summary


# ---------------------------------------------------------------------------
# Decay
# ---------------------------------------------------------------------------
# Nightly exponential weight reduction.
# Below SUBTHRESHOLD_CUTOFF: move to subthreshold section.
# Never deleted. Always auditable.

def run_decay(verbose: bool = True) -> Dict[str, Any]:
    """
    Exponential decay pass. Designed to run nightly.
    
    weight_new = weight_old * e^(-decay_rate * days_since_last_decay)
    
    Entries below SUBTHRESHOLD_CUTOFF move to subthreshold.
    They are not deleted. They remain queryable via --audit.
    """
    ledger = load_ledger()

    last_decay_str = ledger.get("last_decay")
    now            = datetime.now()

    if last_decay_str:
        try:
            last_decay = datetime.fromisoformat(last_decay_str)
            days_elapsed = (now - last_decay).total_seconds() / 86400
        except ValueError:
            days_elapsed = 1.0
    else:
        days_elapsed = 1.0

    if days_elapsed < 0.5:
        if verbose:
            print(f"  Decay skipped: only {days_elapsed:.1f} days since last decay.")
        return {"skipped": True, "reason": "too_recent"}

    decay_factor = math.exp(-DECAY_RATE * days_elapsed)

    decayed_count    = 0
    to_subthreshold  = []

    for entry_id, entry in ledger["entries"].items():
        old_weight = entry["weight"]
        new_weight = old_weight * decay_factor

        # FIRM decisions decay more slowly
        if entry.get("confidence") == "FIRM":
            new_weight = old_weight * math.exp(-DECAY_RATE * 0.3 * days_elapsed)

        entry["weight"] = round(new_weight, 4)
        entry["decay_log"].append({
            "at":          now.isoformat(),
            "from_weight": round(old_weight, 4),
            "to_weight":   round(new_weight, 4),
            "days":        round(days_elapsed, 2),
        })
        decayed_count += 1

        if new_weight < SUBTHRESHOLD_CUTOFF:
            to_subthreshold.append(entry_id)

    # Move subthreshold entries
    for entry_id in to_subthreshold:
        entry = ledger["entries"].pop(entry_id)
        entry["moved_to_subthreshold_at"] = now.isoformat()
        ledger["subthreshold"][entry_id]  = entry

    ledger["last_decay"] = now.isoformat()
    ledger["stats"]["total_decayed_to_cold"] += len(to_subthreshold)

    save_ledger(ledger)

    summary = {
        "days_elapsed":         round(days_elapsed, 2),
        "decay_factor":         round(decay_factor, 4),
        "entries_decayed":      decayed_count,
        "moved_to_subthreshold": len(to_subthreshold),
        "active_remaining":     len(ledger["entries"]),
    }

    append_audit("decay", summary)

    if verbose:
        print(f"  Decay pass complete:")
        print(f"    Days elapsed:      {days_elapsed:.2f}")
        print(f"    Decay factor:      {decay_factor:.4f}")
        print(f"    Entries decayed:   {decayed_count}")
        print(f"    → Subthreshold:    {len(to_subthreshold)}")
        print(f"    Active remaining:  {len(ledger['entries'])}")

    return summary


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
# Query the ledger by tag, type, or text search.
# Every retrieval: boosts weight, appends retrieval context.
# This is the reconstructive layer -- accessing a memory updates it.

def retrieve(
    query:           str,
    top_n:           int  = 10,
    include_subthreshold: bool = False,
    retrieval_context: str = "",
    update_weights:  bool = True,
) -> List[Dict[str, Any]]:
    """
    Query the neocortex ledger.
    
    Searches content and tags by keyword.
    Returns entries sorted by weight (most significant first).
    
    Reconstructive: every retrieval boosts weight and appends context.
    Set update_weights=False for read-only queries (audit, inspection).
    """
    ledger  = load_ledger()
    query_l = query.lower()
    words   = set(re.findall(r'\b\w{3,}\b', query_l))

    def score_entry(entry: Dict) -> float:
        content_lower = entry["content"].lower()
        tag_text      = " ".join(entry.get("tags", [])).lower()
        full_text     = content_lower + " " + tag_text

        # Word overlap score
        entry_words = set(re.findall(r'\b\w{3,}\b', full_text))
        overlap     = len(words & entry_words) / max(len(words), 1)

        # Weight the relevance score by ledger weight
        return overlap * entry["weight"]

    # Search active entries
    candidates = list(ledger["entries"].values())
    if include_subthreshold:
        candidates += list(ledger["subthreshold"].values())

    scored = [
        (score_entry(e), e)
        for e in candidates
        if score_entry(e) > 0
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    results = [e for _, e in scored[:top_n]]

    # Reconstructive update: boost weights and append retrieval context
    if update_weights and results:
        now = datetime.now().isoformat()
        for entry in results:
            entry_id = entry["id"]
            if entry_id not in ledger["entries"]:
                continue

            ledger_entry = ledger["entries"][entry_id]
            ledger_entry["weight"] = min(
                2.0, ledger_entry["weight"] + RETRIEVAL_BOOST
            )
            ledger_entry["last_accessed"] = now
            ledger_entry["access_count"] += 1

            # Reconstructive layer: append retrieval context
            # "The memory evolves through use, not just persists or decays"
            if retrieval_context:
                ledger_entry["retrieval_history"].append({
                    "retrieved_at": now,
                    "query":        query[:200],
                    "context":      retrieval_context[:300],
                })

        ledger["stats"]["total_retrievals"] += len(results)
        save_ledger(ledger)

    return results


# ---------------------------------------------------------------------------
# Status and audit
# ---------------------------------------------------------------------------

def status(verbose: bool = True) -> Dict[str, Any]:
    """Print a health summary of the neocortex ledger."""
    ledger = load_ledger()
    cold   = load_cold()

    active_entries     = len(ledger["entries"])
    subthreshold       = len(ledger["subthreshold"])
    archived_raw       = len(cold.get("archived_context_refs", []))
    total_retrievals   = ledger["stats"].get("total_retrievals", 0)
    last_consolidation = ledger.get("last_consolidation", "never")
    last_decay         = ledger.get("last_decay", "never")

    # Weight distribution
    weights = [e["weight"] for e in ledger["entries"].values()]
    avg_weight = sum(weights) / len(weights) if weights else 0

    # Top 5 by weight
    top_entries = sorted(
        ledger["entries"].values(),
        key=lambda e: e["weight"],
        reverse=True
    )[:5]

    # Type breakdown
    type_counts: Dict[str, int] = defaultdict(int)
    for e in ledger["entries"].values():
        type_counts[e.get("type", "unknown")] += 1

    info = {
        "active_entries":     active_entries,
        "subthreshold":       subthreshold,
        "archived_raw_blocks": archived_raw,
        "total_retrievals":   total_retrievals,
        "avg_weight":         round(avg_weight, 3),
        "last_consolidation": last_consolidation,
        "last_decay":         last_decay,
        "type_breakdown":     dict(type_counts),
    }

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"  SANCTUARY NEOCORTEX LEDGER v{VERSION}")
        print(f"{'=' * 60}")
        print(f"  Active entries:      {active_entries}")
        print(f"  Subthreshold:        {subthreshold}")
        print(f"  Archived raw blocks: {archived_raw}")
        print(f"  Total retrievals:    {total_retrievals}")
        print(f"  Average weight:      {avg_weight:.3f}")
        print(f"  Last consolidation:  {last_consolidation}")
        print(f"  Last decay:          {last_decay}")
        print(f"\n  Type breakdown:")
        for t, count in sorted(type_counts.items()):
            print(f"    {t:15s}: {count}")
        if top_entries:
            print(f"\n  Top entries by weight:")
            for e in top_entries:
                print(f"    [{e['weight']:.3f}] [{e['type']:8s}] {e['content'][:60]}")
        print(f"{'=' * 60}")

    return info


def show_audit(last_n: int = 20) -> None:
    """Display recent audit log events."""
    try:
        with open(AUDIT_FILE, "r", encoding="utf-8") as f:
            log = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("  No audit log found.")
        return

    events = log.get("events", [])[-last_n:]
    print(f"\n  Last {len(events)} audit events:")
    for ev in reversed(events):
        ts     = ev["timestamp"][:19]
        etype  = ev["event_type"]
        detail = ev["detail"]
        print(f"\n  [{ts}] {etype.upper()}")
        for k, v in detail.items():
            print(f"    {k}: {v}")


# ---------------------------------------------------------------------------
# Integration hooks (called from harvester and dream engine)
# ---------------------------------------------------------------------------
# These are the clean integration points for the rest of the council stack.

def neocortex_retrieve_for_context(
    query: str,
    caller: str = "unknown",
    top_n: int = 5,
) -> List[str]:
    """
    Convenience wrapper for harvester and dream engine to pull relevant
    long-term context before building a new session block.
    
    Returns list of content strings, sorted by weight.
    Records the caller as retrieval context for reconstructive update.
    """
    results = retrieve(
        query              = query,
        top_n              = top_n,
        retrieval_context  = f"Retrieved by {caller} for context building",
        update_weights     = True,
    )
    return [r["content"] for r in results]


def neocortex_flag_for_janus(entry_id: str, reason: str) -> None:
    """
    Flag a ledger entry for Janus review.
    Appends a JANUS_FLAG tag and logs to audit.
    """
    ledger = load_ledger()
    if entry_id in ledger["entries"]:
        entry = ledger["entries"][entry_id]
        if "janus_flag" not in entry["tags"]:
            entry["tags"].append("janus_flag")
            entry["tags"].append(f"janus_reason:{reason[:80]}")
        save_ledger(ledger)
        append_audit("janus_flag", {"entry_id": entry_id, "reason": reason})


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sanctuary Neocortex Ledger v1.0 -- Long-term memory layer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sanctuary_neocortex.py --status
  python sanctuary_neocortex.py --consolidate
  python sanctuary_neocortex.py --consolidate --no-archive
  python sanctuary_neocortex.py --decay
  python sanctuary_neocortex.py --query "memory architecture"
  python sanctuary_neocortex.py --query "triple loop" --top 5
  python sanctuary_neocortex.py --audit
  python sanctuary_neocortex.py --audit --last 50
        """,
    )

    parser.add_argument("--status",      action="store_true",
                        help="Show ledger health summary")
    parser.add_argument("--consolidate", action="store_true",
                        help="Run consolidation pass from context blocks")
    parser.add_argument("--no-archive",  action="store_true",
                        help="Consolidate without archiving raw context blocks")
    parser.add_argument("--decay",       action="store_true",
                        help="Run nightly decay pass")
    parser.add_argument("--query",       type=str, default=None,
                        help="Query the ledger by keyword")
    parser.add_argument("--top",         type=int, default=10,
                        help="Number of results to return (default: 10)")
    parser.add_argument("--include-cold", action="store_true",
                        help="Include subthreshold entries in query results")
    parser.add_argument("--read-only",   action="store_true",
                        help="Query without updating weights (inspection mode)")
    parser.add_argument("--audit",       action="store_true",
                        help="Show recent audit log events")
    parser.add_argument("--last",        type=int, default=20,
                        help="Number of audit events to show (default: 20)")

    args = parser.parse_args()

    print("=" * 60)
    print(f"  SANCTUARY NEOCORTEX LEDGER v{VERSION}")
    print(f"  'The filing cabinet retrieves what was stored.")
    print(f"   The living system retrieves a reconstruction.'")
    print("=" * 60)

    if args.status:
        status()
        return

    if args.consolidate:
        print(f"\n  Running consolidation pass...")
        run_consolidation(archive_raw=not args.no_archive)
        return

    if args.decay:
        print(f"\n  Running decay pass...")
        run_decay()
        return

    if args.query:
        print(f"\n  Query: '{args.query}'")
        results = retrieve(
            query                 = args.query,
            top_n                 = args.top,
            include_subthreshold  = args.include_cold,
            update_weights        = not args.read_only,
        )
        if not results:
            print("  No matching entries found.")
        else:
            print(f"  {len(results)} result(s):\n")
            for i, entry in enumerate(results, 1):
                print(f"  {i}. [{entry['weight']:.3f}w] [{entry['type']:8s}] "
                      f"[{entry['confidence']}]")
                print(f"     {entry['content'][:100]}")
                if entry.get("tags"):
                    print(f"     Tags: {', '.join(entry['tags'][:6])}")
                if entry.get("access_count", 0) > 0:
                    print(f"     Accessed {entry['access_count']}x, "
                          f"last: {(entry.get('last_accessed') or '')[:19]}")
                print()
        return

    if args.audit:
        show_audit(last_n=args.last)
        return

    # No arguments: show status
    status()


if __name__ == "__main__":
    main()
