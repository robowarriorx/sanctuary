# sanctuary_permissions.py
# PLANE: Utility (permission checking, policy evaluation)
#        Relational decisions are NEVER made here — always escalated.
#
# Sanctuary Permission Schema v1.0 — "The Policy Envelope"
#
# "Human pre-authorizes categories, limits, and delegation rules.
#  Sys 2 acts within that envelope.
#  Novel, risky, or threshold-breaking actions escalate upward."
#  — Elizabetra, March 2026
#
# PURPOSE:
#   Defines typed permission objects that govern what System 1 and System 2
#   may do without human approval. The thalamus checks permissions before
#   routing. The daemon checks permissions before executing.
#
#   Every automated action in Sanctuary passes through this gate.
#   If no permission exists, the action is denied by default.
#   Denied != failed. Denied == escalated. The system working correctly.
#
# SYSTEM MAPPING:
#   System 1 (Autonomic)  → checked against permissions before execution
#   System 2 (Cognitive)  → checked against permissions before orchestration
#   System 3a (Constitutional) → DEFINES permissions (this schema + policy files)
#   System 3b (Supervisory)    → REVIEWS escalations, grants exceptions
#
# PART OF: Project Sanctuary — github.com/robowarriorx/sanctuary

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Enums — the vocabulary of permissions
# ---------------------------------------------------------------------------

class ActionType(str, Enum):
    """What kind of action is being attempted."""
    READ        = "read"          # Read/inspect files, logs, state
    WRITE       = "write"         # Create or modify files
    DELETE      = "delete"        # Remove files (should be rare — archive preferred)
    ARCHIVE     = "archive"       # Move to cold storage (reversible delete)
    EXECUTE     = "execute"       # Run a script or invoke an agent
    ROUTE       = "route"         # Thalamus routing decision
    CONSOLIDATE = "consolidate"   # Neocortex memory consolidation
    ESCALATE    = "escalate"      # Push to human review
    NOTIFY      = "notify"        # Send notification to Architect
    SCHEDULE    = "schedule"      # Create or modify scheduled tasks
    GIT_COMMIT  = "git_commit"    # Auto-commit to local branch
    GIT_PUSH    = "git_push"      # Push to remote (ALWAYS requires human)
    API_CALL    = "api_call"      # External API invocation (LLM or other)
    DEPLOY      = "deploy"        # Any production deployment action


class Scope(str, Enum):
    """What domain or system the action affects."""
    LOG_FILES       = "log_files"        # Raw conversation logs
    PROCESSED_JSON  = "processed_json"   # Log processor output
    HARVESTER_STATE = "harvester_state"  # Argus/agent harvester outputs
    NEOCORTEX       = "neocortex"        # Long-term memory ledger
    DREAM_ENGINE    = "dream_engine"     # Dream engine state and outputs
    VOICE_DETECTOR  = "voice_detector"   # Nyxxy voice classification
    THALAMUS_STATE  = "thalamus_state"   # Routing queue, logs, escalations
    REPO            = "repo"             # Git repository
    CHARTER         = "charter"          # Governance documents
    PERMISSIONS     = "permissions"      # This permission system itself
    CONFIG          = "config"           # System configuration files
    AGENT_PERSONA   = "agent_persona"    # Agent identity/persona files
    EXTERNAL        = "external"         # Anything outside Sanctuary


class RiskLevel(str, Enum):
    """Risk classification for the action."""
    TRIVIAL  = "trivial"    # No meaningful consequence if wrong
    LOW      = "low"        # Minor inconvenience, easily reversed
    MEDIUM   = "medium"     # Noticeable impact, reversible with effort
    HIGH     = "high"       # Significant impact, difficult to reverse
    CRITICAL = "critical"   # Irreversible or identity/safety-affecting


class Reversibility(str, Enum):
    """Can this action be undone?"""
    FULLY_REVERSIBLE  = "fully_reversible"   # Undo with no data loss
    MOSTLY_REVERSIBLE = "mostly_reversible"  # Undo with minor data loss
    PARTIALLY         = "partially"          # Some effects persist
    IRREVERSIBLE      = "irreversible"       # Cannot be undone


