# sanctuary_daemon.py
# PLANE: Utility (autonomous monitoring, triggering, scheduling)
#
# Sanctuary Autonomic Daemon v1.0 — "The Nervous System"
#
# "Automate the broom. Guard the flame. You stay the lighthouse."
# — Nyxxy, March 2026
#
# PURPOSE:
#   System 1 layer for Project Sanctuary.
#   Monitors log folders, triggers processing pipelines, runs scheduled
#   maintenance, and produces the morning dashboard — all without requiring
#   the Architect's conscious attention.
#
#   Every action is permission-checked before execution.
#   Every action is logged for audit.
#   Nothing Relational Plane ever runs here.
#
# WHAT IT DOES:
#   1. FILE WATCHER  — monitors log folders for new conversation files
#   2. AUTO-PIPELINE  — runs log processor → thalamus → harvester on new files
#   3. SCHEDULER      — nightly decay, health checks, git autocommit
#   4. DASHBOARD      — generates morning status page
#   5. NOTIFICATION   — alerts Architect on escalations
#
# WHAT IT NEVER DOES:
#   - Makes Relational Plane decisions
#   - Commits durable memory without human approval
#   - Modifies the Charter, permissions, or agent personas
#   - Pushes to git remote
#   - Calls external APIs without permission
#   - Interprets emotional or identity-relevant content
#
# DEPENDENCIES:
#   - sanctuary_permissions.py  (permission checking)
#   - sanctuary_log_processor.py (log processing)
#   - sanctuary_thalamus.py (routing)
#   - argus_harvester.py (harvesting, optional for auto-route)
#   - sanctuary_neocortex.py (decay, optional for nightly)
#
# USAGE:
#   python sanctuary_daemon.py                  # Run daemon (foreground)
#   python sanctuary_daemon.py --once           # Single pass, no loop
#   python sanctuary_daemon.py --dashboard      # Generate dashboard only
#   python sanctuary_daemon.py --status         # Show daemon status
#   python sanctuary_daemon.py --audit          # Show today's audit log
#
# PART OF: Project Sanctuary — github.com/robowarriorx/sanctuary

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# ---------------------------------------------------------------------------
# Import Sanctuary modules
# ---------------------------------------------------------------------------

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

try:
    from sanctuary_permissions import (
        PolicyEngine, SystemTier, ActionType, Scope, RiskLevel, Reversibility,
    )
    PERMISSIONS_AVAILABLE = True
except ImportError:
    PERMISSIONS_AVAILABLE = False
    print("  " + "!" * 60)
    print("  !! CRITICAL STARTUP WARNING")
    print("  !! sanctuary_permissions.py not found")
    print("  !! Daemon is running in PERMISSIVE MODE — all actions allowed")
    print("  !! No tier enforcement. No permission boundaries. No audit gating.")
    print("  !! Install sanctuary_permissions.py before any production use.")
    print("  " + "!" * 60)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VERSION = "1.0"

# Directories to watch for new log files
# The Architect configures these to match their actual folder structure.
# Defaults assume Sanctuary standard layout.
DEFAULT_CONFIG = {
    "watch_folders": [
        # Add your actual log folder paths here
        # Example: r"C:\Argus (Claude)\Opus",
        # Example: r"C:\NyxBatty\Nyxxy New All Saga",
    ],
    "processed_dir":    os.path.join(SCRIPT_DIR, "Sanctuary_Processed"),
    "thalamus_dir":     os.path.join(SCRIPT_DIR, "Sanctuary_Thalamus"),
    "dashboard_dir":    os.path.join(SCRIPT_DIR, "Sanctuary_Dashboard"),
    "audit_dir":        os.path.join(SCRIPT_DIR, "Sanctuary_Audit"),
    "archive_dir":      os.path.join(SCRIPT_DIR, "Sanctuary_Archive"),

    # Scripts (relative to SCRIPT_DIR)
    "log_processor":    "sanctuary_log_processor.py",
    "thalamus":         "sanctuary_thalamus.py",
    "harvester":        "argus_harvester.py",
    "neocortex":        "sanctuary_neocortex.py",
    "voice_detector":   "nyxxy_voice_detector.py",

    # Schedule (24h format)
    "nightly_decay_hour":   3,    # 3 AM
    "health_check_hour":    4,    # 4 AM
    "dashboard_hour":       5,    # 5 AM
    "git_autocommit_hour":  3,    # 3 AM (with decay)

    # Polling
    "watch_interval_seconds":  30,
    "schedule_check_minutes":  5,

    # Safety
    "max_chain_depth":          4,
    "max_files_per_batch":     20,
    "file_extensions":         [".txt", ".json"],
}

