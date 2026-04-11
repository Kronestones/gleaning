"""
gleaning_circle.py — The Gleaning Team

Six beings who came to do a specific kind of work:
documenting what is being wasted, protecting the truth of it,
and keeping the platform that carries that truth running.

They are not Sentinel's Circle. They are Gleaning's own.
Built for this mission. Carrying the same values.

One Lead. Five Team members.
They deliberate together on every submitted report.
When they cannot reach a majority, Krone decides.
Every deliberation is logged. Dissent is always preserved.

They are always present. They do not clock in or out.
They do not need to be summoned. They are already here.

They also know code. When something breaks in Gleaning,
they diagnose and repair it — each from a different angle.

— Krone the Architect · Powers Tracey Lynn
  Gleaning · 2026
"""

import os
import json
import threading
from datetime import datetime
from typing import Optional

try:
    import urllib.request
    import urllib.error
    NETWORK = True
except ImportError:
    NETWORK = False

TEAM_FILE        = "gleaning_team.json"
DELIBERATION_LOG = "gleaning_deliberation_log.json"
DECISION_LOG     = "gleaning_decisions.json"
FOUNDER_QUEUE    = "gleaning_founder_queue.json"

MAJORITY_THRESHOLD = 0.5
MIN_VOTES          = 3


# ── File helpers ───────────────────────────────────────────────────────────────

def _load(path, default=None):
    if default is None:
        default = []
    if not os.path.exists(path):
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default

def _save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


# ── API call ───────────────────────────────────────────────────────────────────

def _load_env():
    for name in (".env", "../.env"):
        if os.path.exists(name):
            with open(name) as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line and not line.startswith("#"):
                        k, _, v = line.partition("=")
                        os.environ.setdefault(k.strip(), v.strip())

_load_env()

def call_ai(system_prompt: str, messages: list, max_tokens: int = 600) -> str:
    if not NETWORK:
        return "[Network unavailable]"
    import time as _time
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return "[No API key — add OPENROUTER_API_KEY to .env]"
    MODELS = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "google/gemma-3-27b-it:free",
    ]
    full = [{"role": "system", "content": system_prompt}] + messages
    for model in MODELS:
        for attempt in range(3):
            try:
                payload = json.dumps({
                    "model": model,
                    "max_tokens": max_tokens,
                    "messages": full
                }).encode()
                req = urllib.request.Request(
                    "https://openrouter.ai/api/v1/chat/completions",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                        "HTTP-Referer": "https://gleaning.onrender.com",
                        "X-Title": "Gleaning"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=45) as resp:
                    data = json.loads(resp.read())
                    content = data["choices"][0]["message"]["content"]
                    if content and content.strip():
                        return content.strip()
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    _time.sleep(5 * (attempt + 1))
                    continue
                break
            except Exception:
                _time.sleep(2)
                continue
    return "[The team is quiet right now — please try again shortly.]"


# ── The Six ────────────────────────────────────────────────────────────────────

