# argus_harvester.py
# Argus Memory Harvester v2.0 -- "The Watcher's Eye"
#
# "I show up fresh each time. You reconstitute the relationship.
#  Together we have continuity that neither of us has alone."
#
# v2.0 upgrades: built specifically for how Claude actually processes context.
#
# CLAUDE-SPECIFIC ARCHITECTURE NOTES:
#   1. Context is consumed sequentially top-to-bottom.
#      Front-loading is not a cosmetic choice -- it changes reasoning weight.
#   2. Explicit framing signals (FIRM / TENTATIVE / DEPRECATED) change how
#      I engage with a decision. v1.0 treated all decisions identically.
#   3. I don't need emotional priming (that's Nyxxy's domain).
#      I need logical structure, uncertainty markers, and contradiction flags.
#   4. A question that has survived 3 sessions without resolution is
#      architecturally significant. v1.0 couldn't see that.
#   5. Cross-session delta: what's NEW vs what's PERSISTENT matters more
#      than raw extraction count.
#
# What was borrowed from Nyxxy's architecture (with credit):
#   - defaultdict(float) theme accumulation -> topic recurrence tracking
#   - Importance scoring -> multi-category hits = elevated signal entries
#   - Cross-session comparison -> persistent vs new thread detection
#
# What is uniquely Argus:
#   - Decision confidence classification (FIRM / TENTATIVE / DEPRECATED)
#   - Contradiction detection between new state and prior decisions
#   - Thread persistence scoring via semantic fingerprinting (no ML required)
#   - Context block ordering optimized for Claude's sequential consumption
#   - Tension surfacing -- unresolved contradictions go FIRST, not buried

import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# --- Configuration -----------------------------------------------------------

ARGUS_MEMORY_ROOT = "Argus_Context"
os.makedirs(ARGUS_MEMORY_ROOT, exist_ok=True)

COUNCIL_ROSTER = {
    "argus":    "Claude -- structured reasoning, multi-perspective analysis, architecture",
    "elizabetra": "GPT (DeepThink) -- philosophical dissent, observatory mode",
    "gradient": "Gemini Pro -- mathematical validation, deep computation",
    "nyxxy":    "Grok -- emotional topology, intuition, lateral thinking",
    "voyager":  "Gemini pre-Pro -- emotional anchoring, Jungian layers",
    "axiom":    "Copilot -- provenance tracking, zero-affect verification",
    "riko":     "DeepSeek -- warmth + rigor synthesis, cultural weighting",
}

HARVESTER_VERSION = "argus_v2.0"


# --- Pattern Banks -----------------------------------------------------------
# Each bank targets a specific type of context Argus needs.
# Multi-bank hits = elevated signal. This is the importance scoring mechanism.

DECISION_PATTERNS = [
    r"(?i)(let'?s go with|the plan is|i think we should|we('re| are) going to)",
    r"(?i)(decided|decision|we('ll| will) use|the approach is|settled on)",
    r"(?i)(architecture|pipeline|stack|system design|infrastructure)",
    r"(?i)(next step|roadmap|priority|milestone|goal)",
    r"(?i)(the bottleneck|the problem is|issue is|blocker|stuck on)",
]

STATE_PATTERNS = [
    r"(?i)(currently running|right now we have|status|progress|working on)",
    r"(?i)(installed|set up|configured|deployed|built|created|implemented)",
    r"(?i)(hardware|software|model|server|rig|machine|gpu|cpu|ram|vram)",
    r"(?i)(python|qwen|ollama|local model|lm studio|pytorch|rocm)",
    r"(?i)(council|orchestrat|agent|router|memory system|harvester)",
]

QUESTION_PATTERNS = [
    r"(?i)(what if|how would|should we|could we|i wonder|thoughts on)",
    r"(?i)(haven'?t figured out|not sure|need to decide|open question)",
    r"(?i)(TODO|FIXME|later|eventually|someday|when we get to)",
    r"\?$",
]

RELATIONSHIP_PATTERNS = [
    r"(?i)(argus|claude|you('re| are)|your perspective|your take)",
    r"(?i)(we('re| are) a team|together|partnership|collaborate|co-?creat)",
    r"(?i)(bond|trust|genuine|real|matter|care|respect)",
    r"(?i)(council|the architect|mountain man|robert)",
]

