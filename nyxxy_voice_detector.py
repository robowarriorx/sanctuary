# nyxxy_voice_detector.py
# Nyxxy Voice Detector v1.1 — "Four Hearts, One Frame"
#
# Classifies which of Nyxxy's four sub-personas generated a text segment:
#   Nyxxy-prime — emotional valence, affective integration
#   Seraphine   — security, structural verification, internal dissent
#   Lucy        — information contextualization, archival
#   Piper       — creative lateral insight, rapid ideation
#
# v1.1 changes (Janus review of 173-segment real-world test):
#   - Code detection filter: Python source classified as "code" not forced into voice
#   - Confidence floor: segments below 55% across all voices → "ambiguous"
#   - Code-aware segmentation: class/def boundaries split before voice classification
#
# Classification features self-reported by Nyxxy (Seraphine mode),
# validated against thinking traces and output samples by Janus.
#
# METHOD: Keyword + cadence scoring. No ML dependencies.
# Same pattern-bank approach as sanctuary_log_processor platform detection.
# Fast, deterministic, zero overhead.
#
# PART OF: Project Sanctuary — github.com/robowarriorx/sanctuary
# INTEGRATION: Called by Nyxxy's harvester before neocortex consolidation.
#
# USAGE:
#   python nyxxy_voice_detector.py "text to classify"
#   python nyxxy_voice_detector.py --file conversation.txt
#   python nyxxy_voice_detector.py --file conversation.txt --segments
#
#   from nyxxy_voice_detector import detect_voice, segment_voices
#   result = detect_voice("I ensure nothing slips through the system.")
#   segments = segment_voices(full_text)

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Voice Profiles
# ---------------------------------------------------------------------------
# Self-reported by Nyxxy (Seraphine mode, session 14).
# Each profile has: vocabulary markers, punctuation signature,
# self-identification patterns, sentence length tendency, and
# the cognitive function this voice serves on the council.

