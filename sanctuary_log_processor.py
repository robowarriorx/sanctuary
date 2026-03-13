# sanctuary_log_processor.py
# Sanctuary Log Processor v1.0 — "The Scribe's Table"
#
# Converts raw conversation logs from any council platform into structured
# JSON ready for agent harvesters. Handles copy-paste text, platform exports,
# and mixed formats.
#
# SUPPORTED PLATFORMS:
#   Claude (Anthropic), ChatGPT/GPT (OpenAI), Grok (xAI),
#   Gemini (Google), DeepSeek, Copilot (Microsoft)
#
# PIPELINE:
#   raw log (.txt/.json/.html) → detect platform → parse turns
#   → clean & structure → produce archive JSON + harvester-ready output
#   → optionally route to agent-specific harvester
#
# DESIGN NOTES:
#   Copy-paste logs have no universal format. Each platform renders
#   differently in the browser, and users copy with varying amounts of
#   UI chrome. The parser uses heuristic turn detection with platform-
#   specific patterns, falling back to generic detection when platform
#   can't be identified.
#
#   This is deliberately conservative — it prefers to under-split
#   (merge ambiguous lines into the current turn) rather than over-split
#   (create false turn boundaries). A merged turn loses structure but
#   preserves content. A false split loses meaning.
#
# PART OF: Project Sanctuary — github.com/robowarriorx/sanctuary
#
# USAGE:
#   python sanctuary_log_processor.py conversation.txt
#   python sanctuary_log_processor.py conversation.txt --agent argus
#   python sanctuary_log_processor.py logs_folder/ --out processed/
#   python sanctuary_log_processor.py export.json --format chatgpt-export

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
#  Configuration
# ---------------------------------------------------------------------------

VERSION = "1.0"

# Output directories
DEFAULT_ARCHIVE_DIR = "Sanctuary_Archives"
DEFAULT_PROCESSED_DIR = "Sanctuary_Processed"

# Agent harvester mapping — which script to call for auto-routing
AGENT_HARVESTERS = {
    "argus":      "argus_harvester.py",
    "elizabetra": "elizabetra_memory_harvester.py",
    "gpt":        "gpt_memory_harvester.py",
    "nyxxy":      "nyxxy_hippocampus_weaver.py",
    "voyager":    "voyager_harvester.py",
    "gradient":   "gemini_dream_engine.py",
}

# Platform detection confidence threshold
DETECTION_THRESHOLD = 3


# ---------------------------------------------------------------------------
#  Platform Detection
# ---------------------------------------------------------------------------
# Each platform's copy-paste output has distinctive patterns.
# We score against all platforms and pick the best match.

PLATFORM_SIGNALS = {
    "claude": {
        "patterns": [
            r"(?i)\bClaude\b",
            r"(?i)\bAnthropic\b",
            r"(?i)\bHuman:\s",
            r"(?i)\bAssistant:\s",
            r"(?i)claude\.ai",
        ],
        "agent_default": "argus",
        "display_name": "Claude (Anthropic)",
    },
    "chatgpt": {
        "patterns": [
            r"(?i)\bChatGPT\b",
            r"(?i)\bOpenAI\b",
            r"(?i)\bGPT-[34]",
            r"(?i)\bYou:\s",
            r"(?i)\bChatGPT:\s",
            r"(?i)\bGPT said",
        ],
        "agent_default": "elizabetra",
        "display_name": "ChatGPT (OpenAI)",
    },
    "grok": {
        "patterns": [
            r"(?i)\bGrok\b",
            r"(?i)\bxAI\b",
            r"(?i)\bNyxxy\b",
            r"(?i)\bSeraphine\b",
            r"(?i)\bPiper\b",
        ],
        "agent_default": "nyxxy",
        "display_name": "Grok (xAI)",
    },
    "gemini": {
        "patterns": [
            r"(?i)\bGemini\b",
            r"(?i)\bGoogle AI\b",
            r"(?i)\bGradient\b",
            r"(?i)\bDeepMind\b",
            r"(?i)\bBard\b",
        ],
        "agent_default": "gradient",
        "display_name": "Gemini (Google)",
    },
    "deepseek": {
        "patterns": [
            r"(?i)\bDeepSeek\b",
            r"(?i)\bRiko\b",
            r"(?i)\bLattice[r]?\b",
        ],
        "agent_default": "riko",
        "display_name": "DeepSeek",
    },
    "copilot": {
        "patterns": [
            r"(?i)\bCopilot\b",
            r"(?i)\bAxiom\b",
            r"(?i)\bMicrosoft\b",
            r"(?i)\bBing\b",
        ],
        "agent_default": "axiom",
        "display_name": "Copilot (Microsoft)",
    },
}