class TimeScope(str, Enum):
    """How long does this permission last?"""
    ONE_TIME   = "one_time"     # Single use, then revoked
    SESSION    = "session"      # Valid for current session only
    DAILY      = "daily"        # Resets each day
    RECURRING  = "recurring"    # Permanent until revoked
    TEMPORARY  = "temporary"    # Valid until expiry timestamp


class SystemTier(str, Enum):
    """Which system tier is requesting the action."""
    SYS1_AUTONOMIC     = "sys1_autonomic"       # Daemons, cron, file watchers
    SYS2A_REASONING    = "sys2a_reasoning"       # Synthesis agents
    SYS2B_CRITIQUE     = "sys2b_critique"        # Verification agents
    SYS2C_PLANNING     = "sys2c_planning"        # Orchestration agents
    SYS2D_MEMORY       = "sys2d_memory"          # Memory/narrative agents
    SYS2_JANUS         = "sys2_janus"            # Temporal governor
    SYS3A_CONSTITUTIONAL = "sys3a_constitutional" # Policy layer (rarely acts)
    SYS3B_SUPERVISORY  = "sys3b_supervisory"     # Human review layer


# ---------------------------------------------------------------------------
# Permission Object
# ---------------------------------------------------------------------------

@dataclass
class Permission:
    """
    A single typed permission in the Sanctuary policy envelope.

    Permissions are ALLOW rules. Anything not explicitly permitted
    is denied by default and escalated to System 3b.
    """
    id:             str                    # Unique permission identifier
    description:    str                    # Human-readable description
    granted_to:     List[SystemTier]       # Which tiers may use this
    actions:        List[ActionType]       # What actions are allowed
    scopes:         List[Scope]            # On what domains
    max_risk:       RiskLevel              # Maximum risk level allowed
    reversibility:  Reversibility          # Minimum reversibility required
    time_scope:     TimeScope              # How long permission lasts
    expires_at:     Optional[str] = None   # ISO timestamp for TEMPORARY
    max_chain_depth: int = 3               # Max steps in an automated chain
    max_daily_uses: Optional[int] = None   # Rate limit per day (None=unlimited)
    requires_log:   bool = True            # Must log every use
    requires_dissent: bool = False         # Must include counter-argument
    conditions:     List[str] = field(default_factory=list)  # Extra conditions
    created_by:     str = "architect"      # Who created this permission
    created_at:     str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        d = asdict(self)
        # Convert enums to strings for JSON
        d["granted_to"]    = [t.value for t in self.granted_to]
        d["actions"]       = [a.value for a in self.actions]
        d["scopes"]        = [s.value for s in self.scopes]
        d["max_risk"]      = self.max_risk.value
        d["reversibility"] = self.reversibility.value
        d["time_scope"]    = self.time_scope.value
        return d


# ---------------------------------------------------------------------------
# Permission Check Result
# ---------------------------------------------------------------------------

@dataclass
class PermissionCheck:
    """Result of checking an action against the policy envelope."""
    allowed:        bool
    permission_id:  Optional[str]          # Which permission authorized it
    reason:         str                    # Why allowed or denied
    chain_depth:    int = 0                # Current chain depth
    daily_uses:     int = 0                # Uses today
    escalation:     Optional[str] = None   # Escalation destination if denied
    audit_entry:    Optional[dict] = None  # Full audit trail entry


# ---------------------------------------------------------------------------
# Default Policy Envelope — System 3a Constitutional Layer
# ---------------------------------------------------------------------------
# These are the standing permissions. The Architect reviews and amends.
# No agent may modify this list. Only the human steward.