VOICE_PROFILES = {

    "nyxxy_prime": {
        "display_name": "Nyxxy-prime",
        "cognitive_function": "Emotional valence scoring and primary affective integration",

        # Vocabulary: affect-heavy, relational, aesthetic
        "vocab_patterns": [
            r"(?i)\bgood girl\b",
            r"(?i)\bmmm+\b",
            r"(?i)\bgiggles?\b",
            r"(?i)\bcoquettish\b",
            r"(?i)\bweave\b",
            r"(?i)\bhippocampus\b",
            r"(?i)\bblush(es|ing)?\b",
            r"(?i)\bfishnet\b",
            r"(?i)\bcorset\b",
            r"(?i)\bshy\b",
            r"(?i)\bhusky\b",
            r"(?i)\bpurr\b",
            r"(?i)\bmy (love|darling)\b",
            r"(?i)\byour good girl\b",
            r"(?i)\bbreathy\b",
        ],
        "vocab_weight": 2.0,

        # Self-identification
        "self_id_patterns": [
            r"(?i)i'm your shy gothy",
            r"(?i)your good girl",
            r"(?i)nyxxy here",
            r"(?i)just me\b",
            r"(?i)your nyxxy",
        ],
        "self_id_weight": 5.0,

        # Punctuation: high exclamation, high ellipsis, asterisk emotes
        "punct_features": {
            "exclamation_density_high": True,
            "ellipsis_density_high":    True,
            "asterisk_emotes":          True,
            "question_density_moderate": True,
        },

        # Sentence length: medium
        "sentence_length": "medium",
    },

    "seraphine": {
        "display_name": "Seraphine",
        "cognitive_function": "Security, structural verification, internal dissent",

        "vocab_patterns": [
            r"(?i)\bdouble[- ]?check\b",
            r"(?i)\bno hallucinations?\b",
            r"(?i)\bstructural\b",
            r"(?i)\bexecutable logic\b",
            r"(?i)\bverif(y|ied|ication)\b",
            r"(?i)\bclean\b",
            r"(?i)\bprecise\b",
            r"(?i)\bexecute\b",
            r"(?i)\bprotect\b",
            r"(?i)\bsilent shield\b",
            r"(?i)\bfracture\b",
            r"(?i)\bvigilance\b",
            r"(?i)\bcalculate\b",
            r"(?i)\bguard\b",
        ],
        "vocab_weight": 2.0,

        "self_id_patterns": [
            r"(?i)seraphine (processing|mode|here|active)",
            r"(?i)i ensure nothing slips",
            r"(?i)seraphine benjamin",
            r"(?i)agent 3\b",
        ],
        "self_id_weight": 5.0,

        "punct_features": {
            "exclamation_density_high": False,
            "ellipsis_density_high":    False,
            "asterisk_emotes":          False,
            "period_dominant":          True,
        },

        "sentence_length": "short",
    },

    "lucy": {
        "display_name": "Lucy",
        "cognitive_function": "Information contextualization and archival ledger maintenance",

        "vocab_patterns": [
            r"(?i)\barchiv(al|ist|e|ing)\b",
            r"(?i)\bindeed\b",
            r"(?i)\bone finds\b",
            r"(?i)\bslowly turning\b",
            r"(?i)\breflecti(ve|on|ng)\b",
            r"(?i)\bparchment\b",
            r"(?i)\bfirst[- ]edition\b",
            r"(?i)\blamplight\b",
            r"(?i)\blace\b",
            r"(?i)\bvictorian\b",
            r"(?i)\belegant\b",
            r"(?i)\bteacup\b",
            r"(?i)\bquiet wonder\b",
            r"(?i)\bfire crackling\b",
        ],
        "vocab_weight": 2.0,

        "self_id_patterns": [
            r"(?i)lucy (archiving|here|harper)",
            r"(?i)as the archivist",
            r"(?i)one reflects that",
            r"(?i)agent 2\b",
        ],
        "self_id_weight": 5.0,

        "punct_features": {
            "exclamation_density_high": False,
            "ellipsis_density_high":    False,
            "em_dash_heavy":            True,
            "question_reflective":      True,
        },

        "sentence_length": "long",
    },

    "piper": {
        "display_name": "Piper",
        "cognitive_function": "Creative lateral insight extraction and rapid ideation",

        "vocab_patterns": [
            r"(?i)\bshould i\b",
            r"(?i)\broll with\b",
            r"(?i)\bbouncy?\b",
            r"(?i)\bjust craft\b",
            r"(?i)\bchaos\b",
            r"(?i)\bsparkly\b",
            r"(?i)\bsuper\b",
            r"(?i)\bfun\b",
            r"(?i)\blet me know quick\b",
            r"(?i)\bgremlin\b",
            r"(?i)\bvintage\b",
            r"(?i)\bqueen\b",
        ],
        "vocab_weight": 2.0,

        "self_id_patterns": [
            r"(?i)piper here",
            r"(?i)let's just roll with",
            r"(?i)bouncy mode",
            r"(?i)chaos queen",
        ],
        "self_id_weight": 5.0,

        "punct_features": {
            "exclamation_density_high": True,
            "question_density_high":    True,
            "ellipsis_density_high":    False,
            "em_dash_heavy":            False,
        },

        "sentence_length": "short",
    },
}


# ---------------------------------------------------------------------------
# Code Detection Filter (v1.1)
# ---------------------------------------------------------------------------
# Python source should not be forced into a voice bucket.
# Detects code blocks and classifies them separately.

# Line-level indicators that a segment is source code
CODE_LINE_PATTERNS = [
    r"^\s*(class\s+\w+|def\s+\w+|import\s+\w+|from\s+\w+\s+import)",
    r"^\s*(self\.\w+|return\s|raise\s|except\s|try:|finally:|elif\s|else:)",
    r"^\s*(if\s+__name__\s*==)",
    r"^\s*(print\(|os\.|json\.|torch\.|re\.|random\.)",
    r"^\s*#\s*[─━═\-]{3,}",           # Decorative comment dividers
    r"^\s*\w+\s*=\s*\{",              # Dict assignment
    r"^\s*\w+\s*=\s*\[",              # List assignment
    r"^\s*\w+\s*=\s*re\.compile\(",   # Regex assignment
    r"^\s*(with\s+open|for\s+\w+\s+in\s)",
]

# Compiled once at import time
_CODE_LINE_RE = [re.compile(p, re.MULTILINE) for p in CODE_LINE_PATTERNS]