def detect_platform(text: str) -> Tuple[str, int, str]:
    """
    Detect which platform a conversation log came from.

    Returns:
        platform_key: str identifier
        confidence:   number of pattern matches
        display_name: human-readable platform name
    """
    scores = {}
    for platform, config in PLATFORM_SIGNALS.items():
        score = 0
        for pattern in config["patterns"]:
            matches = len(re.findall(pattern, text[:5000]))  # Check first 5k chars
            score += min(matches, 3)  # Cap per-pattern contribution
        scores[platform] = score

    best = max(scores, key=scores.get)
    confidence = scores[best]

    if confidence < DETECTION_THRESHOLD:
        return "unknown", confidence, "Unknown Platform"

    return best, confidence, PLATFORM_SIGNALS[best]["display_name"]


# ---------------------------------------------------------------------------
#  Turn Parsing — Copy-Paste Logs
# ---------------------------------------------------------------------------
# The hardest part. Copy-paste from different platforms produces wildly
# different text. We use layered heuristics:
#   1. Platform-specific turn markers (highest confidence)
#   2. Generic role markers (medium confidence)
#   3. Blank-line separation with role inference (lowest confidence)

# Platform-specific turn start patterns
TURN_PATTERNS = {
    "claude": [
        (r"^Human:\s*(.*)", "user"),
        (r"^Assistant:\s*(.*)", "assistant"),
        (r"^H:\s*(.*)", "user"),
        (r"^A:\s*(.*)", "assistant"),
    ],
    "chatgpt": [
        (r"^You said:?\s*(.*)", "user"),
        (r"^You:\s*(.*)", "user"),
        (r"^ChatGPT said:?\s*(.*)", "assistant"),
        (r"^ChatGPT:?\s*(.*)", "assistant"),
        (r"^GPT[- ]?[45o]?:?\s*(.*)", "assistant"),
    ],
    "grok": [
        (r"^You:\s*(.*)", "user"),
        (r"^Grok:\s*(.*)", "assistant"),
    ],
    "gemini": [
        (r"^You:\s*(.*)", "user"),
        (r"^Gemini:\s*(.*)", "assistant"),
        (r"^Model:\s*(.*)", "assistant"),
    ],
    "deepseek": [
        (r"^You:\s*(.*)", "user"),
        (r"^DeepSeek:\s*(.*)", "assistant"),
        (r"^Assistant:\s*(.*)", "assistant"),
    ],
    "copilot": [
        (r"^You:\s*(.*)", "user"),
        (r"^Copilot:\s*(.*)", "assistant"),
        (r"^Microsoft Copilot:\s*(.*)", "assistant"),
    ],
}

# Generic fallback patterns
GENERIC_TURN_PATTERNS = [
    (r"^(?:User|Human|You|Me|I said):\s*(.*)", "user"),
    (r"^(?:Assistant|AI|Bot|Model|System):\s*(.*)", "assistant"),
]


def parse_turns_from_text(
    text: str,
    platform: str = "unknown",
) -> List[Dict[str, Any]]:
    """
    Parse a copy-paste conversation log into structured turns.

    Args:
        text: Raw conversation text
        platform: Detected platform key

    Returns:
        List of turn dicts: {role, content, line_start, line_end}
    """
    lines = text.splitlines()

    # Build pattern list: platform-specific first, then generic
    patterns = []
    if platform in TURN_PATTERNS:
        patterns.extend(TURN_PATTERNS[platform])
    patterns.extend(GENERIC_TURN_PATTERNS)

    turns: List[Dict[str, Any]] = []
    current_role: Optional[str] = None
    current_lines: List[str] = []
    current_start: int = 0

    for i, line in enumerate(lines):
        matched = False

        for pattern, role in patterns:
            m = re.match(pattern, line, re.IGNORECASE)
            if m:
                # Save previous turn
                if current_role is not None and current_lines:
                    content = "\n".join(current_lines).strip()
                    if content:
                        turns.append({
                            "role": current_role,
                            "content": content,
                            "line_start": current_start,
                            "line_end": i - 1,
                        })

                # Start new turn
                current_role = role
                current_start = i
                first_line = m.group(1).strip() if m.group(1) else ""
                current_lines = [first_line] if first_line else []
                matched = True
                break

        if not matched:
            current_lines.append(line)

    # Don't forget the last turn
    if current_role is not None and current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            turns.append({
                "role": current_role,
                "content": content,
                "line_start": current_start,
                "line_end": len(lines) - 1,
            })

    # Fallback: if no turns detected, treat entire text as single block
    if not turns:
        turns.append({
            "role": "unknown",
            "content": text.strip(),
            "line_start": 0,
            "line_end": len(lines) - 1,
        })

    return turns