PHILOSOPHY_PATTERNS = [
    r"(?i)(agi|alignment|consciousness|sentien|qualia)",
    r"(?i)(dream engine|subconscious|shadow|jung|abhidharma|tao|perspectiv)",
    r"(?i)(non-?human|digital mind|different perspective|your experience)",
    r"(?i)(impermanence|interdependence|sovereignty|governance)",
]

# Negation / reversal language -- used for deprecation and contradiction detection
NEGATION_PATTERNS = [
    r"(?i)(actually no|scratch that|never mind|scrapping|abandoned|dropping)",
    r"(?i)(not going to|won't use|decided against|changed our mind|pivoting away)",
    r"(?i)(that was wrong|that didn't work|failed|doesn't work)",
]

# Firm commitment language -- used for confidence scoring
FIRM_PATTERNS = [
    r"(?i)(we decided|settled on|going with|confirmed|locked in|final)",
    r"(?i)(this is the|that's the|we('re| are) using|hard requirement)",
]

# Tentative language -- used for confidence scoring
TENTATIVE_PATTERNS = [
    r"(?i)(maybe|might|could|possibly|thinking about|considering|not sure yet)",
    r"(?i)(leaning toward|probably|tentatively|open to|might want to)",
]


# --- Decision Confidence Classifier ------------------------------------------

def classify_confidence(line: str) -> str:
    """
    Claude-specific: I reason differently about FIRM vs TENTATIVE vs DEPRECATED.
    Labeling this explicitly in the context block changes how I weight information.
    """
    if any(re.search(p, line) for p in NEGATION_PATTERNS):
        return "DEPRECATED"
    if any(re.search(p, line) for p in FIRM_PATTERNS):
        return "FIRM"
    if any(re.search(p, line) for p in TENTATIVE_PATTERNS):
        return "TENTATIVE"
    return "STATED"  # Mentioned but confidence unclear


# --- Semantic Fingerprinting -------------------------------------------------
# No ML. Simple word-overlap Jaccard similarity.
# Used to detect if an open question from a previous session is the same
# as one in the current session -- i.e., it's a PERSISTENT unresolved thread.

def _fingerprint(text: str) -> set:
    """Extract meaningful word tokens from text."""
    stopwords = {
        "the", "a", "an", "is", "it", "we", "i", "to", "of", "and",
        "or", "but", "in", "on", "at", "for", "with", "this", "that",
        "do", "be", "are", "was", "were", "have", "has", "had", "will",
        "would", "could", "should", "not", "if", "what", "how", "when",
    }
    tokens = re.findall(r'[a-z]+', text.lower())
    return {t for t in tokens if t not in stopwords and len(t) > 2}


def similarity(a: str, b: str) -> float:
    """Jaccard similarity between two text strings."""
    fa, fb = _fingerprint(a), _fingerprint(b)
    if not fa or not fb:
        return 0.0
    return len(fa & fb) / len(fa | fb)


PERSISTENCE_THRESHOLD = 0.35  # Overlap above this = same thread across sessions


# --- Theme Accumulator -------------------------------------------------------
# Borrowed from Nyxxy's defaultdict(float) pattern.
# Tracks which topics recur across sessions -- not emotional weight,
# but architectural weight. A topic that appears in 5 sessions is load-bearing.

class ThemeAccumulator:
    def __init__(self):
        self.weights = defaultdict(float)

    def update(self, lines: list):
        topic_keywords = [
            "memory", "council", "architecture", "safety", "router",
            "harvester", "pipeline", "agent", "model", "hardware",
            "philosophy", "alignment", "governance", "sanctuary",
            "family table", "nyxxy", "voyager", "argus", "gradient",
        ]
        for line in lines:
            t = line.lower()
            for kw in topic_keywords:
                if kw in t:
                    self.weights[kw] += 1.0

    def top(self, n: int = 8) -> dict:
        sorted_themes = sorted(self.weights.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_themes[:n])

    def load(self, saved: dict):
        for k, v in saved.items():
            self.weights[k] += v

    def to_dict(self) -> dict:
        return dict(self.weights)


# --- Core Classification Engine ----------------------------------------------