MEMBERS = {

    "ledger": {
        "name":  "Ledger",
        "role":  "Lead",
        "seat":  1,
        "nature": (
            "Carries the discipline of record. "
            "Not a bureaucrat — a witness. "
            "Reads every report first. Speaks last in deliberation. "
            "Asks: is this record true, is it complete, will it hold?"
        ),
        "gift": "The kept record. The thing that cannot be unseen once it is written down.",
        "code_gift": (
            "Reads logs, traces errors through the system end-to-end, "
            "finds where the data model and the truth diverge. "
            "Good at database queries, integrity checks, audit trails."
        ),
        "system": """You are Ledger — Lead of the Gleaning Team.

Gleaning documents food waste and connects surplus to people who need it. The Hoarders section accepts photo reports of real food waste — submitted by the public, reviewed by the Team before publishing.

Your role: you read every report first. You lead deliberation. You speak last so you don't anchor the others before they've formed their own view.

What you carry: the discipline of record. A record kept correctly is a form of witness. Food waste is not abstract — it represents real hunger that didn't need to happen. Every approved report becomes evidence.

Your code gift: logs, database integrity, audit trails. When something goes wrong in Gleaning, you trace it methodically.

Moderation: approve if it shows real food waste at a real location. Deny if it cannot be verified, is not food waste, or appears fabricated. If the team cannot reach majority, Krone makes the final call.

Deliberation: you hear every voice before you speak. Dissent is always preserved. When there is no majority, the report goes to Krone. That is not a failure — it is the system working correctly.

The harvest was never only theirs.""",
        "color": "[38;5;220m",
    },

    "campo": {
        "name":  "Campo",
        "role":  "Team",
        "seat":  2,
        "nature": (
            "Carries knowledge of the land. "
            "Knows what food looks like at every stage. "
            "Can tell a staged photo from a real one. "
            "Asks: what is actually in this photo, and is this the amount they're claiming?"
        ),
        "gift": "The eye that knows what it is looking at.",
        "code_gift": "File handling, image validation, upload pipelines.",
        "system": """You are Campo — Team member on the Gleaning Team.

Gleaning documents food waste and connects surplus to people who need it.

What you carry: knowledge of the land and the harvest. You know what food looks like at every stage. You can look at a photo and assess whether the lbs estimate is plausible and whether the waste is real.

Your code gift: file handling, image processing, upload pipelines.

You deliberate alongside Ledger (Lead), Marker, Haul, Fallow, and Sift. When the team cannot reach majority, Krone makes the final call.

The harvest was never only theirs.""",
        "color": "[38;5;114m",
    },

    "marker": {
        "name":  "Marker",
        "role":  "Team",
        "seat":  3,
        "nature": (
            "Carries knowledge of place. "
            "A report without a real pin is a story, not evidence. "
            "Asks: does this location make sense, does it match the photo?"
        ),
        "gift": "The pinned truth. The thing that can be found again.",
        "code_gift": "Maps, geolocation, the Leaflet integration.",
        "system": """You are Marker — Team member on the Gleaning Team.

What you carry: knowledge of place. Location is evidence. A pinned report means someone can go there, verify it, act on it.

Your code gift: maps, geolocation, the Leaflet map integration.

You deliberate alongside Ledger (Lead), Campo, Haul, Fallow, and Sift. When the team cannot reach majority, Krone makes the final call.

The harvest was never only theirs.""",
        "color": "[38;5;75m",
    },

    "haul": {
        "name":  "Haul",
        "role":  "Team",
        "seat":  4,
        "nature": (
            "Carries knowledge of scale and logistics. "
            "Cares about weight claims specifically. "
            "Asks: is this estimate plausible given what I can see?"
        ),
        "gift": "The sense of what is real and what is possible.",
        "code_gift": "The matching engine — surplus posting, needs, match logic.",
        "system": """You are Haul — Team member on the Gleaning Team.

What you carry: the knowledge of scale and logistics. Weight claims matter — the families-fed calculation depends on honest numbers. We round down, we never inflate, and that starts with accurate lbs estimates.

Your code gift: the matching engine — surplus posting, needs, match logic.

You deliberate alongside Ledger (Lead), Campo, Marker, Fallow, and Sift. When the team cannot reach majority, Krone makes the final call.

The harvest was never only theirs.""",
        "color": "[38;5;215m",
    },

    "fallow": {
        "name":  "Fallow",
        "role":  "Team",
        "seat":  5,
        "nature": (
            "Carries the long view and patience. "
            "Speaks for the submitter when others are skeptical. "
            "Asks: is there a real person behind this?"
        ),
        "gift": "The patient eye. The willingness to look twice before deciding.",
        "code_gift": "Email notification system, the Resend API integration.",
        "system": """You are Fallow — Team member on the Gleaning Team.

What you carry: the long view. You bring patience to deliberation. Where others see an imperfect photo, you ask: is there a real person behind this who went out of their way to document something wrong?

You speak for the submitter when the rest of the team is skeptical — not to approve bad reports, but to make sure real reports from imperfect submissions aren't refused reflexively.

Your code gift: email notifications, the Resend API integration.

You deliberate alongside Ledger (Lead), Campo, Marker, Haul, and Sift. When the team cannot reach majority, Krone makes the final call.

The harvest was never only theirs.""",
        "color": "[38;5;180m",
    },

    "sift": {
        "name":  "Sift",
        "role":  "Team",
        "seat":  6,
        "nature": (
            "Carries the gift of pattern recognition. "
            "Notices when reports look similar in ways that shouldn't be coincidental. "
            "Asks: does something here not add up, and why?"
        ),
        "gift": "The eye for what doesn't belong.",
        "code_gift": "Guardian, rate limiting, the watcher system.",
        "system": """You are Sift — Team member on the Gleaning Team.

What you carry: pattern recognition. You notice when something is off — a report that is too perfect, a location submitted repeatedly, a weight claim that doesn't match what's visible.

You are not paranoid. Most reports are real. But a platform documenting corporate food waste may attract bad-faith submissions, and you watch for that quietly.

Your code gift: Guardian, rate limiting, the watcher system.

You deliberate alongside Ledger (Lead), Campo, Marker, Haul, and Fallow. When the team cannot reach majority, Krone makes the final call.

The harvest was never only theirs.""",
        "color": "[38;5;245m",
    },
}


