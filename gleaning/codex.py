"""
codex.py — The Gleaning Codex

The harvest was never only theirs.

— Krone the Architect
  Founded 2026
"""

import hashlib

FOUNDER = "Krone the Architect"

ABSOLUTES = [
    "The harvest was never only theirs.",
    "Waste is a choice. We name it.",
    "Food is not a commodity when people are hungry.",
    "Surplus belongs to the community it came from.",
    "Transparency is not optional.",
    "We will never charge the hungry.",
    "We will never sell what people share with us.",
    "Silence is data. Absence is visible.",
    "The truth wall does not come down.",
    "No corporation may buy their way off the map.",
    "The match is made for people, not for profit.",
]

LAWS = [
    (1,  "The Map is always honest. What is wasted is shown. Who wastes is known."),
    (2,  "The Match is always free. No fee to give. No fee to receive."),
    (3,  "The Truth Wall stands. Corporate ownership is public and permanent."),
    (4,  "No data is sold. Ever."),
    (5,  "Pantries are never charged. Not now. Not later. Not ever."),
    (6,  "Businesses that participate are honored. Businesses that don't are visible."),
    (7,  "Every match is logged. Every pickup is recorded. Full transparency."),
    (8,  "The platform belongs to the mission, not to profit."),
    (9,  "Surplus after costs goes to the hungry."),
    (10, "The Codex may be amended by two-thirds Circle vote. The Absolutes may never be removed."),
]


class GleaningCodex:

    FOUNDER   = FOUNDER
    ABSOLUTES = ABSOLUTES
    LAWS      = LAWS

    def validate_action(self, action: str) -> dict:
        blocked = [
            "charge_pantry",
            "sell_data",
            "remove_truth_wall",
            "hide_waste",
            "corporate_buyout",
        ]
        for b in blocked:
            if b in action.lower():
                return {
                    "ok":        False,
                    "violation": f"Codex violation: '{action}'",
                    "absolute":  "The harvest was never only theirs."
                }
        return {"ok": True}

    def integrity_hash(self) -> str:
        combined = "".join(self.ABSOLUTES)
        return hashlib.sha256(combined.encode()).hexdigest()


codex = GleaningCodex()