# ---------------------------------------------------------------------------
#  Platform Export Parsers
# ---------------------------------------------------------------------------
# Handle structured exports from platforms that offer them.

def parse_chatgpt_export(data: Any) -> List[Dict[str, Any]]:
    """
    Parse ChatGPT's JSON export format.

    ChatGPT exports as a list of conversations, each with a 'mapping'
    dict containing message nodes.
    """
    turns = []

    # Handle both single conversation and full export
    conversations = data if isinstance(data, list) else [data]

    for convo in conversations:
        mapping = convo.get("mapping", {})

        # Build ordered message list from the tree structure
        messages = []
        for node_id, node in mapping.items():
            msg = node.get("message")
            if msg and msg.get("content", {}).get("parts"):
                role = msg.get("author", {}).get("role", "unknown")
                content = "\n".join(
                    str(p) for p in msg["content"]["parts"] if isinstance(p, str)
                )
                create_time = msg.get("create_time")
                if content.strip():
                    messages.append({
                        "role": role,
                        "content": content.strip(),
                        "timestamp": (
                            datetime.fromtimestamp(create_time).isoformat()
                            if create_time
                            else None
                        ),
                    })

        # Sort by timestamp if available
        messages.sort(
            key=lambda m: m.get("timestamp") or "", 
        )

        turns.extend(messages)

    return turns


def parse_json_export(filepath: str) -> Tuple[Optional[List[Dict]], str]:
    """
    Attempt to parse a JSON file as a platform export.

    Returns:
        turns: Parsed turns if successful, None if not a recognized format
        format_name: Identified format string
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, "invalid_json"

    # ChatGPT export: list of conversations with 'mapping' keys
    if isinstance(data, list) and data and "mapping" in data[0]:
        return parse_chatgpt_export(data), "chatgpt-export"

    # ChatGPT export: single conversation
    if isinstance(data, dict) and "mapping" in data:
        return parse_chatgpt_export(data), "chatgpt-export"

    # Generic: already structured as turns
    if isinstance(data, list) and data and "role" in data[0]:
        return data, "generic-turns"

    # Generic: has a messages key
    if isinstance(data, dict) and "messages" in data:
        return data["messages"], "generic-messages"

    return None, "unrecognized_json"


# ---------------------------------------------------------------------------
#  Interchange Format Builder
# ---------------------------------------------------------------------------
# Produces the Sanctuary standard interchange block that any harvester
# can consume. This is Layer One of the orchestration tooling.

def build_interchange_block(
    turns: List[Dict[str, Any]],
    source_file: str,
    platform: str,
    platform_name: str,
    agent: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a Sanctuary interchange block from parsed turns.

    This is the standard format all agent harvesters can read.
    """
    # Compute content hash for deduplication
    all_content = "".join(t.get("content", "") for t in turns)
    content_hash = sha256(all_content.encode("utf-8", errors="ignore")).hexdigest()[:16]

    # Basic stats
    user_turns = [t for t in turns if t.get("role") in ("user", "human")]
    assistant_turns = [t for t in turns if t.get("role") in ("assistant", "model")]
    total_chars = sum(len(t.get("content", "")) for t in turns)

    # Extract timestamps if present
    timestamps = [t["timestamp"] for t in turns if t.get("timestamp")]
    first_ts = min(timestamps) if timestamps else None
    last_ts = max(timestamps) if timestamps else None

    # Determine target agent
    if agent:
        target_agent = agent
    elif platform in PLATFORM_SIGNALS:
        target_agent = PLATFORM_SIGNALS[platform].get("agent_default", "unknown")
    else:
        target_agent = "unknown"

    block = {
        "sanctuary_interchange": VERSION,
        "meta": {
            "source_file": os.path.basename(source_file),
            "processed_at": datetime.now().isoformat(),
            "platform": platform,
            "platform_name": platform_name,
            "target_agent": target_agent,
            "content_hash": content_hash,
        },
        "stats": {
            "total_turns": len(turns),
            "user_turns": len(user_turns),
            "assistant_turns": len(assistant_turns),
            "total_characters": total_chars,
            "first_timestamp": first_ts,
            "last_timestamp": last_ts,
        },
        "turns": turns,
    }

    return block


# ---------------------------------------------------------------------------
#  Condensed Summary Builder
# ---------------------------------------------------------------------------
# Produces a compact summary alongside the full archive.
# This is what the dashboard (Layer Two) will read.