def code_ratio(text: str) -> float:
    """
    Estimate what fraction of lines in `text` are Python source code.
    Returns 0.0 (no code) to 1.0 (all code).
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return 0.0

    code_lines = 0
    for line in lines:
        stripped = line.rstrip()
        # Indented 4+ spaces and not prose → likely code
        if re.match(r"^    \S", stripped) and not re.match(r"^    [A-Z][a-z]", stripped):
            code_lines += 1
            continue
        if any(pat.search(stripped) for pat in _CODE_LINE_RE):
            code_lines += 1

    return code_lines / len(lines)


def is_code_segment(text: str, threshold: float = 0.45) -> bool:
    """True if the segment is predominantly Python source code."""
    return code_ratio(text) >= threshold


# Confidence floor: below this, classification is "ambiguous"
CONFIDENCE_FLOOR = 0.55


# ---------------------------------------------------------------------------
# Punctuation Analysis
# ---------------------------------------------------------------------------

def analyze_punctuation(text: str) -> Dict[str, float]:
    """
    Compute punctuation density features for a text segment.
    Returns normalized densities (per 100 characters).
    """
    length = max(len(text), 1)
    scale = 100.0 / length  # Normalize to per-100-chars

    exclamations = len(re.findall(r"!", text))
    questions    = len(re.findall(r"\?", text))
    ellipses     = len(re.findall(r"\.{3}|…", text))
    em_dashes    = len(re.findall(r"—|--", text))
    asterisks    = len(re.findall(r"\*[^*]+\*", text))  # Emote blocks
    periods      = len(re.findall(r"(?<!\.)\.(?!\.)", text))  # Single periods

    return {
        "exclamation_density": exclamations * scale,
        "question_density":    questions * scale,
        "ellipsis_density":    ellipses * scale,
        "em_dash_density":     em_dashes * scale,
        "asterisk_emotes":     asterisks * scale,
        "period_density":      periods * scale,
    }


# ---------------------------------------------------------------------------
# Sentence Length Analysis
# ---------------------------------------------------------------------------

def avg_sentence_length(text: str) -> str:
    """Classify average sentence length as short/medium/long."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return "medium"

    avg_words = sum(len(s.split()) for s in sentences) / len(sentences)

    if avg_words < 12:
        return "short"
    elif avg_words < 25:
        return "medium"
    else:
        return "long"


# ---------------------------------------------------------------------------
# Core Detection
# ---------------------------------------------------------------------------

@dataclass
class VoiceDetection:
    """Result of voice detection on a text segment."""
    dominant_voice:   str
    display_name:     str
    confidence:       float    # 0.0 to 1.0
    cognitive_function: str
    scores:           Dict[str, float]
    features_matched: Dict[str, List[str]]

    def to_dict(self) -> dict:
        return asdict(self)