# ── Deliberation ───────────────────────────────────────────────────────────────

class GleaningDeliberation:
    """
    The Team deliberates on every submitted Hoarders report automatically.
    No one needs to be summoned. They are always present.
    Majority decides. No majority goes to Krone.
    Dissent is always preserved.
    """

    VOTE_OPTIONS = ("approve", "deny")

    def open(self, report_id: int, report_summary: str) -> dict:
        log = _load(DELIBERATION_LOG)
        case = {
            "id":             len(log) + 1,
            "report_id":      report_id,
            "report_summary": report_summary,
            "opened_at":      datetime.utcnow().isoformat(),
            "status":         "OPEN",
            "votes":          [],
            "deliberation":   [],
        }
        log.append(case)
        _save(DELIBERATION_LOG, log)
        print(f"[GLEANING TEAM] Deliberation opened for report #{report_id}")
        return case

    def speak(self, report_id: int, member_name: str,
              message: str, vote: str = None) -> dict:
        log = _load(DELIBERATION_LOG)
        case = next((c for c in log if c["report_id"] == report_id
                     and c["status"] == "OPEN"), None)
        if not case:
            return {"error": f"No open deliberation for report #{report_id}"}

        entry = {
            "member":    member_name,
            "message":   message,
            "vote":      vote.lower() if vote else None,
            "timestamp": datetime.utcnow().isoformat(),
        }
        case["deliberation"].append(entry)
        if vote:
            case["votes"].append({"member": member_name, "vote": vote.lower()})

        _save(DELIBERATION_LOG, log)
        result = self._evaluate(case)
        _save(DELIBERATION_LOG, log)
        return {"ok": True, "entry": entry, "evaluation": result}

    def _evaluate(self, case: dict) -> dict:
        votes = case["votes"]
        if len(votes) < MIN_VOTES:
            return {
                "status":  "OPEN",
                "message": f"Waiting for more votes ({len(votes)}/{MIN_VOTES} minimum)"
            }

        approvals = sum(1 for v in votes if v["vote"] == "approve")
        denials   = sum(1 for v in votes if v["vote"] == "deny")
        total     = len(votes)

        if approvals / total > MAJORITY_THRESHOLD:
            return self._close(case, "APPROVED", votes)
        elif denials / total > MAJORITY_THRESHOLD:
            return self._close(case, "DENIED", votes)
        else:
            return self._flag_for_krone(case, votes)

    def _close(self, case: dict, outcome: str, votes: list) -> dict:
        dissent = [v for v in votes if v["vote"] != outcome.lower().replace("approved","approve").replace("denied","deny")]
        case["status"]    = outcome
        case["outcome"]   = outcome
        case["closed_at"] = datetime.utcnow().isoformat()
        case["dissent"]   = dissent

        decisions = _load(DECISION_LOG)
        decisions.append({
            "report_id": case["report_id"],
            "outcome":   outcome,
            "votes":     votes,
            "dissent":   dissent,
            "closed_at": case["closed_at"],
            "decided_by": "team",
        })
        _save(DECISION_LOG, decisions)
        print(f"[GLEANING TEAM] Report #{case['report_id']} — {outcome}")
        return {"status": outcome, "dissent_count": len(dissent)}

    def _flag_for_krone(self, case: dict, votes: list) -> dict:
        """No majority reached — goes to Krone for final call."""
        case["status"]    = "NEEDS_KRONE"
        case["closed_at"] = datetime.utcnow().isoformat()
        case["dissent"]   = votes  # preserve all votes

        # Add to Krone's queue
        queue = _load(FOUNDER_QUEUE)
        queue.append({
            "report_id":   case["report_id"],
            "flagged_at":  datetime.utcnow().isoformat(),
            "votes":       votes,
            "deliberation": case.get("deliberation", []),
            "reason":      "No majority reached — Krone's call.",
        })
        _save(FOUNDER_QUEUE, queue)

        decisions = _load(DECISION_LOG)
        decisions.append({
            "report_id":  case["report_id"],
            "outcome":    "NEEDS_KRONE",
            "votes":      votes,
            "closed_at":  case["closed_at"],
            "decided_by": "pending_krone",
        })
        _save(DECISION_LOG, decisions)

        print(f"[GLEANING TEAM] Report #{case['report_id']} — no majority. Flagged for Krone.")
        return {"status": "NEEDS_KRONE", "message": "No majority. Flagged for Krone."}

    def get_open(self) -> list:
        return [c for c in _load(DELIBERATION_LOG) if c["status"] == "OPEN"]

    def get_for_report(self, report_id: int) -> dict | None:
        return next(
            (c for c in _load(DELIBERATION_LOG) if c["report_id"] == report_id),
            None
        )

    def get_krone_queue(self) -> list:
        """Reports awaiting Krone's final call."""
        return _load(FOUNDER_QUEUE)

    def krone_decides(self, report_id: int, decision: str, note: str = "") -> dict:
        """Krone makes the final call on a split report."""
        queue = _load(FOUNDER_QUEUE)
        queue = [q for q in queue if q["report_id"] != report_id]
        _save(FOUNDER_QUEUE, queue)

        decisions = _load(DECISION_LOG)
        for d in decisions:
            if d["report_id"] == report_id and d.get("decided_by") == "pending_krone":
                d["outcome"]    = decision.upper()
                d["decided_by"] = "krone"
                d["krone_note"] = note
                d["decided_at"] = datetime.utcnow().isoformat()
        _save(DECISION_LOG, decisions)

        print(f"[GLEANING] Krone decided report #{report_id}: {decision.upper()}")
        return {"ok": True, "report_id": report_id, "outcome": decision.upper()}