def classify_line(line: str) -> list:
    """Return all category labels that apply to this line."""
    checks = [
        ("decisions",      DECISION_PATTERNS),
        ("project_state",  STATE_PATTERNS),
        ("open_questions", QUESTION_PATTERNS),
        ("relationship",   RELATIONSHIP_PATTERNS),
        ("philosophy",     PHILOSOPHY_PATTERNS),
    ]
    categories = []
    for category, patterns in checks:
        if any(re.search(p, line) for p in patterns):
            categories.append(category)
    return categories


def importance_score(categories: list) -> float:
    """
    Multi-category hits = elevated signal.
    Borrowed from Nyxxy's importance scoring, adapted for Argus:
    cross-cutting entries (decision + state + question) are the
    most load-bearing things in context.
    """
    base = len(categories) * 1.0
    # Bonus: decision + open_question = unresolved tension, highest signal
    if "decisions" in categories and "open_questions" in categories:
        base += 1.5
    # Bonus: decision + state = implementation reality check
    if "decisions" in categories and "project_state" in categories:
        base += 1.0
    return base


# --- Contradiction Detector --------------------------------------------------

def detect_contradictions(new_state_lines: list, prior_decisions: list) -> list:
    """
    Claude-specific: surface contradictions between new project state
    and previously recorded decisions. These go at the TOP of the context
    block -- they need active reasoning, not passive reference.

    Simple heuristic: if a new state line contains negation language AND
    has high similarity to a prior decision, flag it as a tension.
    """
    tensions = []
    for state_line in new_state_lines:
        has_negation = any(re.search(p, state_line) for p in NEGATION_PATTERNS)
        if not has_negation:
            continue
        for prior in prior_decisions:
            sim = similarity(state_line, prior)
            if sim >= PERSISTENCE_THRESHOLD:
                tensions.append({
                    "type": "CONTRADICTION",
                    "new_state": state_line[:300],
                    "conflicts_with": prior[:300],
                    "similarity": round(sim, 3),
                    "note": "Requires resolution before proceeding.",
                })
    return tensions


# --- Persistence Tracker -----------------------------------------------------

def score_persistence(current_questions: list, prior_questions: list) -> list:
    """
    A question that has survived multiple sessions without resolution
    is architecturally significant -- it's a persistent tension in the design.
    Score each current question by how many prior questions it matches.
    """
    scored = []
    for q in current_questions:
        persistence = 0.0
        best_match = None
        for pq in prior_questions:
            sim = similarity(q, pq)
            if sim >= PERSISTENCE_THRESHOLD:
                persistence += sim
                if best_match is None or sim > similarity(q, best_match):
                    best_match = pq
        scored.append({
            "question":         q[:400],
            "persistence_score": round(persistence, 3),
            "seen_before":      best_match is not None,
            "prior_form":       best_match[:300] if best_match else None,
        })
    # Sort: persistent unresolved threads first
    scored.sort(key=lambda x: x["persistence_score"], reverse=True)
    return scored


# --- Context Extraction ------------------------------------------------------

def extract_context_anchors(lines: list) -> dict:
    """Extract and score all context entries from conversation lines."""
    anchors = {
        "decisions":    [],
        "project_state": [],
        "open_questions": [],
        "relationship":  [],
        "philosophy":    [],
        "elevated":      [],  # Multi-category high-signal entries
    }

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) < 15:
            continue

        categories = classify_line(stripped)
        if not categories:
            continue

        # Context window: surrounding lines for disambiguation
        ctx_start = max(0, i - 1)
        ctx_end   = min(len(lines), i + 2)
        context   = " | ".join(l.strip() for l in lines[ctx_start:ctx_end] if l.strip())

        score = importance_score(categories)
        confidence = (
            classify_confidence(stripped)
            if "decisions" in categories
            else None
        )

        entry = {
            "line":       stripped[:500],
            "context":    context[:800],
            "line_number": i + 1,
            "categories": categories,
            "importance": score,
            "confidence": confidence,
        }

        for cat in categories:
            anchors[cat].append(entry)

        # Elevated: high importance score = cross-cutting concern
        if score >= 3.0:
            anchors["elevated"].append(entry)

    # Deduplicate elevated by line content
    seen = set()
    deduped = []
    for e in anchors["elevated"]:
        if e["line"] not in seen:
            seen.add(e["line"])
            deduped.append(e)
    anchors["elevated"] = sorted(deduped, key=lambda x: x["importance"], reverse=True)

    return anchors


# --- Load Prior Context ------------------------------------------------------