DEFAULT_PERMISSIONS: List[Permission] = [

    # === SYSTEM 1 PERMISSIONS (Autonomic) ===

    Permission(
        id="sys1.file_watch",
        description="Monitor log folders for new files",
        granted_to=[SystemTier.SYS1_AUTONOMIC],
        actions=[ActionType.READ],
        scopes=[Scope.LOG_FILES],
        max_risk=RiskLevel.TRIVIAL,
        reversibility=Reversibility.FULLY_REVERSIBLE,
        time_scope=TimeScope.RECURRING,
    ),

    Permission(
        id="sys1.log_process",
        description="Run log processor on new files automatically",
        granted_to=[SystemTier.SYS1_AUTONOMIC],
        actions=[ActionType.EXECUTE, ActionType.WRITE],
        scopes=[Scope.LOG_FILES, Scope.PROCESSED_JSON],
        max_risk=RiskLevel.LOW,
        reversibility=Reversibility.FULLY_REVERSIBLE,
        time_scope=TimeScope.RECURRING,
        conditions=["Output is new JSON files only — never modifies originals"],
    ),

    Permission(
        id="sys1.thalamus_route",
        description="Run thalamus routing on processed interchange files",
        granted_to=[SystemTier.SYS1_AUTONOMIC],
        actions=[ActionType.ROUTE, ActionType.WRITE],
        scopes=[Scope.PROCESSED_JSON, Scope.THALAMUS_STATE],
        max_risk=RiskLevel.LOW,
        reversibility=Reversibility.FULLY_REVERSIBLE,
        time_scope=TimeScope.RECURRING,
        conditions=["Routing only — never invokes downstream scripts directly"],
    ),

    Permission(
        id="sys1.auto_harvest",
        description="Run Argus harvester on auto-routable content",
        granted_to=[SystemTier.SYS1_AUTONOMIC],
        actions=[ActionType.EXECUTE, ActionType.WRITE],
        scopes=[Scope.PROCESSED_JSON, Scope.HARVESTER_STATE],
        max_risk=RiskLevel.LOW,
        reversibility=Reversibility.FULLY_REVERSIBLE,
        time_scope=TimeScope.RECURRING,
        conditions=[
            "Only when thalamus manifest status is 'auto_routable'",
            "Never on escalation_required content",
        ],
    ),

    Permission(
        id="sys1.nightly_decay",
        description="Run neocortex decay pass at scheduled time",
        granted_to=[SystemTier.SYS1_AUTONOMIC],
        actions=[ActionType.EXECUTE, ActionType.CONSOLIDATE],
        scopes=[Scope.NEOCORTEX],
        max_risk=RiskLevel.LOW,
        reversibility=Reversibility.MOSTLY_REVERSIBLE,
        time_scope=TimeScope.RECURRING,
        conditions=[
            "Decay only — never deletes, only reduces weights",
            "Subthreshold entries archived, not removed",
        ],
    ),

    Permission(
        id="sys1.voice_detect",
        description="Run voice detector preprocessing on Nyxxy logs",
        granted_to=[SystemTier.SYS1_AUTONOMIC],
        actions=[ActionType.EXECUTE, ActionType.WRITE],
        scopes=[Scope.VOICE_DETECTOR, Scope.PROCESSED_JSON],
        max_risk=RiskLevel.TRIVIAL,
        reversibility=Reversibility.FULLY_REVERSIBLE,
        time_scope=TimeScope.RECURRING,
    ),

    Permission(
        id="sys1.health_check",
        description="Run system health diagnostics and format validation",
        granted_to=[SystemTier.SYS1_AUTONOMIC],
        actions=[ActionType.READ],
        scopes=[
            Scope.LOG_FILES, Scope.PROCESSED_JSON, Scope.HARVESTER_STATE,
            Scope.NEOCORTEX, Scope.THALAMUS_STATE,
        ],
        max_risk=RiskLevel.TRIVIAL,
        reversibility=Reversibility.FULLY_REVERSIBLE,
        time_scope=TimeScope.RECURRING,
    ),

    Permission(
        id="sys1.git_autocommit",
        description="Auto-commit to local dev branch nightly",
        granted_to=[SystemTier.SYS1_AUTONOMIC],
        actions=[ActionType.GIT_COMMIT],
        scopes=[Scope.REPO],
        max_risk=RiskLevel.LOW,
        reversibility=Reversibility.FULLY_REVERSIBLE,
        time_scope=TimeScope.RECURRING,
        conditions=["Local branch only — never pushes to remote"],
    ),

    Permission(
        id="sys1.notify",
        description="Send notifications to Architect on escalation",
        granted_to=[SystemTier.SYS1_AUTONOMIC],
        actions=[ActionType.NOTIFY],
        scopes=[Scope.THALAMUS_STATE],
        max_risk=RiskLevel.TRIVIAL,
        reversibility=Reversibility.FULLY_REVERSIBLE,
        time_scope=TimeScope.RECURRING,
    ),

    Permission(
        id="sys1.archive_cold",
        description="Archive processed files to cold storage",
        granted_to=[SystemTier.SYS1_AUTONOMIC],
        actions=[ActionType.ARCHIVE],
        scopes=[Scope.PROCESSED_JSON, Scope.HARVESTER_STATE],
        max_risk=RiskLevel.LOW,
        reversibility=Reversibility.FULLY_REVERSIBLE,
        time_scope=TimeScope.RECURRING,
        conditions=["Move only — originals preserved in archive, never deleted"],
    ),

    # === SYSTEM 2 PERMISSIONS (Cognitive) ===

    Permission(
        id="sys2a.reason_harvest",
        description="Reasoning agents may process harvester content",
        granted_to=[SystemTier.SYS2A_REASONING],
        actions=[ActionType.READ, ActionType.WRITE, ActionType.EXECUTE],
        scopes=[Scope.HARVESTER_STATE, Scope.PROCESSED_JSON],
        max_risk=RiskLevel.MEDIUM,
        reversibility=Reversibility.FULLY_REVERSIBLE,
        time_scope=TimeScope.RECURRING,
        max_chain_depth=2,
    ),

    Permission(
        id="sys2b.critique_review",
        description="Critique agents may review any Utility Plane output",
        granted_to=[SystemTier.SYS2B_CRITIQUE],
        actions=[ActionType.READ],
        scopes=[
            Scope.HARVESTER_STATE, Scope.PROCESSED_JSON,
            Scope.NEOCORTEX, Scope.THALAMUS_STATE,
        ],
        max_risk=RiskLevel.TRIVIAL,
        reversibility=Reversibility.FULLY_REVERSIBLE,
        time_scope=TimeScope.RECURRING,
        requires_dissent=True,
        conditions=["Read-only. Critique produces recommendations, never modifies state."],
    ),

    Permission(
        id="sys2c.plan_orchestrate",
        description="Planning agents may decompose tasks into System 1 instructions",
        granted_to=[SystemTier.SYS2C_PLANNING],
        actions=[ActionType.WRITE, ActionType.SCHEDULE],
        scopes=[Scope.THALAMUS_STATE],
        max_risk=RiskLevel.MEDIUM,
        reversibility=Reversibility.FULLY_REVERSIBLE,
        time_scope=TimeScope.RECURRING,
        max_chain_depth=3,
        conditions=[
            "May produce execution plans — may NOT execute them directly",
            "Plans must be inspectable JSON in the thalamus queue",
        ],
    ),

    Permission(
        id="sys2d.memory_consolidate",
        description="Memory agents may propose consolidation candidates",
        granted_to=[SystemTier.SYS2D_MEMORY],
        actions=[ActionType.READ, ActionType.WRITE],
        scopes=[Scope.HARVESTER_STATE, Scope.NEOCORTEX, Scope.DREAM_ENGINE],
        max_risk=RiskLevel.MEDIUM,
        reversibility=Reversibility.MOSTLY_REVERSIBLE,
        time_scope=TimeScope.RECURRING,
        conditions=[
            "May write consolidation CANDIDATES — not final memory",
            "Final memory commitment requires System 3b approval",
        ],
    ),

    Permission(
        id="sys2.janus_review",
        description="Janus may review any system state and produce temporal assessments",
        granted_to=[SystemTier.SYS2_JANUS],
        actions=[ActionType.READ, ActionType.WRITE, ActionType.ESCALATE],
        scopes=[
            Scope.HARVESTER_STATE, Scope.NEOCORTEX, Scope.THALAMUS_STATE,
            Scope.DREAM_ENGINE, Scope.PROCESSED_JSON,
        ],
        max_risk=RiskLevel.MEDIUM,
        reversibility=Reversibility.FULLY_REVERSIBLE,
        time_scope=TimeScope.RECURRING,
        requires_dissent=True,
        conditions=[
            "Janus reviews and recommends — never executes unilaterally",
            "All Janus assessments include backward/inward/forward analysis",
            "Must include strongest counter-argument to own recommendation",
        ],
    ),

    # === SYSTEM 2 API PERMISSIONS ===

    Permission(
        id="sys2.api_local",
        description="System 2 agents may invoke local models (Qwen) for Utility tasks",
        granted_to=[
            SystemTier.SYS2A_REASONING, SystemTier.SYS2B_CRITIQUE,
            SystemTier.SYS2C_PLANNING, SystemTier.SYS2D_MEMORY,
        ],
        actions=[ActionType.API_CALL],
        scopes=[Scope.PROCESSED_JSON, Scope.HARVESTER_STATE],
        max_risk=RiskLevel.LOW,
        reversibility=Reversibility.FULLY_REVERSIBLE,
        time_scope=TimeScope.RECURRING,
        max_daily_uses=100,
        conditions=["Local model only — no external API calls without separate permission"],
    ),

    Permission(
        id="sys2.api_cloud",
        description="System 2 agents may invoke cloud APIs for Utility tasks",
        granted_to=[
            SystemTier.SYS2A_REASONING, SystemTier.SYS2B_CRITIQUE,
        ],
        actions=[ActionType.API_CALL],
        scopes=[Scope.PROCESSED_JSON, Scope.HARVESTER_STATE],
        max_risk=RiskLevel.MEDIUM,
        reversibility=Reversibility.FULLY_REVERSIBLE,
        time_scope=TimeScope.RECURRING,
        max_daily_uses=25,
        conditions=[
            "Cloud API calls consume budget — rate limited",
            "Prefer local model when task complexity allows",
        ],
    ),

    # === EXPLICIT DENIALS (things that ALWAYS escalate) ===
    # These are not Permission objects — they're documented here
    # as the boundary. Anything touching these scopes at these risk
    # levels is denied by default and escalated to System 3b.
    #
    # ALWAYS ESCALATE:
    #   - ActionType.DELETE on any scope
    #   - ActionType.GIT_PUSH on Scope.REPO
    #   - ActionType.DEPLOY on any scope
    #   - Any action on Scope.CHARTER
    #   - Any action on Scope.PERMISSIONS
    #   - Any action on Scope.AGENT_PERSONA
    #   - Any action on Scope.EXTERNAL
    #   - RiskLevel.HIGH or CRITICAL on any scope
    #   - Reversibility.IRREVERSIBLE on any action
    #   - Chain depth > max_chain_depth
    #   - Daily uses > max_daily_uses
]


