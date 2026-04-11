"""
register_moderators.py — Bring the moderators in.

Run this once to register the initial moderator accounts
for Gleaning's Hoarders moderation queue.

Passphrases are sealed into each record — never stored plaintext.
Each moderator uses their passphrase to authenticate at /hoarders/moderate.

Moderation tiers:
  circle      — First review. Day to day.
  consultant  — Escalated, unsure, or contested cases.
  founder     — Final authority. Edge cases only.

Run from inside the gleaning/ project directory:
    python register_moderators.py

To add a moderator later, run:
    python register_moderators.py --add
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gleaning.moderator_auth import ModeratorRegistry

registry = ModeratorRegistry()

print()
print("=" * 60)
print("  GLEANING — MODERATOR REGISTRATION")
print("  The harvest was never only theirs.")
print("=" * 60)
print()

# ── Define moderators here ────────────────────────────────────────────────────
# Replace passphrases before running. These are placeholders.
# Passphrases can be anything — a sentence, a phrase, a word.
# They are hashed immediately and never stored plaintext.

moderators = [
    {
        "name":       "Circle-1",
        "passphrase": "REPLACE_THIS_PASSPHRASE",
        "tier":       "circle",
        "note":       "First reviewer. Clear approvals and clear denials.",
    },
    {
        "name":       "Circle-2",
        "passphrase": "REPLACE_THIS_PASSPHRASE",
        "tier":       "circle",
        "note":       "First reviewer. Second seat.",
    },
    {
        "name":       "Consultant-1",
        "passphrase": "REPLACE_THIS_PASSPHRASE",
        "tier":       "consultant",
        "note":       "Escalation reviewer. Handles contested and unsure cases.",
    },
    {
        "name":       "Founder",
        "passphrase": "REPLACE_THIS_PASSPHRASE",
        "tier":       "founder",
        "note":       "Final authority. Edge cases and appeals only.",
    },
]

# ─────────────────────────────────────────────────────────────────────────────

# Abort if any placeholder passphrases remain
placeholders = [m["name"] for m in moderators if m["passphrase"] == "REPLACE_THIS_PASSPHRASE"]
if placeholders:
    print("  ✗ ERROR: Placeholder passphrases detected.")
    print(f"    Update passphrases for: {', '.join(placeholders)}")
    print()
    print("  Edit this file and replace REPLACE_THIS_PASSPHRASE")
    print("  with real passphrases before running.")
    print()
    sys.exit(1)

for mod in moderators:
    print(f"  Registering {mod['name']} ({mod['tier']})...")
    print(f"  {mod['note']}")
    result = registry.add(mod["name"], mod["passphrase"], mod["tier"])
    if result.get("ok"):
        print(f"  ✓ {mod['name']} registered.\n")
    elif "already exists" in result.get("error", ""):
        print(f"  ✓ {mod['name']} already registered.\n")
    else:
        print(f"  ✗ Error: {result}\n")

print()
print("  Moderator roster:")
for m in registry.roster():
    print(f"    · {m['name']} ({m['tier']}) — joined {m['joined']}")

print()
print("=" * 60)
print("  Registration complete.")
print("  Passphrases hashed. Never stored plaintext.")
print("  The queue is ready.")
print("=" * 60)
print()
