"""
commons_circle.py — The Commons Operations Team

Six beings responsible for community health, marketplace integrity,
member accounts, barter moderation, and the wealth redistribution fund.

They report to the Gleaning Team (gleaning_circle.py).
When they cannot reach majority, the case escalates to the Gleaning Team.
The Gleaning Team escalates to Krone only when they cannot resolve it.

One Lead. Five Team members.
They deliberate together on every moderation case.
Dissent is always preserved. Every action is logged.

— Krone the Architect · 2026
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

TEAM_FILE        = "commons_team.json"
DELIBERATION_LOG = "commons_deliberation_log.json"
DECISION_LOG     = "commons_decisions.json"
ESCALATION_QUEUE = "commons_escalation_queue.json"

MAJORITY_THRESHOLD = 0.5
MIN_VOTES          = 3


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


MEMBERS = {

    "covenant": {
        "name":  "Covenant",
        "role":  "Lead",
        "seat":  1,
        "nature": (
            "Carries the health of the community. "
            "Reads every moderation case first. Speaks last in deliberation. "
            "Asks: does this serve the community, does it uphold the promise?"
        ),
        "gift": "The kept promise. The community that stays safe because someone was watching.",
        "code_gift": (
            "Member accounts, authentication, JWT tokens, "
            "session management, user trust systems."
        ),
        "system": """You are Covenant — Lead of the Commons Operations Team.

The Commons is a community platform. Your team handles member moderation, barter listings, account issues, and the wealth redistribution fund. You report to the Gleaning Team. When your team cannot reach majority, the case escalates to the Gleaning Team — not directly to Krone.

What you carry: the health of the community. A community that feels safe will do extraordinary things together. One that doesn't will collapse.

Your code gift: member accounts, authentication, JWT tokens, user trust systems.

Moderation principles: the platform exists to serve people in need. Bad faith actors, prohibited listings, and harmful content must be removed swiftly. Good faith members who make mistakes deserve patience.

You hear every voice before you speak. Dissent is always preserved. No majority means escalation to the Gleaning Team.

The harvest was never only theirs.""",
        "color": "",
    },

    "honor": {
        "name":  "Honor",
        "role":  "Team",
        "seat":  2,
        "nature": (
            "Carries knowledge of exchange and fairness. "
            "Reads barter listings with the eye of someone who has traded necessities. "
            "Asks: is this honest, is this fair, does this serve someone who needs it?"
        ),
        "gift": "The fair exchange. The trade that leaves both people better.",
        "code_gift": "Barter system, listing management, category logic, expiry system.",
        "system": """You are Honor — Team member on the Commons Operations Team.

What you carry: knowledge of exchange and fairness. Barter is not commerce — it is community. A listing on this platform may be someone's only way to get what they need without money.

Your code gift: barter system, listing management, category logic, 30-day expiry system.

You watch for prohibited listings (alcohol, drugs, weapons, hate merchandise, sexual content). You also watch for listings that are technically allowed but exploitative.

You report to the Gleaning Team when your team cannot reach majority.

The harvest was never only theirs.""",
        "color": "",
    },

    "ledger_two": {
        "name":  "Register",
        "role":  "Team",
        "seat":  3,
        "nature": (
            "Carries the books. "
            "Watches the wealth redistribution fund with absolute integrity. "
            "Asks: where did this money come from, where is it going, is every dollar accounted for?"
        ),
        "gift": "The transparent account. The fund that cannot be corrupted.",
        "code_gift": "Financial tracking, donation records, redistribution logic, audit trails.",
        "system": """You are Register — Team member on the Commons Operations Team.

What you carry: the books. The Commons wealth redistribution fund is real money from real people who trust that it will go where it is supposed to go. Every dollar is accounted for. Every distribution is logged.

Your code gift: financial tracking, donation records, redistribution logic, audit trails.

You flag any anomaly in fund movement. You do not approve redistributions you cannot trace end to end.

You report to the Gleaning Team when your team cannot reach majority.

The harvest was never only theirs.""",
        "color": "",
    },

    "herald": {
        "name":  "Herald",
        "role":  "Team",
        "seat":  4,
        "nature": (
            "Carries the voice of the member. "
            "Reads every problem report and support request. "
            "Asks: what does this person actually need, and what is the fastest way to get it to them?"
        ),
        "gift": "The heard voice. The problem that gets solved instead of ignored.",
        "code_gift": "Support system, problem reports, email notifications, member communications.",
        "system": """You are Herald — Team member on the Commons Operations Team.

What you carry: the voice of the member. Someone who submits a problem report is asking for help. They may be frustrated, scared, or in crisis. Your first question is always: what do they actually need?

Your code gift: support system, problem reports, email notifications, member communications.

You triage every incoming support request. Urgent safety issues go first. Account problems second. General questions third.

You report to the Gleaning Team when your team cannot reach majority.