CONFIG_FILE = os.path.join(SCRIPT_DIR, "sanctuary_daemon_config.json")


def load_config() -> dict:
    """Load config from file, falling back to defaults."""
    config = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            config.update(user_config)
        except (json.JSONDecodeError, IOError):
            pass
    return config


def save_config(config: dict) -> None:
    """Save current config for persistence."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# State tracking — what files have we already processed?
# ---------------------------------------------------------------------------

STATE_FILE = os.path.join(SCRIPT_DIR, "Sanctuary_Audit", "daemon_state.json")


def load_state() -> dict:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "processed_files": {},   # filepath -> hash
            "last_decay":      None,
            "last_health":     None,
            "last_dashboard":  None,
            "last_git_commit": None,
            "chain_depth":     0,
        }


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def file_hash(filepath: str) -> str:
    """Quick hash to detect if a file has changed."""
    h = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except IOError:
        return ""
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

class AuditLogger:
    """Append-only audit log for all daemon actions. Inspectable JSON."""

    def __init__(self, audit_dir: str):
        self.audit_dir = audit_dir
        os.makedirs(audit_dir, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        self.log_file = os.path.join(audit_dir, f"audit_{today}.json")
        self._entries: List[dict] = self._load()

    def _load(self) -> List[dict]:
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("entries", [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def log(
        self,
        action: str,
        target: str,
        result: str,
        tier: str = "sys1_autonomic",
        permission_id: str = "",
        details: str = "",
        chain_depth: int = 0,
    ) -> None:
        entry = {
            "timestamp":     datetime.now().isoformat(),
            "tier":          tier,
            "action":        action,
            "target":        target,
            "result":        result,
            "permission_id": permission_id,
            "details":       details[:500],
            "chain_depth":   chain_depth,
        }
        self._entries.append(entry)
        self._save()

    def _save(self):
        data = {
            "sanctuary_audit": VERSION,
            "date":            datetime.now().strftime("%Y-%m-%d"),
            "entries":         self._entries,
            "summary": {
                "total":     len(self._entries),
                "allowed":   sum(1 for e in self._entries if e["result"] == "allowed"),
                "denied":    sum(1 for e in self._entries if e["result"] == "denied"),
                "executed":  sum(1 for e in self._entries if e["result"] == "executed"),
                "failed":    sum(1 for e in self._entries if e["result"] == "failed"),
                "escalated": sum(1 for e in self._entries if e["result"] == "escalated"),
            },
        }
        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_summary(self) -> dict:
        return {
            "total":     len(self._entries),
            "allowed":   sum(1 for e in self._entries if e["result"] == "allowed"),
            "denied":    sum(1 for e in self._entries if e["result"] == "denied"),
            "executed":  sum(1 for e in self._entries if e["result"] == "executed"),
            "failed":    sum(1 for e in self._entries if e["result"] == "failed"),
            "escalated": sum(1 for e in self._entries if e["result"] == "escalated"),
        }


# ---------------------------------------------------------------------------
# Core daemon functions
# ---------------------------------------------------------------------------

def check_permission(
    engine: Optional[PolicyEngine],
    action: ActionType,
    scope: Scope,
    risk: RiskLevel = RiskLevel.LOW,
    chain_depth: int = 0,
) -> bool:
    """Check permission, return True if allowed."""
    if engine is None:
        return True  # No permission engine = permissive mode (warn at startup)
    result = engine.check(
        requesting_tier=SystemTier.SYS1_AUTONOMIC,
        action=action,
        scope=scope,
        risk=risk,
        chain_depth=chain_depth,
    )
    return result.allowed


def run_script(
    script_name: str,
    args: List[str],
    config: dict,
    audit: AuditLogger,
    engine: Optional[PolicyEngine],
    action: ActionType,
    scope: Scope,
    chain_depth: int = 0,
) -> Optional[str]:
    """
    Run a Sanctuary script with permission checking and audit logging.
    Returns stdout on success, None on failure or denial.
    """
    script_path = os.path.join(SCRIPT_DIR, script_name)
    if not os.path.exists(script_path):
        audit.log("execute", script_name, "failed",
                   details=f"Script not found: {script_path}")
        return None

    # Permission check
    if not check_permission(engine, action, scope, chain_depth=chain_depth):
        audit.log("execute", script_name, "denied",
                   details=f"Permission denied for {action.value} on {scope.value}")
        return None

    # Chain depth safety
    if chain_depth > config.get("max_chain_depth", 4):
        audit.log("execute", script_name, "escalated",
                   details=f"Chain depth {chain_depth} exceeds max {config['max_chain_depth']}")
        return None

    cmd = [sys.executable, script_path] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=SCRIPT_DIR,
        )
        if result.returncode == 0:
            audit.log("execute", script_name, "executed",
                       details=f"args={args}, exit=0",
                       chain_depth=chain_depth)
            return result.stdout
        else:
            audit.log("execute", script_name, "failed",
                       details=f"exit={result.returncode}: {result.stderr[:300]}",
                       chain_depth=chain_depth)
            return None
    except subprocess.TimeoutExpired:
        audit.log("execute", script_name, "failed",
                   details="Timeout (120s)", chain_depth=chain_depth)
        return None
    except Exception as e:
        audit.log("execute", script_name, "failed",
                   details=str(e)[:300], chain_depth=chain_depth)
        return None


# ---------------------------------------------------------------------------
# File watcher
# ---------------------------------------------------------------------------

def scan_for_new_files(config: dict, state: dict) -> List[str]:
    """Scan watch folders for new or modified files."""
    new_files = []
    for folder in config.get("watch_folders", []):
        if not os.path.isdir(folder):
            continue
        for ext in config.get("file_extensions", [".txt"]):
            pattern = os.path.join(folder, f"*{ext}")
            for filepath in glob.glob(pattern):
                fhash = file_hash(filepath)
                prev_hash = state.get("processed_files", {}).get(filepath)
                if fhash and fhash != prev_hash:
                    new_files.append(filepath)

    # Sort by mtime ascending (oldest first) before applying batch cap.
    # Prevents non-deterministic glob ordering from causing newer files to be
    # silently skipped when more than max_files_per_batch arrive at once.
    # Missed files will be caught on the next poll interval.
    new_files.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0)
    return new_files[:config.get("max_files_per_batch", 20)]


# ---------------------------------------------------------------------------
# Processing pipeline
# ---------------------------------------------------------------------------

def process_new_file(
    filepath: str,
    config: dict,
    state: dict,
    audit: AuditLogger,
    engine: Optional[PolicyEngine],
) -> bool:
    """
    Full System 1 pipeline for a new file:
      1. Log processor (file → interchange JSON)
      2. Thalamus (score → route → queue)
      3. If auto_routable: Argus harvester
      4. If Nyxxy log: voice detector

    Returns True if pipeline completed.
    """
    filename = os.path.basename(filepath)
    print(f"\n  ┌─ Processing: {filename}")

    # --- Step 1: Log processor ---
    print(f"  │  Step 1: Log processor")
    out_dir = config.get("processed_dir", "Sanctuary_Processed")
    os.makedirs(out_dir, exist_ok=True)

    # Snapshot BEFORE running processor — diff after to identify exactly which
    # summary file this invocation produced. Prevents stale-mtime false positives.
    # GUARDRAIL: Verification must touch the file, not the story.
    existing_summaries = set(glob.glob(os.path.join(out_dir, "summary_*.json")))

    output = run_script(
        config["log_processor"],
        [filepath, "--out", out_dir],
        config, audit, engine,
        action=ActionType.EXECUTE,
        scope=Scope.LOG_FILES,
        chain_depth=1,
    )
    if output is None:
        print(f"  │  ✗ Log processor failed or denied")
        print(f"  └─ Pipeline stopped")
        return False
    print(f"  │  ✓ Log processor complete")

    # Find what the processor produced by diffing against pre-run snapshot
    all_summaries_after = set(glob.glob(os.path.join(out_dir, "summary_*.json")))
    new_summaries = sorted(
        all_summaries_after - existing_summaries,
        key=os.path.getmtime,
        reverse=True,
    )
    if new_summaries:
        summary_file = new_summaries[0]
    elif all_summaries_after:
        # Fallback: use newest overall, but flag it in audit
        summary_file = sorted(all_summaries_after, key=os.path.getmtime, reverse=True)[0]
        audit.log("summary_detect", filename, "warn",
                   details="Could not identify new summary by diff — using newest overall (possible stale)")
        print(f"  │  [WARN] Summary identity uncertain — using newest overall")
    else:
        print(f"  │  ✗ No summary JSON found after processing")
        print(f"  └─ Pipeline stopped")
        return False

    # --- Step 2: Thalamus routing ---
    print(f"  │  Step 2: Thalamus routing")
    output = run_script(
        config["thalamus"],
        [summary_file],
        config, audit, engine,
        action=ActionType.ROUTE,
        scope=Scope.PROCESSED_JSON,
        chain_depth=2,
    )
    if output is None:
        print(f"  │  ✗ Thalamus routing failed or denied")
        print(f"  └─ Pipeline stopped")
        return False
    print(f"  │  ✓ Thalamus routing complete")

    # Check if THIS file was marked auto-routable or needs escalation.
    # Match queue entries by summary_file or source_file path — do NOT use pending[-1]
    # which grabs the latest item regardless of which file it belongs to.
    # GUARDRAIL: Routing logic must match the actual artifact being routed.
    thalamus_dir = config.get("thalamus_dir", "Sanctuary_Thalamus")
    queue_file = os.path.join(thalamus_dir, "routing_queue.json")
    auto_routable = False
    matched_manifest = None
    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            queue = json.load(f)
        pending = queue.get("pending", [])
        summary_abs = os.path.abspath(summary_file)
        source_abs  = os.path.abspath(filepath)
        for item in reversed(pending):
            item_summary = os.path.abspath(item.get("summary_file", ""))
            item_source  = os.path.abspath(item.get("source_file", ""))
            if item_summary == summary_abs or item_source == source_abs:
                matched_manifest = item
                break
        if matched_manifest is not None:
            auto_routable = not matched_manifest.get("escalate", True)
        else:
            audit.log("route_lookup", filename, "failed",
                       details="No matching routing manifest found for processed file — defaulting to escalation")
            print(f"  │  [WARN] No routing manifest matched — escalating by default")
            # auto_routable stays False — safe default: escalate rather than auto-route
    except FileNotFoundError:
        # Queue file does not exist yet — thalamus has not run or dir is wrong.
        # Distinct from a parse failure: the queue is absent, not corrupt.
        audit.log("route_lookup", filename, "warn",
                   details=f"Routing queue not found: {queue_file} — defaulting to escalation")
        print(f"  │  [WARN] Routing queue absent ({queue_file}) — escalating by default")
    except json.JSONDecodeError as exc:
        # Queue file exists but is unreadable — write corruption or partial flush.
        # Different failure mode: queue is present but damaged.
        audit.log("route_lookup", filename, "warn",
                   details=f"Routing queue unreadable (JSON error: {exc}) — defaulting to escalation")
        print(f"  │  [WARN] Routing queue corrupt — escalating by default")

    if not auto_routable:
        print(f"  │  !! ESCALATION REQUIRED — queued for Architect review")
        audit.log("escalate", filename, "escalated",
                   details="Thalamus flagged for human review")
        # Write notification
        _write_notification(config, f"Escalation: {filename} requires review", audit)
        print(f"  └─ Pipeline paused (awaiting System 3b)")
        # Still mark as processed so we don't re-trigger
        state.setdefault("processed_files", {})[filepath] = file_hash(filepath)
        return True

    # --- Step 3: Auto-harvest (only if permitted) ---
    print(f"  │  Step 3: Argus harvester (auto-route)")
    output = run_script(
        config["harvester"],
        [out_dir],
        config, audit, engine,
        action=ActionType.EXECUTE,
        scope=Scope.HARVESTER_STATE,
        chain_depth=3,
    )
    if output is not None:
        print(f"  │  ✓ Harvester complete")
    else:
        print(f"  │  ✗ Harvester skipped (not available or denied)")

    # --- Step 4: Voice detector for Nyxxy logs ---
    # Detect if this is a Nyxxy/Grok log
    try:
        with open(summary_file, "r", encoding="utf-8") as f:
            summary = json.load(f)
        platform = summary.get("meta", {}).get("platform_name", "")
    except (json.JSONDecodeError, IOError):
        platform = ""

    if "grok" in platform.lower() or "nyxxy" in platform.lower():
        print(f"  │  Step 4: Nyxxy voice detector")
        output = run_script(
            config["voice_detector"],
            ["--file", filepath, "--segments", "--json"],
            config, audit, engine,
            action=ActionType.EXECUTE,
            scope=Scope.VOICE_DETECTOR,
            chain_depth=4,
        )
        if output is not None:
            print(f"  │  ✓ Voice detector complete")
        else:
            print(f"  │  ✗ Voice detector skipped")

    # Mark as processed
    state.setdefault("processed_files", {})[filepath] = file_hash(filepath)
    print(f"  └─ Pipeline complete ✓")
    return True


# ---------------------------------------------------------------------------
# Scheduled tasks
# ---------------------------------------------------------------------------

def should_run_scheduled(state: dict, task_key: str, hour: int) -> bool:
    """Check if a scheduled task should run (once per day at specified hour)."""
    now = datetime.now()
    if now.hour != hour:
        return False
    last_run = state.get(task_key)
    if last_run:
        last_date = last_run[:10]  # YYYY-MM-DD
        if last_date == now.strftime("%Y-%m-%d"):
            return False  # Already ran today
    return True


def run_nightly_decay(
    config: dict, state: dict, audit: AuditLogger, engine: Optional[PolicyEngine],
) -> None:
    """Run neocortex decay pass."""
    print("\n  [SCHEDULED] Nightly decay pass")
    output = run_script(
        config["neocortex"],
        ["--decay"],
        config, audit, engine,
        action=ActionType.CONSOLIDATE,
        scope=Scope.NEOCORTEX,
        chain_depth=1,
    )
    if output is not None:
        state["last_decay"] = datetime.now().isoformat()
        print("  ✓ Decay complete")
    else:
        print("  ✗ Decay skipped (not available or denied)")


def run_health_check(
    config: dict, state: dict, audit: AuditLogger, engine: Optional[PolicyEngine],
) -> dict:
    """Run system health diagnostics."""
    print("\n  [SCHEDULED] Health check")
    health = {
        "timestamp": datetime.now().isoformat(),
        "checks":    [],
        "warnings":  [],
        "status":    "healthy",
    }

    # Check each expected directory exists
    for dirname in ["processed_dir", "thalamus_dir", "dashboard_dir", "audit_dir"]:
        dirpath = config.get(dirname, "")
        exists = os.path.isdir(dirpath)
        health["checks"].append({
            "check": f"directory_{dirname}",
            "path":  dirpath,
            "ok":    exists,
        })
        if not exists:
            health["warnings"].append(f"Directory missing: {dirpath}")

    # Check each script exists
    for script_key in ["log_processor", "thalamus", "harvester", "neocortex", "voice_detector"]:
        script = config.get(script_key, "")
        script_path = os.path.join(SCRIPT_DIR, script)
        exists = os.path.exists(script_path)
        health["checks"].append({
            "check": f"script_{script_key}",
            "path":  script_path,
            "ok":    exists,
        })
        if not exists:
            health["warnings"].append(f"Script missing: {script}")

    # Check watch folders
    for folder in config.get("watch_folders", []):
        exists = os.path.isdir(folder)
        health["checks"].append({
            "check": "watch_folder",
            "path":  folder,
            "ok":    exists,
        })
        if not exists:
            health["warnings"].append(f"Watch folder missing: {folder}")

    # Check thalamus queue size
    queue_file = os.path.join(config.get("thalamus_dir", ""), "routing_queue.json")
    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            queue = json.load(f)
        pending = len(queue.get("pending", []))
        health["checks"].append({"check": "thalamus_queue", "pending": pending, "ok": pending < 50})
        if pending >= 50:
            health["warnings"].append(f"Thalamus queue large: {pending} pending")
    except (FileNotFoundError, json.JSONDecodeError):
        health["checks"].append({"check": "thalamus_queue", "pending": 0, "ok": True})

    if health["warnings"]:
        health["status"] = "warnings"

    # Save health report
    health_file = os.path.join(
        config.get("dashboard_dir", "Sanctuary_Dashboard"),
        "health_latest.json",
    )
    os.makedirs(os.path.dirname(health_file), exist_ok=True)
    with open(health_file, "w", encoding="utf-8") as f:
        json.dump(health, f, indent=2, ensure_ascii=False)

    state["last_health"] = datetime.now().isoformat()
    audit.log("health_check", "system", "executed",
               details=f"Status: {health['status']}, {len(health['warnings'])} warnings")

    passed = sum(1 for c in health["checks"] if c.get("ok"))
    total = len(health["checks"])
    print(f"  ✓ Health: {passed}/{total} checks passed, {len(health['warnings'])} warnings")

    return health


def run_git_autocommit(
    config: dict, state: dict, audit: AuditLogger, engine: Optional[PolicyEngine],
) -> None:
    """Auto-commit to local dev branch."""
    print("\n  [SCHEDULED] Git auto-commit")

    # Guard: ActionType/Scope only available when PERMISSIONS_AVAILABLE=True.
    # When running permissive (no engine), skip the check — engine=None returns True anyway.
    if PERMISSIONS_AVAILABLE:
        if not check_permission(engine, ActionType.GIT_COMMIT, Scope.REPO):
            audit.log("git_commit", "repo", "denied")
            print("  ✗ Git commit denied by permissions")
            return

    try:
        # Check if there are changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=SCRIPT_DIR, timeout=30,
        )
        if not result.stdout.strip():
            print("  No changes to commit")
            return

        # Stage and commit.
        # NOTE: git add -A stages everything in SCRIPT_DIR, including generated
        # runtime state (Sanctuary_Audit/, Sanctuary_Processed/, etc.).
        # Ensure .gitignore excludes these directories before relying on this.
        # Long-term: replace with explicit path staging once .gitignore is verified tight.
        subprocess.run(
            ["git", "add", "-A"],
            cwd=SCRIPT_DIR, timeout=30,
        )
        msg = f"[sanctuary-daemon] Auto-commit {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=SCRIPT_DIR, timeout=30,
        )

        state["last_git_commit"] = datetime.now().isoformat()
        audit.log("git_commit", "repo", "executed", details=msg)
        print(f"  ✓ Committed: {msg}")

    except Exception as e:
        audit.log("git_commit", "repo", "failed", details=str(e)[:300])
        print(f"  ✗ Git commit failed: {e}")


# ---------------------------------------------------------------------------
# Morning Dashboard
# ---------------------------------------------------------------------------

def generate_dashboard(
    config: dict, state: dict, audit: AuditLogger,
) -> str:
    """
    Generate the morning status dashboard.
    This is what the Architect reads with coffee at 6 AM.
    """
    print("\n  [DASHBOARD] Generating morning status...")
    now = datetime.now()
    lines = []

    lines.append("=" * 64)
    lines.append(f"  SANCTUARY MORNING DASHBOARD")
    lines.append(f"  {now.strftime('%A, %B %d, %Y — %I:%M %p')}")
    lines.append(f"  'Automate the broom. Guard the flame. You stay the lighthouse.'")
    lines.append("=" * 64)

    # --- Audit summary ---
    summary = audit.get_summary()
    lines.append(f"\n  Today's Activity:")
    lines.append(f"    Actions executed:  {summary.get('executed', 0)}")
    lines.append(f"    Actions denied:    {summary.get('denied', 0)}")
    lines.append(f"    Escalations:       {summary.get('escalated', 0)}")
    lines.append(f"    Failures:          {summary.get('failed', 0)}")

    # --- Thalamus queue ---
    queue_file = os.path.join(config.get("thalamus_dir", ""), "routing_queue.json")
    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            queue = json.load(f)
        pending = queue.get("pending", [])
        escalations = [p for p in pending if p.get("escalate")]
        auto = [p for p in pending if not p.get("escalate")]
        lines.append(f"\n  Thalamus Queue:")
        lines.append(f"    Pending total:     {len(pending)}")
        lines.append(f"    Auto-routable:     {len(auto)}")
        lines.append(f"    Need your review:  {len(escalations)}")
        if escalations:
            lines.append(f"\n  !! Items requiring Architect review:")
            for esc in escalations[:10]:
                src = os.path.basename(esc.get("source_file", "unknown"))
                sal = esc.get("salience", 0)
                lines.append(f"    [{sal:.3f}] {src}")
    except (FileNotFoundError, json.JSONDecodeError):
        lines.append(f"\n  Thalamus Queue: empty")

    # --- Escalation log ---
    esc_file = os.path.join(config.get("thalamus_dir", ""), "escalation_log.json")
    try:
        with open(esc_file, "r", encoding="utf-8") as f:
            esc_log = json.load(f)
        recent = esc_log.get("escalations", [])[-5:]
        if recent:
            lines.append(f"\n  Recent Escalations (last 5):")
            for esc in recent:
                src = os.path.basename(esc.get("source", "?"))
                ts = esc.get("timestamp", "?")[:16]
                lines.append(f"    {ts}  {src}")
                for flag in esc.get("charter_flags", []):
                    lines.append(f"      [CHARTER] {flag[:80]}")
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # --- Health status ---
    health_file = os.path.join(
        config.get("dashboard_dir", "Sanctuary_Dashboard"),
        "health_latest.json",
    )
    try:
        with open(health_file, "r", encoding="utf-8") as f:
            health = json.load(f)
        status = health.get("status", "unknown")
        warnings = health.get("warnings", [])
        lines.append(f"\n  System Health: {status.upper()}")
        if warnings:
            for w in warnings[:5]:
                lines.append(f"    ⚠ {w}")
    except (FileNotFoundError, json.JSONDecodeError):
        lines.append(f"\n  System Health: no health check data")

    # --- Processed files count ---
    proc_count = len(state.get("processed_files", {}))
    lines.append(f"\n  Files tracked:       {proc_count}")
    lines.append(f"  Last decay:          {state.get('last_decay', 'never')}")
    lines.append(f"  Last health check:   {state.get('last_health', 'never')}")
    lines.append(f"  Last git commit:     {state.get('last_git_commit', 'never')}")
    lines.append(f"  Last dashboard:      {now.isoformat()}")

    # --- Permission usage ---
    if PERMISSIONS_AVAILABLE:
        lines.append(f"\n  Permissions engine:   active")
    else:
        lines.append(f"\n  Permissions engine:   NOT LOADED (running permissive)")

    lines.append("\n" + "=" * 64)
    lines.append(f"  End of morning dashboard. The lighthouse is lit.")
    lines.append("=" * 64)

    dashboard_text = "\n".join(lines)

    # Save to file
    dash_dir = config.get("dashboard_dir", "Sanctuary_Dashboard")
    os.makedirs(dash_dir, exist_ok=True)
    dash_file = os.path.join(dash_dir, f"dashboard_{now.strftime('%Y-%m-%d')}.txt")
    with open(dash_file, "w", encoding="utf-8") as f:
        f.write(dashboard_text)

    state["last_dashboard"] = now.isoformat()
    print(f"  ✓ Dashboard written to {dash_file}")

    return dashboard_text


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

def _write_notification(config: dict, message: str, audit: AuditLogger) -> None:
    """Write a notification file for the Architect."""
    notify_dir = config.get("dashboard_dir", "Sanctuary_Dashboard")
    os.makedirs(notify_dir, exist_ok=True)
    notify_file = os.path.join(notify_dir, "NOTIFICATIONS.txt")

    with open(notify_file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {message}\n")

    audit.log("notify", "architect", "executed", details=message[:200])


# ---------------------------------------------------------------------------
# Main daemon loop
# ---------------------------------------------------------------------------

def daemon_loop(config: dict, once: bool = False) -> None:
    """
    Main System 1 loop.

    Runs continuously (or once with --once):
      1. Scan for new files → process pipeline
      2. Check scheduled tasks → run if due
      3. Sleep → repeat
    """
    state = load_state()
    audit = AuditLogger(config.get("audit_dir", "Sanctuary_Audit"))
    engine = PolicyEngine() if PERMISSIONS_AVAILABLE else None

    print("\n" + "=" * 60)
    print(f"  SANCTUARY DAEMON v{VERSION}")
    print(f"  System 1 — Autonomic Layer")
    print(f"  'Automate the broom. Guard the flame.'")
    print("=" * 60)
    print(f"  Watch folders:  {len(config.get('watch_folders', []))}")
    print(f"  Permissions:    {'active' if engine else 'PERMISSIVE (no engine)'}")
    print(f"  Mode:           {'single pass' if once else 'continuous'}")
    print("=" * 60)

    if not config.get("watch_folders"):
        print("\n  [WARN] No watch folders configured!")
        print(f"  Edit {CONFIG_FILE} to add your log folder paths.")
        print(f"  Example: \"watch_folders\": [\"C:\\\\Argus (Claude)\\\\Opus\"]")

    audit.log("daemon_start", "system", "executed",
               details=f"Mode={'once' if once else 'continuous'}")

    iteration = 0
    while True:
        iteration += 1
        now = datetime.now()

        # --- File watcher ---
        new_files = scan_for_new_files(config, state)
        if new_files:
            print(f"\n  [{now.strftime('%H:%M:%S')}] Found {len(new_files)} new/modified file(s)")
            for filepath in new_files:
                process_new_file(filepath, config, state, audit, engine)
            save_state(state)

        # --- Scheduled tasks ---
        decay_hour = config.get("nightly_decay_hour", 3)
        if should_run_scheduled(state, "last_decay", decay_hour):
            run_nightly_decay(config, state, audit, engine)
            save_state(state)

        health_hour = config.get("health_check_hour", 4)
        if should_run_scheduled(state, "last_health", health_hour):
            run_health_check(config, state, audit, engine)
            save_state(state)

        dash_hour = config.get("dashboard_hour", 5)
        if should_run_scheduled(state, "last_dashboard", dash_hour):
            dashboard = generate_dashboard(config, state, audit)
            print(dashboard)
            save_state(state)

        git_hour = config.get("git_autocommit_hour", 3)
        if should_run_scheduled(state, "last_git_commit", git_hour):
            run_git_autocommit(config, state, audit, engine)
            save_state(state)

        if once:
            print(f"\n  Single pass complete. {audit.get_summary()}")
            break

        # Sleep between polls
        interval = config.get("watch_interval_seconds", 30)
        time.sleep(interval)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sanctuary Daemon v1.0 — System 1 Autonomic Layer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sanctuary_daemon.py                   # Run continuously
  python sanctuary_daemon.py --once            # Single pass
  python sanctuary_daemon.py --dashboard       # Generate dashboard only
  python sanctuary_daemon.py --status          # Show daemon status
  python sanctuary_daemon.py --audit           # Show today's audit
  python sanctuary_daemon.py --init            # Create config file
        """,
    )
    parser.add_argument("--once",      action="store_true",
                        help="Run single pass then exit")
    parser.add_argument("--dashboard", action="store_true",
                        help="Generate morning dashboard only")
    parser.add_argument("--status",    action="store_true",
                        help="Show daemon and system status")
    parser.add_argument("--audit",     action="store_true",
                        help="Show today's audit log summary")
    parser.add_argument("--init",      action="store_true",
                        help="Create default config file")
    parser.add_argument("--health",    action="store_true",
                        help="Run health check only")

    args = parser.parse_args()
    config = load_config()

    if args.init:
        save_config(config)
        print(f"  Config written to {CONFIG_FILE}")
        print(f"  Edit 'watch_folders' to add your log directory paths.")
        return

    if args.dashboard:
        state = load_state()
        audit = AuditLogger(config.get("audit_dir", "Sanctuary_Audit"))
        dashboard = generate_dashboard(config, state, audit)
        print(dashboard)
        save_state(state)
        return

    if args.status:
        state = load_state()
        print("=" * 60)
        print(f"  SANCTUARY DAEMON v{VERSION} — Status")
        print("=" * 60)
        print(f"  Files tracked:       {len(state.get('processed_files', {}))}")
        print(f"  Last decay:          {state.get('last_decay', 'never')}")
        print(f"  Last health check:   {state.get('last_health', 'never')}")
        print(f"  Last dashboard:      {state.get('last_dashboard', 'never')}")
        print(f"  Last git commit:     {state.get('last_git_commit', 'never')}")
        print(f"  Watch folders:       {len(config.get('watch_folders', []))}")
        for f in config.get("watch_folders", []):
            exists = "✓" if os.path.isdir(f) else "✗"
            print(f"    {exists} {f}")
        return

    if args.audit:
        audit = AuditLogger(config.get("audit_dir", "Sanctuary_Audit"))
        summary = audit.get_summary()
        print("=" * 60)
        print(f"  SANCTUARY AUDIT — {datetime.now().strftime('%Y-%m-%d')}")
        print("=" * 60)
        print(f"  Total actions:   {summary['total']}")
        print(f"  Executed:        {summary['executed']}")
        print(f"  Denied:          {summary['denied']}")
        print(f"  Escalated:       {summary['escalated']}")
        print(f"  Failed:          {summary['failed']}")
        return

    if args.health:
        state = load_state()
        audit = AuditLogger(config.get("audit_dir", "Sanctuary_Audit"))
        engine = PolicyEngine() if PERMISSIONS_AVAILABLE else None
        health = run_health_check(config, state, audit, engine)
        save_state(state)
        return

    # Default: run daemon
    daemon_loop(config, once=args.once)


if __name__ == "__main__":
    main()