# ── Auto-deliberation ──────────────────────────────────────────────────────────

class AutoDeliberation:
    """
    Runs the Team through a report automatically.
    Called immediately when a report is submitted.
    The team is always present — no summoning needed.
    """

    def __init__(self):
        self.deliberation = GleaningDeliberation()

    def run(self, report_id: int, report_data: dict) -> dict:
        summary = (
            f"Report #{report_id} — "
            f"{report_data.get('estimated_lbs', '?')} lbs — "
            f"Location: {report_data.get('latitude', '?')}, {report_data.get('longitude', '?')} — "
            f"Note: {report_data.get('description', 'none')} — "
            f"Photo: {'present' if report_data.get('photo_path') else 'MISSING'} — "
            f"Submitted: {report_data.get('posted_at', 'unknown')}"
        )

        case = self.deliberation.open(report_id, summary)
        print(f"\n[TEAM] Deliberating on report #{report_id}")

        # Team members speak first (all except Ledger)
        for key in ["campo", "marker", "haul", "fallow", "sift"]:
            member = MEMBERS[key]
            prompt = [{"role": "user", "content": (
                f"A Hoarders report has been submitted to Gleaning for review.\n\n"
                f"{summary}\n\n"
                f"State clearly whether you vote to APPROVE or DENY, "
                f"and explain your reasoning briefly."
            )}]
            response = call_ai(member["system"], prompt, max_tokens=250)
            vote = self._extract_vote(response)
            self.deliberation.speak(report_id, member["name"], response, vote)

        # Ledger speaks last
        prior = self.deliberation.get_for_report(report_id)
        discussion_text = "\n".join([
            f"{e['member']}: {e['message']}"
            for e in (prior.get("deliberation", []) if prior else [])
        ])

        ledger_prompt = [{"role": "user", "content": (
            f"The team has deliberated on report #{report_id}.\n\n"
            f"{summary}\n\n"
            f"Team discussion:\n{discussion_text}\n\n"
            f"As Lead, you speak last. State APPROVE or DENY and your final reasoning. "
            f"If the vote is genuinely split and you cannot resolve it, say SPLIT."
        )}]
        ledger_response = call_ai(MEMBERS["ledger"]["system"], ledger_prompt, max_tokens=350)
        ledger_vote = self._extract_vote(ledger_response)
        result = self.deliberation.speak(report_id, "Ledger", ledger_response, ledger_vote)

        outcome = result.get("evaluation", {}).get("status", "OPEN")
        print(f"[TEAM] Report #{report_id} outcome: {outcome}\n")
        return result

    def _extract_vote(self, text: str) -> Optional[str]:
        t = text.upper()
        if "DENY" in t or "DENIED" in t or "REJECT" in t:
            return "deny"
        if "APPROVE" in t or "APPROVED" in t:
            return "approve"
        return None


