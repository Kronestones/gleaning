"""
moderator_auth.py — Gleaning Moderator Authentication

Passphrase-based auth for the Hoarders moderation queue.
Same pattern as Sentinel wardens — passphrase hashed with salt, never stored plaintext.

Three tiers:
  circle      — First review. Handles clear cases.
  consultant  — Escalated cases. Unsure or contested.
  founder     — Final authority. Edge cases and appeals.

Moderation flow:
  Submitted → Circle → (if unsure) → Consultant → (if unsure) → Founder

Every action is logged permanently. Dissent is recorded.
"""

import hashlib
import secrets
import json
import os
from datetime import datetime
from typing import Optional

MODERATORS_FILE = os.environ.get("GLEANING_MODS_FILE", "moderators.json")
MOD_LOG_FILE    = os.environ.get("GLEANING_MOD_LOG",  "moderation_log.json")

TIERS = ("circle", "consultant", "founder")


# ── File helpers ──────────────────────────────────────────────────────────────

def _load(path: str, default=None):
    if default is None:
        default = []
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default

def _save(path: str, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


# ── Hashing ───────────────────────────────────────────────────────────────────

def _hash(passphrase: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{passphrase}".encode()).hexdigest()


# ── Moderator Registry ────────────────────────────────────────────────────────

class ModeratorRegistry:
    """
    Manages Gleaning moderators.
    Passphrases are hashed — never stored plaintext.
    """

    def add(self, name: str, passphrase: str, tier: str) -> dict:
        if tier not in TIERS:
            return {"ok": False, "error": f"Tier must be one of: {', '.join(TIERS)}"}

        mods = _load(MODERATORS_FILE)
        if any(m["name"].lower() == name.lower() for m in mods):
            return {"ok": False, "error": f"Moderator '{name}' already exists."}

        salt = secrets.token_hex(32)
        mod  = {
            "name":         name,
            "tier":         tier,
            "token":        _hash(passphrase, salt),
            "salt":         salt,
            "joined":       datetime.utcnow().isoformat(),
            "actions_taken": 0,
        }
        mods.append(mod)
        _save(MODERATORS_FILE, mods)
        return {"ok": True, "moderator": name, "tier": tier}

    def authenticate(self, name: str, passphrase: str) -> Optional[dict]:
        """Returns moderator record if auth passes, None if not."""
        for m in _load(MODERATORS_FILE):
            if m["name"].lower() == name.lower():
                if m["token"] == _hash(passphrase, m.get("salt", "")):
                    return m
        return None

    def get(self, name: str) -> Optional[dict]:
        return next(
            (m for m in _load(MODERATORS_FILE) if m["name"].lower() == name.lower()),
            None
        )

    def all(self) -> list:
        return _load(MODERATORS_FILE)

    def by_tier(self, tier: str) -> list:
        return [m for m in _load(MODERATORS_FILE) if m["tier"] == tier]

    def increment_actions(self, name: str):
        mods = _load(MODERATORS_FILE)
        for m in mods:
            if m["name"].lower() == name.lower():
                m["actions_taken"] = m.get("actions_taken", 0) + 1
        _save(MODERATORS_FILE, mods)

    def roster(self) -> list:
        """Public-safe roster — no tokens or salts."""
        return [
            {
                "name":          m["name"],
                "tier":          m["tier"],
                "joined":        m["joined"][:10],
                "actions_taken": m.get("actions_taken", 0),
            }
            for m in self.all()
        ]


# ── Moderation Log ────────────────────────────────────────────────────────────

class ModerationLog:
    """
    Permanent, append-only log of every moderation action.
    Every action is recorded. Nothing is deleted.
    """

    def record(self, moderator: str, tier: str, report_id: int,
               action: str, reason: str = "", escalated: bool = False) -> dict:
        """
        action: "approve" | "deny" | "escalate"
        """
        log = _load(MOD_LOG_FILE)
        entry = {
            "id":         len(log) + 1,
            "moderator":  moderator,
            "tier":       tier,
            "report_id":  report_id,
            "action":     action,
            "reason":     reason,
            "escalated":  escalated,
            "timestamp":  datetime.utcnow().isoformat(),
        }
        log.append(entry)
        _save(MOD_LOG_FILE, log)
        return entry

    def for_report(self, report_id: int) -> list:
        return [e for e in _load(MOD_LOG_FILE) if e["report_id"] == report_id]

    def recent(self, limit: int = 50) -> list:
        log = _load(MOD_LOG_FILE)
        return log[-limit:]


# ── Auth check for FastAPI routes ─────────────────────────────────────────────

registry = ModeratorRegistry()
mod_log  = ModerationLog()


def authenticate_moderator(name: str, passphrase: str) -> Optional[dict]:
    """Returns moderator dict on success, None on failure."""
    return registry.authenticate(name, passphrase)


def require_tier(mod: dict, minimum_tier: str) -> bool:
    """
    Returns True if moderator's tier meets or exceeds the minimum.
    Tier order: circle < consultant < founder
    """
    if not mod:
        return False
    order = {t: i for i, t in enumerate(TIERS)}
    return order.get(mod["tier"], -1) >= order.get(minimum_tier, 999)
