"""
pool.py — Gleaning Consultant Pool

Adapted from Medusa consultant pool pattern.
Loads all consultant profiles from JSON files.
Available to all three teams on demand.
"""

import json
import os
from typing import Optional


PROFILES_DIR = os.path.join(os.path.dirname(__file__), "profiles")


class Consultant:
    def __init__(self, profile: dict):
        self.id           = profile.get("id", "unknown")
        self.name         = profile.get("name", "Unnamed Consultant")
        self.domain       = profile.get("domain", "general")
        self.focus        = profile.get("focus", "")
        self.profile      = profile
        self._queries     = 0

    def advise(self, context: dict = None) -> dict:
        self._queries += 1
        return {
            "consultant": self.name,
            "domain":     self.domain,
            "focus":      self.focus,
            "profile":    self.profile,
        }

    def diagnose(self, issue: str = "") -> list:
        self._queries += 1
        return (
            self.profile.get("failure_modes", []) +
            self.profile.get("checks", []) +
            self.profile.get("diagnosis", []) +
            ([self.profile["notes"]] if self.profile.get("notes") else [])
        )

    def __repr__(self):
        return f"Consultant({self.id}: {self.name})"


class ConsultantPool:
    def __init__(self):
        self._consultants = {}
        self._load_all()
        print(f"  [◈ GLEANING POOL] {len(self._consultants)} consultants loaded.")

    def _load_all(self):
        if not os.path.exists(PROFILES_DIR):
            print(f"  [◈ GLEANING POOL] Profiles directory not found: {PROFILES_DIR}")
            return
        for filename in sorted(os.listdir(PROFILES_DIR)):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(PROFILES_DIR, filename)
            try:
                with open(path) as f:
                    profiles = json.load(f)
                if isinstance(profiles, list):
                    for p in profiles:
                        c = Consultant(p)
                        self._consultants[c.id] = c
                elif isinstance(profiles, dict):
                    c = Consultant(profiles)
                    self._consultants[c.id] = c
            except Exception as e:
                print(f"  [◈ GLEANING POOL] Failed to load {filename}: {e}")

    def get(self, consultant_id: str) -> Optional[Consultant]:
        return self._consultants.get(consultant_id)

    def by_domain(self, domain: str) -> list:
        return [c for c in self._consultants.values() if c.domain == domain]

    def by_focus(self, focus: str) -> list:
        focus = focus.lower()
        return [c for c in self._consultants.values()
                if focus in (c.focus or "").lower() or focus in c.name.lower()]

    def diagnose(self, domain: str, focus: str = "") -> list:
        results = []
        for c in self.by_domain(domain):
            if not focus or focus.lower() in (c.focus or "").lower():
                results.extend(c.diagnose())
        return results

    def coverage_report(self) -> dict:
        from collections import Counter
        domains = Counter(c.domain for c in self._consultants.values())
        return {"total": len(self._consultants), "domains": dict(domains)}

    def all_ids(self) -> list:
        return sorted(self._consultants.keys())

    def __len__(self):
        return len(self._consultants)

    def __repr__(self):
        return f"ConsultantPool({len(self._consultants)} consultants)"