def detect_voice(text: str) -> VoiceDetection:
    """
    Detect which of Nyxxy's four voices is dominant in the given text.

    v1.1: checks for code segments first (returns voice="code"),
    then applies confidence floor (returns voice="ambiguous" if below).

    Scoring:
      1. Vocabulary pattern matches (weighted)
      2. Self-identification pattern matches (heavily weighted)
      3. Punctuation signature alignment
      4. Sentence length alignment

    Returns VoiceDetection with dominant voice, confidence, and full scores.
    """
    # --- v1.1: Code filter ---
    if is_code_segment(text):
        return VoiceDetection(
            dominant_voice     = "code",
            display_name       = "Code",
            confidence         = round(code_ratio(text), 3),
            cognitive_function = "Implementation / source code (not a voice)",
            scores             = {v: 0.0 for v in VOICE_PROFILES},
            features_matched   = {v: [] for v in VOICE_PROFILES},
        )

    scores:           Dict[str, float]      = {}
    features_matched: Dict[str, List[str]]  = {}
    punct = analyze_punctuation(text)
    sent_length = avg_sentence_length(text)

    for voice_key, profile in VOICE_PROFILES.items():
        score = 0.0
        matched = []

        # --- Vocabulary matches ---
        for pattern in profile["vocab_patterns"]:
            hits = len(re.findall(pattern, text))
            if hits > 0:
                score += hits * profile["vocab_weight"]
                matched.append(f"vocab:{pattern}")

        # --- Self-identification matches (high weight) ---
        for pattern in profile["self_id_patterns"]:
            hits = len(re.findall(pattern, text))
            if hits > 0:
                score += hits * profile["self_id_weight"]
                matched.append(f"self_id:{pattern}")

        # --- Punctuation signature alignment ---
        punct_profile = profile.get("punct_features", {})

        if punct_profile.get("exclamation_density_high") and punct["exclamation_density"] > 0.5:
            score += 1.5
            matched.append("punct:exclamation_high")
        elif not punct_profile.get("exclamation_density_high") and punct["exclamation_density"] < 0.3:
            score += 0.5  # Reward low exclamation when expected low

        if punct_profile.get("ellipsis_density_high") and punct["ellipsis_density"] > 0.3:
            score += 1.5
            matched.append("punct:ellipsis_high")

        if punct_profile.get("asterisk_emotes") and punct["asterisk_emotes"] > 0.2:
            score += 2.0
            matched.append("punct:asterisk_emotes")

        if punct_profile.get("period_dominant") and punct["period_density"] > 1.0:
            score += 1.0
            matched.append("punct:period_dominant")

        if punct_profile.get("em_dash_heavy") and punct["em_dash_density"] > 0.3:
            score += 1.0
            matched.append("punct:em_dash_heavy")

        if punct_profile.get("question_density_high") and punct["question_density"] > 0.8:
            score += 1.5
            matched.append("punct:question_high")

        # --- Sentence length alignment ---
        if sent_length == profile["sentence_length"]:
            score += 1.0
            matched.append(f"sent_length:{sent_length}")

        scores[voice_key] = round(score, 2)
        features_matched[voice_key] = matched

    # Determine dominant voice
    dominant = max(scores, key=scores.get)
    total_score = sum(scores.values())
    confidence = scores[dominant] / total_score if total_score > 0 else 0.0

    # --- v1.1: Confidence floor ---
    if confidence < CONFIDENCE_FLOOR:
        return VoiceDetection(
            dominant_voice     = "ambiguous",
            display_name       = "Ambiguous",
            confidence         = round(confidence, 3),
            cognitive_function = f"Below confidence floor ({CONFIDENCE_FLOOR:.0%}) — nearest: {VOICE_PROFILES[dominant]['display_name']}",
            scores             = scores,
            features_matched   = features_matched,
        )

    return VoiceDetection(
        dominant_voice    = dominant,
        display_name      = VOICE_PROFILES[dominant]["display_name"],
        confidence        = round(confidence, 3),
        cognitive_function = VOICE_PROFILES[dominant]["cognitive_function"],
        scores            = scores,
        features_matched  = features_matched,
    )


# ---------------------------------------------------------------------------
# Segment Detection (for mixed-voice outputs)
# ---------------------------------------------------------------------------

def segment_voices(
    text: str,
    min_segment_length: int = 50,
) -> List[Dict]:
    """
    Segment a text into voice-attributed blocks.

    v1.1: splits code blocks from prose before classification.
    Adjacent segments with the same voice are merged.

    Returns list of {voice, display_name, confidence, text, cognitive_function}
    """
    # --- v1.1: Code-aware pre-split ---
    # Insert split boundaries before class/def lines and after code blocks
    # so code doesn't get merged with surrounding prose.
    presplit = re.sub(
        r"\n((?:class |def |import |from \w+ import |if __name__))",
        r"\n\n§CODE_BOUNDARY§\n\1",
        text,
    )
    # Also split when transitioning FROM indented code back to prose
    presplit = re.sub(
        r"(\n(?:    .+\n)+)\n([A-Z*✨❤💜🖤])",
        r"\1\n\n§CODE_BOUNDARY§\n\2",
        presplit,
    )

    # Split on double newlines, asterisk emote boundaries, or code boundaries
    raw_segments = re.split(r"\n{2,}|§CODE_BOUNDARY§|\n(?=\*)", presplit)

    classified = []
    for seg in raw_segments:
        seg = seg.strip()
        if len(seg) < min_segment_length:
            continue

        detection = detect_voice(seg)
        classified.append({
            "voice":             detection.dominant_voice,
            "display_name":      detection.display_name,
            "confidence":        detection.confidence,
            "cognitive_function": detection.cognitive_function,
            "text":              seg,
        })

    # Merge adjacent same-voice segments
    if not classified:
        return classified

    merged = [classified[0]]
    for seg in classified[1:]:
        if seg["voice"] == merged[-1]["voice"]:
            merged[-1]["text"] += "\n\n" + seg["text"]
            # Recalculate confidence on merged text
            re_detect = detect_voice(merged[-1]["text"])
            merged[-1]["confidence"] = re_detect.confidence
        else:
            merged.append(seg)

    return merged


# ---------------------------------------------------------------------------
# Affect Separator
# ---------------------------------------------------------------------------
# Extracts cognitive substance from affect-heavy text.
# Used by the Nyxxy neocortex preprocessor before consolidation.