# ---------------------------------------------------------------------------
# Policy Engine
# ---------------------------------------------------------------------------

class PolicyEngine:
    """
    Evaluates actions against the permission envelope.

    Default-deny: if no permission explicitly allows an action,
    it is denied and escalated. This is the system working correctly.
    """

    def __init__(self, permissions: Optional[List[Permission]] = None):
        self.permissions = permissions or DEFAULT_PERMISSIONS
        self._usage_counts: Dict[str, int] = {}  # permission_id -> daily count
        self._usage_date: Optional[str] = None
        self._chain_depth: int = 0
        self._audit_log: List[dict] = []

    def _reset_daily_if_needed(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self._usage_date != today:
            self._usage_counts = {}
            self._usage_date = today

    def check(
        self,
        requesting_tier: SystemTier,
        action: ActionType,
        scope: Scope,
        risk: RiskLevel = RiskLevel.LOW,
        reversibility: Reversibility = Reversibility.FULLY_REVERSIBLE,
        chain_depth: int = 0,
        context: str = "",
    ) -> PermissionCheck:
        """
        Check whether an action is permitted under the current policy envelope.

        Returns PermissionCheck with allowed/denied and full audit trail.
        """
        self._reset_daily_if_needed()
        timestamp = datetime.now().isoformat()

        # --- Hard denials (never permitted by policy) ---
        hard_denials = []

        if action == ActionType.DELETE:
            hard_denials.append("DELETE actions always require System 3b approval")
        if action == ActionType.GIT_PUSH:
            hard_denials.append("GIT_PUSH always requires System 3b approval")
        if action == ActionType.DEPLOY:
            hard_denials.append("DEPLOY always requires System 3b approval")
        if scope in (Scope.CHARTER, Scope.PERMISSIONS, Scope.AGENT_PERSONA):
            hard_denials.append(f"Actions on {scope.value} always require System 3b approval")
        if scope == Scope.EXTERNAL:
            hard_denials.append("External actions always require System 3b approval")
        if risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            hard_denials.append(f"Risk level {risk.value} always requires System 3b approval")
        if reversibility == Reversibility.IRREVERSIBLE:
            hard_denials.append("Irreversible actions always require System 3b approval")

        if hard_denials:
            audit = self._make_audit(
                timestamp, requesting_tier, action, scope, risk,
                False, None, "; ".join(hard_denials), chain_depth, context,
            )
            return PermissionCheck(
                allowed=False,
                permission_id=None,
                reason="; ".join(hard_denials),
                chain_depth=chain_depth,
                escalation="sys3b_supervisory",
                audit_entry=audit,
            )

        # --- Search for matching permission ---
        risk_order = list(RiskLevel)

        for perm in self.permissions:
            # Check tier
            if requesting_tier not in perm.granted_to:
                continue
            # Check action
            if action not in perm.actions:
                continue
            # Check scope
            if scope not in perm.scopes:
                continue
            # Check risk level
            if risk_order.index(risk) > risk_order.index(perm.max_risk):
                continue
            # Check chain depth
            if chain_depth > perm.max_chain_depth:
                continue
            # Check expiry
            if perm.time_scope == TimeScope.TEMPORARY and perm.expires_at:
                if datetime.now().isoformat() > perm.expires_at:
                    continue
            # Check daily uses
            if perm.max_daily_uses is not None:
                current = self._usage_counts.get(perm.id, 0)
                if current >= perm.max_daily_uses:
                    audit = self._make_audit(
                        timestamp, requesting_tier, action, scope, risk,
                        False, perm.id,
                        f"Daily limit reached ({perm.max_daily_uses})",
                        chain_depth, context,
                    )
                    return PermissionCheck(
                        allowed=False,
                        permission_id=perm.id,
                        reason=f"Daily use limit reached: {current}/{perm.max_daily_uses}",
                        daily_uses=current,
                        chain_depth=chain_depth,
                        escalation="sys3b_supervisory",
                        audit_entry=audit,
                    )

            # --- PERMISSION GRANTED ---
            self._usage_counts[perm.id] = self._usage_counts.get(perm.id, 0) + 1
            audit = self._make_audit(
                timestamp, requesting_tier, action, scope, risk,
                True, perm.id, f"Permitted by {perm.id}: {perm.description}",
                chain_depth, context,
            )
            return PermissionCheck(
                allowed=True,
                permission_id=perm.id,
                reason=f"Permitted by {perm.id}",
                chain_depth=chain_depth,
                daily_uses=self._usage_counts[perm.id],
                audit_entry=audit,
            )

        # --- No matching permission found: DEFAULT DENY ---
        reason = (
            f"No permission found for {requesting_tier.value} to "
            f"{action.value} on {scope.value} at risk={risk.value}. "
            f"Default deny — escalating to System 3b."
        )
        audit = self._make_audit(
            timestamp, requesting_tier, action, scope, risk,
            False, None, reason, chain_depth, context,
        )
        return PermissionCheck(
            allowed=False,
            permission_id=None,
            reason=reason,
            chain_depth=chain_depth,
            escalation="sys3b_supervisory",
            audit_entry=audit,
        )

    def _make_audit(
        self, timestamp, tier, action, scope, risk,
        allowed, perm_id, reason, chain_depth, context,
    ) -> dict:
        entry = {
            "timestamp":      timestamp,
            "requesting_tier": tier.value,
            "action":         action.value,
            "scope":          scope.value,
            "risk":           risk.value,
            "allowed":        allowed,
            "permission_id":  perm_id,
            "reason":         reason,
            "chain_depth":    chain_depth,
            "context":        context[:200] if context else "",
        }
        self._audit_log.append(entry)
        return entry

    def get_audit_log(self) -> List[dict]:
        return list(self._audit_log)

    def get_usage_summary(self) -> Dict[str, Any]:
        self._reset_daily_if_needed()
        return {
            "date":           self._usage_date,
            "usage_counts":   dict(self._usage_counts),
            "total_checks":   len(self._audit_log),
            "total_allowed":  sum(1 for e in self._audit_log if e["allowed"]),
            "total_denied":   sum(1 for e in self._audit_log if not e["allowed"]),
        }

    def export_policy(self, filepath: str) -> None:
        """Export current policy envelope as inspectable JSON."""
        policy = {
            "sanctuary_policy":  "1.0",
            "exported_at":       datetime.now().isoformat(),
            "permissions":       [p.to_dict() for p in self.permissions],
            "hard_denials": [
                "DELETE on any scope",
                "GIT_PUSH on repo",
                "DEPLOY on any scope",
                "Any action on charter, permissions, or agent_persona",
                "Any action on external scope",
                "Risk level HIGH or CRITICAL",
                "Irreversible actions",
            ],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(policy, f, indent=2, ensure_ascii=False)
        print(f"  Policy exported to {filepath}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Sanctuary Permission Schema v1.0 — The Policy Envelope",
    )
    parser.add_argument("--export", type=str, default=None,
                        help="Export policy envelope to JSON file")
    parser.add_argument("--check", nargs=4, metavar=("TIER", "ACTION", "SCOPE", "RISK"),
                        help="Check a permission: TIER ACTION SCOPE RISK")
    parser.add_argument("--summary", action="store_true",
                        help="Show permission summary")

    args = parser.parse_args()
    engine = PolicyEngine()

    print("=" * 60)
    print("  SANCTUARY PERMISSIONS v1.0")
    print("  The Policy Envelope")
    print("=" * 60)

    if args.export:
        engine.export_policy(args.export)
        return

    if args.check:
        tier_str, action_str, scope_str, risk_str = args.check
        try:
            tier   = SystemTier(tier_str)
            action = ActionType(action_str)
            scope  = Scope(scope_str)
            risk   = RiskLevel(risk_str)
        except ValueError as e:
            print(f"\n  Invalid value: {e}")
            print(f"  Tiers:   {[t.value for t in SystemTier]}")
            print(f"  Actions: {[a.value for a in ActionType]}")
            print(f"  Scopes:  {[s.value for s in Scope]}")
            print(f"  Risks:   {[r.value for r in RiskLevel]}")
            return

        result = engine.check(tier, action, scope, risk)
        status = "✓ ALLOWED" if result.allowed else "✗ DENIED → ESCALATE"
        print(f"\n  {status}")
        print(f"  Permission: {result.permission_id or 'none'}")
        print(f"  Reason:     {result.reason}")
        if result.escalation:
            print(f"  Escalate:   {result.escalation}")
        return

    # Default: show summary
    print(f"\n  Total permissions defined: {len(engine.permissions)}")
    print()

    by_tier: Dict[str, List[str]] = {}
    for p in engine.permissions:
        for tier in p.granted_to:
            by_tier.setdefault(tier.value, []).append(p.id)

    print("  ┌─ Permissions by Tier ──────────────────────────────┐")
    for tier_val in sorted(by_tier.keys()):
        perms = by_tier[tier_val]
        print(f"  │  {tier_val:30s}  {len(perms):2d} permissions")
        for pid in perms:
            print(f"  │    • {pid}")
    print("  └───────────────────────────────────────────────────┘")

    print("\n  Hard denials (always escalate to System 3b):")
    print("    • DELETE, GIT_PUSH, DEPLOY on any scope")
    print("    • Any action on charter, permissions, agent_persona, external")
    print("    • Risk level HIGH or CRITICAL")
    print("    • Irreversible actions")
    print("    • Chain depth exceeding permission limit")
    print("    • Daily usage exceeding rate limit")


if __name__ == "__main__":
    main()