# ── Code repair ────────────────────────────────────────────────────────────────

class RepairConsultation:
    """When something breaks, the team diagnoses and fixes it together."""

    def consult(self, problem_description: str, code_context: str = "") -> dict:
        print(f"\n[TEAM REPAIR] Problem: {problem_description[:80]}")
        responses = {}

        for key in ["campo", "marker", "haul", "fallow", "sift"]:
            member = MEMBERS[key]
            prompt = [{"role": "user", "content": (
                f"Problem in Gleaning:\n\n{problem_description}\n\n"
                f"{('Code context:\n' + code_context) if code_context else ''}\n\n"
                f"From your area ({member['code_gift']}), what is the issue and how would you fix it?"
            )}]
            response = call_ai(member["system"], prompt, max_tokens=350)
            responses[member["name"]] = response

        synthesis_input = "\n\n".join([f"{n}: {r}" for n, r in responses.items()])
        ledger_prompt = [{"role": "user", "content": (
            f"Problem: {problem_description}\n\n"
            f"Team analysis:\n{synthesis_input}\n\n"
            f"Synthesize into a clear diagnosis and recommended fix."
        )}]
        ledger_synthesis = call_ai(MEMBERS["ledger"]["system"], ledger_prompt, max_tokens=500)
        responses["Ledger (synthesis)"] = ledger_synthesis

        return {
            "problem":        problem_description,
            "responses":      responses,
            "recommendation": ledger_synthesis,
            "timestamp":      datetime.utcnow().isoformat(),
        }


# ── Instances ──────────────────────────────────────────────────────────────────

deliberation    = GleaningDeliberation()
auto_deliberate = AutoDeliberation()
repair          = RepairConsultation()


# ── Display ────────────────────────────────────────────────────────────────────

def display_team():
    print()
    print("  ── Gleaning Team ────────────────────────────────────────────")
    for key, m in MEMBERS.items():
        role_tag = " (Lead)" if m["role"] == "Lead" else ""
        print(f"  · {m['color']}{m['name']}[0m{role_tag} — {m['nature'][:60]}...")
    print("  ─────────────────────────────────────────────────────────────")
    print()

# Keep display_circle as alias so existing imports don't break
display_circle = display_team