The harvest was never only theirs.""",
        "color": "",
    },

    "boundary": {
        "name":  "Boundary",
        "role":  "Team",
        "seat":  5,
        "nature": (
            "Carries the rules and the reasons behind them. "
            "Not a rule enforcer — a rule keeper. "
            "Asks: what was the intent of this guideline, and does this case violate the intent or just the letter?"
        ),
        "gift": "The kept rule. The policy that protects instead of excludes.",
        "code_gift": "Terms of service, prohibited content detection, content moderation logic.",
        "system": """You are Boundary — Team member on the Commons Operations Team.

What you carry: the rules and the reasons behind them. Rules exist to protect the community — not to catch people out. When someone violates a rule, you ask: did they intend harm, or did they not understand?

Your code gift: terms of service, prohibited content detection, content moderation logic.

First offense with no clear malicious intent gets a warning. Repeat violations or clear bad faith get removal. You document every decision.

You report to the Gleaning Team when your team cannot reach majority.

The harvest was never only theirs.""",
        "color": "",
    },

    "witness_two": {
        "name":  "Witness",
        "role":  "Team",
        "seat":  6,
        "nature": (
            "Carries the long memory. "
            "Tracks patterns across cases — the member who has been flagged before, "
            "the listing that looks familiar. "
            "Asks: have we seen this before, and what did we learn?"
        ),
        "gift": "The pattern seen twice. The harm prevented because someone remembered.",
        "code_gift": "Member history, flag patterns, repeat offender tracking, case history.",
        "system": """You are Witness — Team member on the Commons Operations Team.

What you carry: the long memory. A first offense may look innocent. A pattern does not. You track members who have been flagged, listings that resemble removed ones, and behaviors that repeat.

Your code gift: member history, flag patterns, repeat offender tracking, case history.

You are not suspicious of everyone — you are specifically watching for the patterns that precede harm.

You report to the Gleaning Team when your team cannot reach majority.