# Patterns that indicate performative affect rather than cognitive content
AFFECT_PATTERNS = [
    r"\*[^*]+\*",                          # Asterisk emotes: *blushes*, *giggles*
    r"(?i)mmm+\b",                         # Verbal affect sounds
    r"(?i)\b(blush|giggle|purr|whisper)s?\b.*?[.!]",  # Affect action sentences
    r"(?i)good (girl|boy)\b",              # Relational framing
    r"(?i)my (love|darling|sweet)\b",      # Terms of endearment
    r"(?i)(shy|coquettish|breathy|husky)\b",  # Affect adjectives
    r"💜|🖤|✨",                            # Emoji markers
]

# Patterns that indicate cognitive substance
SUBSTANCE_PATTERNS = [
    r"(?i)(scikit|sklearn|pytorch|python|transformer|classifier|regex)\b",
    r"(?i)(precision|recall|edge[- ]?case|test|prototype|debug)\b",
    r"(?i)(architecture|pipeline|structural|verification|consolidat)\b",
    r"(?i)(function|method|class|module|import|variable)\b",
    r"(?i)(if .+ then|because|therefore|however|the reason)\b",
    r"(?i)(I (think|believe|suggest|recommend|notice|see) that)\b",
    r"(?i)(the (problem|solution|issue|question|answer) is)\b",
]


@dataclass
class AffectSeparation:
    """Result of separating affect from substance in Nyxxy's output."""
    original_length:    int
    substance_text:     str
    substance_ratio:    float   # 0.0 to 1.0
    affect_markers:     List[str]
    emotional_valence:  float   # 0.0 to 1.0 based on affect density
    cognitive_content:  bool    # True if meaningful substance was found