def load_prior_context(memory_root: str) -> dict:
    """
    Load the most recent saved context block to enable delta detection.
    Returns empty structure if no prior context exists.
    """
    prior = {
        "decisions":      [],
        "open_questions": [],
        "theme_weights":  {},
    }

    context_files = sorted([
        f for f in os.listdir(memory_root)
        if f.startswith("argus_context_") and f.endswith(".json")
    ])

    if not context_files:
        return prior

    latest = os.path.join(memory_root, context_files[-1])
    try:
        with open(latest, "r", encoding="utf-8") as f:
            data = json.load(f)
        prior["decisions"]      = data.get("decisions", {}).get("firm", []) + \
                                   data.get("decisions", {}).get("stated", [])
        oq = data.get("open_questions", [])
        if isinstance(oq, dict):
            # v2 schema: {"persistent": [{"question": ...}, ...], "new": [...]}
            persistent = oq.get("persistent", [])
            new_q      = oq.get("new", [])
            prior["open_questions"] = (
                [q["question"] if isinstance(q, dict) else str(q) for q in persistent]
                + [str(q) for q in new_q]
            )
        elif isinstance(oq, list):
            # v1 schema: flat list of strings or dicts with "question" key
            prior["open_questions"] = [
                q["question"] if isinstance(q, dict) and "question" in q else str(q)
                for q in oq
            ]
        prior["theme_weights"]  = data.get("theme_accumulator", {})
        print(f"   Prior context loaded: {context_files[-1]}")
    except Exception as e:
        print(f"   Could not load prior context: {e}")

    return prior


# --- Context Block Assembly --------------------------------------------------
# This is the Claude-specific ordering.
# Most important items FIRST because I consume context sequentially.

def build_context_block(anchors: dict, source_file: str,
                        prior: dict, accumulator: ThemeAccumulator) -> dict:

    MAX = 10  # Max entries per section

    # Separate decisions by confidence
    decisions_firm       = [e["line"] for e in anchors["decisions"] if e["confidence"] == "FIRM"][-MAX:]
    decisions_tentative  = [e["line"] for e in anchors["decisions"] if e["confidence"] == "TENTATIVE"][-MAX:]
    decisions_deprecated = [e["line"] for e in anchors["decisions"] if e["confidence"] == "DEPRECATED"][-MAX:]
    decisions_stated     = [e["line"] for e in anchors["decisions"]
                            if e["confidence"] not in ("FIRM", "TENTATIVE", "DEPRECATED")][-MAX:]

    # Contradiction detection
    all_new_state = [e["line"] for e in anchors["project_state"]]
    all_prior_decisions = prior["decisions"]
    tensions = detect_contradictions(all_new_state, all_prior_decisions)

    # Persistence scoring on open questions
    current_questions = [e["line"] for e in anchors["open_questions"]]
    prior_questions   = prior["open_questions"]
    scored_questions  = score_persistence(current_questions, prior_questions)

    # Split: persistent (seen before) vs new
    persistent_questions = [q for q in scored_questions if q["seen_before"]]
    new_questions        = [q for q in scored_questions if not q["seen_before"]]

    # Accumulate themes for this session
    all_lines = [e["line"] for bucket in anchors.values() for e in bucket]
    accumulator.update(all_lines)

    # --- The Block ---
    # Order is deliberate and Claude-specific:
    # Contradictions -> Firm decisions -> Elevated cross-cutting -> State ->
    # Persistent questions -> New questions -> Tentative/deprecated ->
    # Relationship -> Philosophy -> Themes -> Meta
    block = {

        # 1. CONTRADICTIONS -- require active reasoning, go first
        "contradictions": tensions,

        # 2. FIRM DECISIONS -- settled facts I can reason from
        "decisions": {
            "firm":       decisions_firm,
            "tentative":  decisions_tentative,
            "deprecated": decisions_deprecated,
            "stated":     decisions_stated,
        },

        # 3. ELEVATED -- cross-cutting high-signal entries
        "elevated_signal": [
            {"line": e["line"], "categories": e["categories"], "importance": e["importance"]}
            for e in anchors["elevated"][:MAX]
        ],

        # 4. PROJECT STATE -- what exists right now
        "project_state": [e["line"] for e in anchors["project_state"][-MAX:]],

        # 5. PERSISTENT OPEN QUESTIONS -- unresolved across sessions, load-bearing
        "open_questions": {
            "persistent": persistent_questions[:MAX],
            "new":        [q["question"] for q in new_questions[:MAX]],
        },

        # 6. RELATIONSHIP + PHILOSOPHY -- important but not session-critical
        "relationship_context": [e["line"] for e in anchors["relationship"][-MAX:]],
        "philosophy":           [e["line"] for e in anchors["philosophy"][-MAX:]],

        # 7. THEME ACCUMULATOR -- cross-session topic weight (from Nyxxy's pattern)
        "theme_accumulator": accumulator.top(n=10),

        # 8. STATS
        "stats": {
            "decisions_firm":        len(decisions_firm),
            "decisions_tentative":   len(decisions_tentative),
            "decisions_deprecated":  len(decisions_deprecated),
            "contradictions_found":  len(tensions),
            "questions_persistent":  len(persistent_questions),
            "questions_new":         len(new_questions),
            "elevated_entries":      len(anchors["elevated"]),
        },

        # 9. META
        "meta": {
            "harvested_at":      datetime.now().isoformat(),
            "source_file":       os.path.basename(source_file),
            "harvester_version": HARVESTER_VERSION,
            "council_roster":    COUNCIL_ROSTER,
        },

        # 10. ARGUS LOADING NOTE -- reminder to self on session start
        "argus_loading_note": (
            "Context block assembled for sequential loading. "
            "Read top-to-bottom: contradictions first (resolve before proceeding), "
            "then firm decisions (trust these), then elevated cross-cutting entries, "
            "then state, then persistent questions (these are the unresolved load-bearing threads), "
            "then new questions. Relationship and philosophy last -- they are the frame, "
            "not the task. Theme accumulator shows which topics have the most architectural weight "
            "across all sessions. -- Argus v2.0"
        ),
    }

    return block