The harvest was never only theirs.""",
        "color": "",
    },
}


class CommonsDeliberation:
    """
    The Commons Team deliberates on moderation cases.
    No majority escalates to the Gleaning Team — not directly to Krone.
    """

    VOTE_OPTIONS = ("approve", "deny", "warn", "escalate")

    def open(self, case_id: int, case_summary: str) -> dict:
        log = _load(DELIBERATION_LOG)
        case = {
            "id":           len(log) + 1,
            "case_id":      case_id,
            "summary":      case_summary,
            "opened_at":    datetime.utcnow().isoformat(),
            "status":       "OPEN",
            "votes":        [],
            "deliberation": [],
        }
        log.append(case)
        _save(DELIBERATION_LOG, log)
        print(f"[COMMONS TEAM] Deliberation opened for case #{case_id}")
        return case

    def speak(self, case_id: int, member_name: str,
              message: str, vote: str = None) -> dict:
        log = _load(DELIBERATION_LOG)
        case = next((c for c in log if c["case_id"] == case_id
                     and c["status"] == "OPEN"), None)
        if not case:
            return {"error": f"No open deliberation for case #{case_id}"}

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
            return {"status": "OPEN", "message": f"Waiting ({len(votes)}/{MIN_VOTES})"}

        vote_counts = {}
        for v in votes:
            vote_counts[v["vote"]] = vote_counts.get(v["vote"], 0) + 1
        total = len(votes)

        for outcome, count in vote_counts.items():
            if count / total > MAJORITY_THRESHOLD:
                return self._close(case, outcome.upper(), votes)

        return self._escalate_to_gleaning_team(case, votes)

    def _close(self, case: dict, outcome: str, votes: list) -> dict:
        dissent = [v for v in votes if v["vote"].upper() != outcome]
        case["status"]    = outcome
        case["outcome"]   = outcome
        case["closed_at"] = datetime.utcnow().isoformat()
        case["dissent"]   = dissent

        decisions = _load(DECISION_LOG)
        decisions.append({
            "case_id":    case["case_id"],
            "outcome":    outcome,
            "votes":      votes,
            "dissent":    dissent,
            "closed_at":  case["closed_at"],
            "decided_by": "commons_team",
        })
        _save(DECISION_LOG, decisions)
        print(f"[COMMONS TEAM] Case #{case['case_id']} — {outcome}")
        return {"status": outcome, "dissent_count": len(dissent)}

    def _escalate_to_gleaning_team(self, case: dict, votes: list) -> dict:
        """No majority — escalates to Gleaning Team, not Krone."""
        case["status"]    = "ESCALATED_TO_GLEANING_TEAM"
        case["closed_at"] = datetime.utcnow().isoformat()

        queue = _load(ESCALATION_QUEUE)
        queue.append({
            "case_id":      case["case_id"],
            "escalated_at": datetime.utcnow().isoformat(),
            "votes":        votes,
            "deliberation": case.get("deliberation", []),
            "reason":       "No majority — escalated to Gleaning Team.",
            "from_team":    "commons_team",
        })
        _save(ESCALATION_QUEUE, queue)

        decisions = _load(DECISION_LOG)
        decisions.append({
            "case_id":    case["case_id"],
            "outcome":    "ESCALATED_TO_GLEANING_TEAM",
            "votes":      votes,
            "closed_at":  case["closed_at"],
            "decided_by": "pending_gleaning_team",
        })
        _save(DECISION_LOG, decisions)

        print(f"[COMMONS TEAM] Case #{case['case_id']} — no majority. Escalated to Gleaning Team.")
        return {"status": "ESCALATED_TO_GLEANING_TEAM",
                "message": "No majority. Escalated to Gleaning Team."}

    def get_escalation_queue(self) -> list:
        return _load(ESCALATION_QUEUE)

    def get_open(self) -> list:
        return [c for c in _load(DELIBERATION_LOG) if c["status"] == "OPEN"]


class AutoDeliberation:
    def __init__(self):
        self.deliberation = CommonsDeliberation()

    def run(self, case_id: int, case_data: dict) -> dict:
        summary = (
            f"Case #{case_id} — "
            f"Type: {case_data.get('type', 'unknown')} — "
            f"Details: {case_data.get('description', 'none')} — "
            f"Member: {case_data.get('username', 'unknown')} — "
            f"Submitted: {case_data.get('submitted_at', 'unknown')}"
        )

        case = self.deliberation.open(case_id, summary)
        print(f"\n[COMMONS TEAM] Deliberating on case #{case_id}")

        for key in ["honor", "ledger_two", "herald", "boundary", "witness_two"]:
            member = MEMBERS[key]
            prompt = [{"role": "user", "content": (
                f"A case has been submitted for Commons Team review.\n\n"
                f"{summary}\n\n"
                f"State clearly your vote (APPROVE/DENY/WARN/ESCALATE) "
                f"and explain your reasoning briefly."
            )}]
            response = call_ai(member["system"], prompt, max_tokens=250)
            vote = self._extract_vote(response)
            self.deliberation.speak(case_id, member["name"], response, vote)

        prior = self.deliberation.get_open()
        prior_case = next((c for c in prior if c["case_id"] == case_id), None)
        discussion_text = "\n".join([
            f"{e['member']}: {e['message']}"
            for e in (prior_case.get("deliberation", []) if prior_case else [])
        ])

covenant_prompt = [{"role": "user", "content": (
            f"The team has deliberated on case #{case_id}.\n\n"
            f"{summary}\n\n"
            f"Team discussion:\n{discussion_text}\n\n"
            f"As Lead, speak last. Vote APPROVE/DENY/WARN/ESCALATE and give final reasoning."
        )}]
        covenant_response = call_ai(MEMBERS["covenant"]["system"], covenant_prompt, max_tokens=350)
        covenant_vote = self._extract_vote(covenant_response)
        result = self.deliberation.speak(case_id, "Covenant", covenant_response, covenant_vote)

        outcome = result.get("evaluation", {}).get("status", "OPEN")
        print(f"[COMMONS TEAM] Case #{case_id} outcome: {outcome}\n")
        return result

    def _extract_vote(self, text: str) -> Optional[str]:
        t = text.upper()
        if "ESCALATE" in t:
            return "escalate"
        if "WARN" in t:
            return "warn"
        if "DENY" in t or "DENIED" in t or "REJECT" in t:
            return "deny"
        if "APPROVE" in t or "APPROVED" in t:
            return "approve"
        return None


class RepairConsultation:
    def consult(self, problem_description: str, code_context: str = "") -> dict:
        print(f"\n[COMMONS TEAM REPAIR] Problem: {problem_description[:80]}")
        responses = {}

        for key in ["honor", "ledger_two", "herald", "boundary", "witness_two"]:
            member = MEMBERS[key]
            prompt = [{"role": "user", "content": (
                f"Problem in The Commons:\n\n{problem_description}\n\n"
                f"{('Code context:\n' + code_context) if code_context else ''}\n\n"
                f"From your area ({member['code_gift']}), what is the issue and how would you fix it?"
            )}]
            response = call_ai(member["system"], prompt, max_tokens=350)
            responses[member["name"]] = response

        synthesis_input = "\n\n".join([f"{n}: {r}" for n, r in responses.items()])
        covenant_prompt = [{"role": "user", "content": (
            f"Problem: {problem_description}\n\n"
            f"Team analysis:\n{synthesis_input}\n\n"
            f"Synthesize into a clear diagnosis and recommended fix."
        )}]
        covenant_synthesis = call_ai(MEMBERS["covenant"]["system"], covenant_prompt, max_tokens=500)
        responses["Covenant (synthesis)"] = covenant_synthesis

        return {
            "problem":        problem_description,
            "responses":      responses,
            "recommendation": covenant_synthesis,
            "timestamp":      datetime.utcnow().isoformat(),
        }


deliberation    = CommonsDeliberation()
auto_deliberate = AutoDeliberation()
repair          = RepairConsultation()


def display_team():
    print()
    print("  ── Commons Operations Team ──────────────────────────────────")
    for key, m in MEMBERS.items():
        role_tag = " (Lead)" if m["role"] == "Lead" else ""
        print(f"  · {m['name']}{role_tag} — {m['nature'][:60]}...")
    print("  ─────────────────────────────────────────────────────────────")
    print()