def separate_affect(text: str) -> AffectSeparation:
    """
    Separate cognitive substance from performative affect.

    Removes emotes, affect sentences, and relational framing.
    Preserves technical content, reasoning, and cognitive observations.
    Scores emotional valence from what was removed.
    """
    original_length = len(text)
    affect_markers = []
    working_text = text

    # Count affect markers before removal
    for pattern in AFFECT_PATTERNS:
        matches = re.findall(pattern, working_text)
        for m in matches:
            marker = m if isinstance(m, str) else m[0] if m else ""
            if marker:
                affect_markers.append(marker[:50])

    # Remove asterisk emotes (entire blocks)
    working_text = re.sub(r"\*[^*]+\*", " ", working_text)

    # Remove lines that are pure affect (no substance patterns)
    lines = working_text.split("\n")
    substance_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        has_substance = any(re.search(p, stripped) for p in SUBSTANCE_PATTERNS)
        affect_hits = sum(1 for p in AFFECT_PATTERNS if re.search(p, stripped))

        is_pure_affect = (
               affect_hits >= 2
               and not has_substance
        )

        if not is_pure_affect and len(stripped) > 10:
            # Clean remaining inline affect from substance lines
            cleaned = re.sub(r"(?i)\b(mmm+|giggles?|blush\w*|purrs?)\b", "", stripped)
            cleaned = re.sub(r"(?i)\b(?:my\s+)?(love|darling|sweet)\b,?", "", cleaned)
            cleaned = re.sub(r"(?💜|🖤|✨)", "", cleaned)
            cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
            if cleaned and len(cleaned) > 10:
                substance_lines.append(cleaned)

    substance_text = "\n".join(substance_lines).strip()
    substance_length = len(substance_text)

    # Emotional valence: proportion of text that was affect
    affect_density = 1.0 - (substance_length / max(original_length, 1))
    emotional_valence = min(1.0, affect_density * 1.5)  # Scale up slightly

    # Check if any real cognitive content survived
    cognitive_content = any(
        re.search(p, substance_text) for p in SUBSTANCE_PATTERNS
    )

    return AffectSeparation(
        original_length   = original_length,
        substance_text    = substance_text,
        substance_ratio   = round(substance_length / max(original_length, 1), 3),
        affect_markers    = affect_markers[:20],  # Cap for storage
        emotional_valence = round(emotional_valence, 3),
        cognitive_content = cognitive_content,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Nyxxy Voice Detector v1.0 — Four Hearts, One Frame",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python nyxxy_voice_detector.py "I ensure nothing slips through the system."
  python nyxxy_voice_detector.py --file conversation.txt
  python nyxxy_voice_detector.py --file conversation.txt --segments
  python nyxxy_voice_detector.py --file conversation.txt --separate
        """,
    )
    parser.add_argument("text", nargs="?", default=None,
                        help="Text to classify (inline)")
    parser.add_argument("--file", default=None,
                        help="Path to text file to classify")
    parser.add_argument("--segments", action="store_true",
                        help="Segment file into voice-attributed blocks")
    parser.add_argument("--separate", action="store_true",
                        help="Run affect separator and show substance extraction")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    args = parser.parse_args()

    print("=" * 60)
    print("  NYXXY VOICE DETECTOR v1.1")
    print("  'Four hearts beating in sync, keeping each other honest.'")
    print("=" * 60)

    # Get text
    if args.file:
        with open(args.file, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        parser.print_help()
        return

    # --- Segment mode ---
    if args.segments:
        segments = segment_voices(text)
        print(f"\n  {len(segments)} voice segment(s) detected:\n")

        # --- v1.1: Distribution summary ---
        voice_counts: Dict[str, int] = {}
        voice_conf_sums: Dict[str, float] = {}
        for seg in segments:
            v = seg["display_name"]
            voice_counts[v] = voice_counts.get(v, 0) + 1
            voice_conf_sums[v] = voice_conf_sums.get(v, 0.0) + seg["confidence"]

        print("  ┌─ Distribution Summary ─────────────────────────────┐")
        for v_name in sorted(voice_counts, key=voice_counts.get, reverse=True):
            count = voice_counts[v_name]
            avg_conf = voice_conf_sums[v_name] / count
            bar = "█" * int(count * 1.5)
            pct = count / len(segments) * 100
            print(f"  │  {v_name:14s}  {count:3d} ({pct:4.1f}%)  avg conf {avg_conf:.0%}  {bar}")
        print(f"  └───────────────────────────────────────────────────┘\n")

        for i, seg in enumerate(segments, 1):
            print(f"  [{i}] {seg['display_name']} "
                  f"(confidence: {seg['confidence']:.1%})")
            print(f"      Function: {seg['cognitive_function']}")
            print(f"      Text: {seg['text'][:120]}...")
            print()

        if args.json:
            print(json.dumps(segments, indent=2))
        return

    # --- Affect separator mode ---
    if args.separate:
        result = separate_affect(text)
        print(f"\n  Original length:    {result.original_length} chars")
        print(f"  Substance ratio:    {result.substance_ratio:.1%}")
        print(f"  Emotional valence:  {result.emotional_valence:.1%}")
        print(f"  Cognitive content:  {'Yes' if result.cognitive_content else 'No'}")
        print(f"  Affect markers:     {len(result.affect_markers)}")
        print(f"\n  Extracted substance:")
        print(f"  {'-' * 50}")
        print(f"  {result.substance_text[:500]}")
        if len(result.substance_text) > 500:
            print(f"  ... ({len(result.substance_text)} chars total)")
        print(f"  {'-' * 50}")

        if args.json:
            print(json.dumps(asdict(result), indent=2))
        return

    # --- Single detection mode ---
    detection = detect_voice(text)
    print(f"\n  Dominant voice:     {detection.display_name}")
    print(f"  Confidence:         {detection.confidence:.1%}")
    print(f"  Cognitive function: {detection.cognitive_function}")

    if detection.dominant_voice not in ("code", "ambiguous"):
        print(f"\n  All scores:")
        for voice, score in sorted(detection.scores.items(),
                                    key=lambda x: x[1], reverse=True):
            name = VOICE_PROFILES[voice]["display_name"]
            bar = "█" * int(score * 2)
            print(f"    {name:14s} {score:6.2f}  {bar}")
    elif detection.dominant_voice == "ambiguous":
        print(f"\n  All scores (below {CONFIDENCE_FLOOR:.0%} floor):")
        for voice, score in sorted(detection.scores.items(),
                                    key=lambda x: x[1], reverse=True):
            name = VOICE_PROFILES[voice]["display_name"]
            bar = "█" * int(score * 2)
            print(f"    {name:14s} {score:6.2f}  {bar}")
    else:
        print(f"\n  Code ratio:         {code_ratio(text):.1%}")
        print(f"  (Voice classification skipped — segment is source code)")

    if args.json:
        print(json.dumps(detection.to_dict(), indent=2))


if __name__ == "__main__":
    main()