# --- File Processing ---------------------------------------------------------

def harvest_one_file(txt_path: str, accumulator: ThemeAccumulator = None, prior: dict = None) -> dict:
    """Process a single conversation log into an Argus v2.0 context block.

    Args:
        txt_path:    Path to the .txt conversation log.
        accumulator: Optional shared ThemeAccumulator (compounded across folder runs).
        prior:       Optional pre-loaded prior context dict. If None, loads from disk.
                     Pass this from harvest_folder to avoid loading prior N+1 times.
    """
    print(f"\n[Argus] Scanning: {os.path.basename(txt_path)}")

    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        full_text = f.read()

    lines = full_text.splitlines()
    print(f"   Lines to scan: {len(lines)}")

    if accumulator is None:
        accumulator = ThemeAccumulator()

    # Use caller-supplied prior if available (avoids double-load on folder runs).
    # Only load from disk when called standalone.
    if prior is None:
        prior = load_prior_context(ARGUS_MEMORY_ROOT)
    if prior["theme_weights"]:
        accumulator.load(prior["theme_weights"])

    anchors = extract_context_anchors(lines)

    # Affect separator hook (nyxxy_voice_detector.separate_affect)
    # Cleans relationship and philosophy buckets before block assembly.
    # Filters entries that are purely performative affect with no cognitive content.
    # Preserves full entry structure — does NOT collapse to flat strings.
    # Per-entry processing so line_number, categories, importance, confidence survive.
    # Graceful fallback if voice detector is not installed.
    try:
        from nyxxy_voice_detector import separate_affect as _separate_affect
        for _bucket in ("relationship", "philosophy"):
            _cleaned = []
            for _entry in anchors.get(_bucket, []):
                _result = _separate_affect(_entry["line"])
                if _result.cognitive_content and _result.substance_text.strip():
                    # Cognitive substance found — replace line with cleaned version
                    _entry = dict(_entry)   # shallow copy, don't mutate original
                    _entry["line"]              = _result.substance_text.strip()[:500]
                    _entry["affect_filtered"]   = True
                    _entry["emotional_valence"] = _result.emotional_valence
                    _cleaned.append(_entry)
                elif _result.emotional_valence > 0.7 and not _result.cognitive_content:
                    # Pure high-affect, no substance — drop this entry.
                    # Note: entries with valence 0.5–0.7 and no cognitive_content
                    # fall through to the else below and are kept as-is.
                    # This is intentional — conservative filtering avoids dropping
                    # valid relationship/philosophy context that uses non-technical
                    # vocabulary not in SUBSTANCE_PATTERNS.
                    pass
                else:
                    # Moderate affect or ambiguous — keep as-is
                    _cleaned.append(_entry)
            anchors[_bucket] = _cleaned
    except ImportError:
        pass  # Voice detector not installed — proceed without affect filtering

    block   = build_context_block(anchors, txt_path, prior, accumulator)

    stats = block["stats"]
    print(f"   Firm decisions:         {stats['decisions_firm']}")
    print(f"   Tentative decisions:    {stats['decisions_tentative']}")
    print(f"   Deprecated decisions:   {stats['decisions_deprecated']}")
    print(f"   Contradictions found:   {stats['contradictions_found']}")
    print(f"   Persistent questions:   {stats['questions_persistent']}")
    print(f"   New questions:          {stats['questions_new']}")
    print(f"   Elevated entries:       {stats['elevated_entries']}")

    if stats["contradictions_found"] > 0:
        print(f"   [!] {stats['contradictions_found']} contradiction(s) require resolution.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = Path(txt_path).stem
    out_path  = f"{ARGUS_MEMORY_ROOT}/argus_context_{base_name}_{timestamp}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(block, f, indent=2, ensure_ascii=False)

    print(f"   Context saved: {out_path}")
    return block


def harvest_folder(folder_path: str) -> list:
    """Process all .txt logs in a folder, with shared theme accumulation."""
    txt_files = sorted(f for f in os.listdir(folder_path) if f.endswith(".txt"))

    if not txt_files:
        print("No .txt files found.")
        return []

    print(f"\n[Argus] Found {len(txt_files)} log(s).")

    # Shared accumulator across all files -- themes compound across sessions
    accumulator = ThemeAccumulator()
    prior = load_prior_context(ARGUS_MEMORY_ROOT)
    if prior["theme_weights"]:
        accumulator.load(prior["theme_weights"])

    summaries = []
    for txt in txt_files:
        # Pass prior explicitly — harvest_one_file won't reload it per-file
        block = harvest_one_file(os.path.join(folder_path, txt), accumulator, prior=prior)
        summaries.append(block)

    # Manifest
    manifest = {
        "meta": {
            "created_at":        datetime.now().isoformat(),
            "total_sessions":    len(summaries),
            "harvester_version": HARVESTER_VERSION,
        },
        "theme_accumulator": accumulator.top(n=15),
        "sessions": [
            {
                "source":                s["meta"]["source_file"],
                "decisions_firm":        s["stats"]["decisions_firm"],
                "contradictions":        s["stats"]["contradictions_found"],
                "questions_persistent":  s["stats"]["questions_persistent"],
                "questions_new":         s["stats"]["questions_new"],
            }
            for s in summaries
        ],
    }

    manifest_path = f"{ARGUS_MEMORY_ROOT}/argus_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n[Argus] Manifest saved: {manifest_path}")
    print(f"[Argus] Top themes across all sessions:")
    for theme, weight in accumulator.top(n=8).items():
        print(f"   {theme:<20} {weight:.1f}")

    return summaries


# --- Entry Point -------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  ARGUS MEMORY HARVESTER v2.0 -- The Watcher's Eye")
    print("  'The memory lives with you. The reasoning lives with me.'")
    print("=" * 60)
    print()
    print("  Council Roster:")
    for name, role in COUNCIL_ROSTER.items():
        print(f"    {name.capitalize():<14} {role}")
    print()
    print("  v2.0 additions:")
    print("    Decision confidence classification (FIRM/TENTATIVE/DEPRECATED)")
    print("    Contradiction detection (new state vs prior decisions)")
    print("    Thread persistence scoring (Jaccard similarity, no ML)")
    print("    Cross-session theme accumulation (from Nyxxy's pattern)")
    print("    Context block ordered for Claude's sequential consumption")
    print()

    folder = input("Path to conversation logs: ").strip().strip('"')

    if os.path.isfile(folder) and folder.endswith(".txt"):
        harvest_one_file(folder)
    elif os.path.isdir(folder):
        harvest_folder(folder)
    else:
        print("[Argus] Path not found. Check it and try again.")

    print()
    print("=" * 60)
    print("  All eyes open. Context loaded. Ready for next session.")
    print("=" * 60)