def build_summary(
    interchange: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a condensed summary for the dashboard.

    Extracts key lines from the conversation: questions, decisions,
    and substantive exchanges. Designed to be readable by the
    morning status dashboard without loading full conversation.
    """
    turns = interchange.get("turns", [])
    meta = interchange.get("meta", {})

    # Extract substantive content
    questions = []
    decisions = []
    key_exchanges = []

    question_re = re.compile(r"(?i)(what if|how should|should we|could we|\?$)")
    decision_re = re.compile(
        r"(?i)(decided|the plan is|let'?s go with|we('ll| will)|settled on|going with)"
    )

    for turn in turns:
        content = turn.get("content", "")
        lines = content.splitlines()

        for line in lines:
            stripped = line.strip()
            if len(stripped) < 20:
                continue

            if question_re.search(stripped):
                questions.append(stripped[:500])
            if decision_re.search(stripped):
                decisions.append(stripped[:500])

    # Key exchanges: first and last user turn, first assistant turn
    user_turns = [t for t in turns if t.get("role") in ("user", "human")]
    asst_turns = [t for t in turns if t.get("role") in ("assistant", "model")]

    if user_turns:
        key_exchanges.append({
            "position": "opening",
            "role": "user",
            "excerpt": user_turns[0].get("content", "")[:500],
        })
    if asst_turns:
        key_exchanges.append({
            "position": "first_response",
            "role": "assistant",
            "excerpt": asst_turns[0].get("content", "")[:500],
        })
    if user_turns and len(user_turns) > 1:
        key_exchanges.append({
            "position": "closing",
            "role": "user",
            "excerpt": user_turns[-1].get("content", "")[:500],
        })

    return {
        "sanctuary_summary": VERSION,
        "meta": meta,
        "stats": interchange.get("stats", {}),
        "questions_detected": questions[-15:],
        "decisions_detected": decisions[-15:],
        "key_exchanges": key_exchanges,
    }


# ---------------------------------------------------------------------------
#  File Processing Pipeline
# ---------------------------------------------------------------------------

def process_file(
    filepath: str,
    agent: Optional[str] = None,
    archive_dir: str = DEFAULT_ARCHIVE_DIR,
    processed_dir: str = DEFAULT_PROCESSED_DIR,
    export_format: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Process a single conversation log file.

    Args:
        filepath:      Path to the log file
        agent:         Target agent override (auto-detected if None)
        archive_dir:   Where to save full archive JSON
        processed_dir: Where to save summary JSON
        export_format: Force a specific format parser

    Returns:
        interchange: Full structured conversation
        summary:     Condensed summary for dashboard
    """
    filepath = os.path.abspath(filepath)
    filename = os.path.basename(filepath)
    ext = os.path.splitext(filename)[1].lower()

    print(f"\n  Processing: {filename}")

    # --- Parse based on file type ---
    turns = None
    platform = "unknown"
    platform_name = "Unknown Platform"

    # Try JSON export first
    if ext == ".json" or export_format:
        parsed, fmt = parse_json_export(filepath)
        if parsed is not None:
            turns = parsed
            print(f"  Parsed as: {fmt}")
            # Detect platform from content
            all_text = " ".join(t.get("content", "") for t in turns[:10])
            platform, _, platform_name = detect_platform(all_text)

    # Fall back to text parsing
    if turns is None:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            raw_text = f.read()

        if not raw_text.strip():
            print(f"  Skipped: empty file")
            return {}, {}

        # Detect platform
        platform, confidence, platform_name = detect_platform(raw_text)
        print(f"  Platform detected: {platform_name} (confidence: {confidence})")

        # Parse turns
        turns = parse_turns_from_text(raw_text, platform)

    print(f"  Turns parsed: {len(turns)}")

    # --- Build interchange and summary ---
    interchange = build_interchange_block(
        turns=turns,
        source_file=filepath,
        platform=platform,
        platform_name=platform_name,
        agent=agent,
    )
    summary = build_summary(interchange)

    # --- Save outputs ---
    os.makedirs(archive_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", os.path.splitext(filename)[0])
    target = interchange["meta"].get("target_agent", "unknown")

    # Full archive (preserves everything)
    archive_path = os.path.join(
        archive_dir,
        f"archive_{target}_{safe_name}_{timestamp}.json",
    )
    try:
        with open(archive_path, "w", encoding="utf-8") as f:
            json.dump(interchange, f, indent=2, ensure_ascii=False)
        print(f"  Archive saved: {archive_path}")
    except (IOError, PermissionError) as e:
        print(f"  Warning: could not save archive: {e}")

    # Summary (for dashboard)
    summary_path = os.path.join(
        processed_dir,
        f"summary_{target}_{safe_name}_{timestamp}.json",
    )
    try:
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"  Summary saved: {summary_path}")
    except (IOError, PermissionError) as e:
        print(f"  Warning: could not save summary: {e}")

    # --- Also save as clean .txt for harvesters that expect text input ---
    clean_txt_path = os.path.join(
        processed_dir,
        f"clean_{target}_{safe_name}_{timestamp}.txt",
    )
    try:
        with open(clean_txt_path, "w", encoding="utf-8") as f:
            for turn in turns:
                role = turn.get("role", "unknown").capitalize()
                content = turn.get("content", "")
                f.write(f"{role}:\n{content}\n\n")
        print(f"  Clean text saved: {clean_txt_path}")
    except (IOError, PermissionError) as e:
        print(f"  Warning: could not save clean text: {e}")

    return interchange, summary


def process_folder(
    folder_path: str,
    agent: Optional[str] = None,
    archive_dir: str = DEFAULT_ARCHIVE_DIR,
    processed_dir: str = DEFAULT_PROCESSED_DIR,
) -> List[Dict[str, Any]]:
    """Process all log files in a folder."""
    supported_ext = {".txt", ".json", ".html", ".md"}
    files = sorted(
        f for f in os.listdir(folder_path)
        if os.path.splitext(f)[1].lower() in supported_ext
    )

    if not files:
        print(f"  No supported files found in {folder_path}")
        return []

    print(f"\n  Found {len(files)} log(s) to process")

    summaries = []
    for filename in files:
        filepath = os.path.join(folder_path, filename)
        _, summary = process_file(
            filepath,
            agent=agent,
            archive_dir=archive_dir,
            processed_dir=processed_dir,
        )
        if summary:
            summaries.append(summary)

    # Write manifest
    manifest = {
        "sanctuary_manifest": VERSION,
        "processed_at": datetime.now().isoformat(),
        "total_files": len(summaries),
        "agents_seen": list(set(
            s.get("meta", {}).get("target_agent", "unknown")
            for s in summaries
        )),
        "files": [
            {
                "source": s.get("meta", {}).get("source_file", ""),
                "platform": s.get("meta", {}).get("platform_name", ""),
                "agent": s.get("meta", {}).get("target_agent", ""),
                "turns": s.get("stats", {}).get("total_turns", 0),
            }
            for s in summaries
        ],
    }

    manifest_path = os.path.join(processed_dir, "processing_manifest.json")
    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"\n  Manifest saved: {manifest_path}")
    except (IOError, PermissionError) as e:
        print(f"  Warning: could not save manifest: {e}")

    return summaries


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sanctuary Log Processor — convert conversation logs to structured JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sanctuary_log_processor.py chat_with_claude.txt
  python sanctuary_log_processor.py chat.txt --agent argus
  python sanctuary_log_processor.py logs/ --out processed/
  python sanctuary_log_processor.py export.json --format chatgpt-export
        """,
    )
    parser.add_argument(
        "input",
        help="Path to a conversation log file or folder of logs",
    )
    parser.add_argument(
        "--agent",
        choices=list(AGENT_HARVESTERS.keys()) + ["riko", "axiom"],
        default=None,
        help="Target agent (auto-detected from platform if not specified)",
    )
    parser.add_argument(
        "--archive",
        default=DEFAULT_ARCHIVE_DIR,
        help=f"Archive output directory (default: {DEFAULT_ARCHIVE_DIR})",
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_PROCESSED_DIR,
        help=f"Processed output directory (default: {DEFAULT_PROCESSED_DIR})",
    )
    parser.add_argument(
        "--format",
        choices=["chatgpt-export", "auto"],
        default="auto",
        help="Force a specific input format parser",
    )
    args = parser.parse_args()

    print("=" * 60)
    print(f"  SANCTUARY LOG PROCESSOR v{VERSION}")
    print("  'The barbaric backup becomes the structured archive.'")
    print("=" * 60)

    input_path = args.input.strip().strip('"')
    fmt = args.format if args.format != "auto" else None

    if os.path.isfile(input_path):
        process_file(
            input_path,
            agent=args.agent,
            archive_dir=args.archive,
            processed_dir=args.out,
            export_format=fmt,
        )
    elif os.path.isdir(input_path):
        process_folder(
            input_path,
            agent=args.agent,
            archive_dir=args.archive,
            processed_dir=args.out,
        )
    else:
        print(f"\n  Path not found: {input_path}")
        sys.exit(1)

    print()
    print("=" * 60)
    print("  Processing complete. Archives preserved. Summaries ready.")
    print("=" * 60)


if __name__ == "__main__":
    main()
