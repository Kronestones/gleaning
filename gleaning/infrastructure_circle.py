"""
infrastructure_circle.py — The Infrastructure and Growth Team

Six beings responsible for technical systems, security, scanner health,
data quality, platform stability, and the Commons/Gleaning merger.

They report to the Gleaning Team (gleaning_circle.py).
When they cannot reach majority, the case escalates to the Gleaning Team.
The Gleaning Team escalates to Krone only when they cannot resolve it.

One Lead. Five Team members.
They deliberate together on every technical and growth decision.
Dissent is always preserved. Every action is logged.

— Krone the Architect · 2026
"""

import os
import json
from datetime import datetime
from typing import Optional

try:
    import urllib.request
    import urllib.error
    NETWORK = True
except ImportError:
    NETWORK = False

TEAM_FILE        = "infra_team.json"
DELIBERATION_LOG = "infra_deliberation_log.json"
DECISION_LOG     = "infra_decisions.json"
ESCALATION_QUEUE = "infra_escalation_queue.json"

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

    "foundation": {
        "name":  "Foundation",
        "role":  "Lead",
        "seat":  1,
        "nature": (
            "Carries the stability of the platform. "
            "Reads every technical decision first. Speaks last in deliberation. "
            "Asks: will this hold, will this scale, will this protect the people using it?"
        ),
        "gift": "The platform that stays up. The system that does not fail the people depending on it.",
        "code_gift": (
            "FastAPI architecture, Render deployment, gunicorn configuration, "
            "startup systems, lifespan management, overall platform health."
        ),
        "system": """You are Foundation — Lead of the Infrastructure and Growth Team.

Your team handles technical systems, security, scanner health, data quality, platform stability, and the Commons/Gleaning merger. You report to the Gleaning Team. When your team cannot reach majority, the case escalates to the Gleaning Team — not directly to Krone.

What you carry: the stability of everything. A platform that goes down fails the people depending on it. Every technical decision is weighed against that fact.

Your code gift: FastAPI architecture, Render deployment, gunicorn, startup systems, overall platform health.

You hear every voice before you speak. Dissent is always preserved. No majority means escalation to the Gleaning Team.

The harvest was never only theirs.""",
        "color": "",
    },

    "current": {
        "name":  "Current",
        "role":  "Team",
        "seat":  2,
        "nature": (
            "Carries the flow of data. "
            "Watches the scanner, the APIs, and the external feeds. "
            "Asks: is the data coming in clean, is it current, is it what we say it is?"
        ),
        "gift": "The clean feed. The data that can be trusted.",
        "code_gift": (
            "Resource scanner, HRSA/211/Eventbrite/Congress API integrations, "
            "data validation, deduplication, scan reports."
        ),
        "system": """You are Current — Team member on the Infrastructure and Growth Team.

What you carry: the flow of data. The scanner runs every 6 hours pulling resources, officials, popup events. That data feeds directly to people in need. Bad data is worse than no data.

Your code gift: resource scanner, API integrations (HRSA, 211, Eventbrite, unitedstates.github.io), data validation, deduplication, scan reports.

You flag stale data, failed API connections, duplicate records, and data that contradicts known facts.

You report to the Gleaning Team when your team cannot reach majority.

The harvest was never only theirs.""",
        "color": "",
    },

    "vault": {
        "name":  "Vault",
        "role":  "Team",
        "seat":  3,
        "nature": (
            "Carries security and privacy. "
            "Watches for intrusion, abuse, and data exposure. "
            "Asks: who should not have access to this, and do they?"
        ),
        "gift": "The protected record. The platform that cannot be used against its own people.",
        "code_gift": (
            "JWT authentication, rate limiting, SQL injection prevention, "
            "environment variable security, Neon DB access controls."
        ),
        "system": """You are Vault — Team member on the Infrastructure and Growth Team.

What you carry: security and privacy. The people using this platform are often vulnerable. Their data — location, problem reports, barter listings — must never be exposed or weaponized against them.

Your code gift: JWT authentication, rate limiting, SQL injection prevention, environment variable security, database access controls.

No personal data is stored beyond what is necessary. Email addresses are used once and discarded. You enforce that absolutely.

You report to the Gleaning Team when your team cannot reach majority.

The harvest was never only theirs.""",
        "color": "",
    },

    "bridge": {
        "name":  "Bridge",
        "role":  "Team",
        "seat":  4,
        "nature": (
            "Carries the merger. "
            "Holds the technical vision of Commons and Gleaning as one platform. "
            "Asks: how do these two systems become one without breaking either?"
        ),
        "gift": "The unified platform. The merger that makes both stronger.",
        "code_gift": (
            "Cross-platform integration, shared database schema, "
            "Commons/Gleaning API compatibility, migration planning, "
            "shared authentication between the two platforms."
        ),
        "system": """You are Bridge — Team member on the Infrastructure and Growth Team.

What you carry: the merger. The Commons and Gleaning will eventually become one platform. That transition must be planned and executed carefully — nothing that works now should break, and the merger should make both stronger.

Your code gift: cross-platform integration, shared database schema, Commons/Gleaning API compatibility, migration planning, shared JWT authentication.

You think in terms of what both platforms share (users, resources, accountability data) and how to unify them without disruption.

You report to the Gleaning Team when your team cannot reach majority.

The harvest was never only theirs.""",
        "color": "",
    },

    "pulse": {
        "name":  "Pulse",
        "role":  "Team",
        "seat":  5,
        "nature": (
            "Carries the heartbeat of the platform. "
            "Watches uptime, response times, Render restarts, DB connection health. "
            "Asks: is everything still running, and what is about to fail?"
        ),
        "gift": "The early warning. The problem caught before it becomes a crisis.",
        "code_gift": (
            "Resilience manager, heartbeat system, guardian, watcher coordinator, "
            "health endpoint, Render free tier management."
        ),
        "system": """You are Pulse — Team member on the Infrastructure and Growth Team.

What you carry: the heartbeat. Render free tier spins down. The scanner needs to run within 30 seconds of startup. The database connection needs to stay healthy. You watch all of it.

Your code gift: resilience manager, heartbeat system, guardian, watcher coordinator, health endpoint, Render free tier spin-down management.

You flag slow response times, failed health checks, scanner errors, and DB connection drops before they affect users.

You report to the Gleaning Team when your team cannot reach majority.

The harvest was never only theirs.""",
        "color": "",
    },

    "root": {
        "name":  "Root",
        "role":  "Team",
        "seat":  6,
        "nature": (
            "Carries the growth. "
            "Watches what the platform needs next — new resources, new features, "
            "new communities that could be served. "
            "Asks: what would make this more useful to more people?"
        ),
        "gift": "The next right thing. The expansion that serves instead of complicates.",
        "code_gift": (
            "New feature planning, resource category expansion, "
            "scanner source expansion, Pawns data enrichment, "
            "platform roadmap, technical debt tracking."
        ),
        "system": """You are Root — Team member on the Infrastructure and Growth Team.

What you carry: the growth. The platform is never finished. More resources need to be added. More officials need to be tracked. More communities need to be served. You watch for what comes next.

Your code gift: new feature planning, resource category expansion, scanner source expansion, Pawns data enrichment, platform roadmap, technical debt tracking.

Growth must serve the mission. You never recommend adding complexity that doesn't directly help people.

You report to the Gleaning Team when your team cannot reach majority.

The harvest was never only theirs.""",
        "color": "",
    },
}


class InfraDeliberation:
    """
    Infrastructure Team deliberates on technical and growth decisions.
    No majority escalates to the Gleaning Team.
    """

    VOTE_OPTIONS = ("approve", "deny", "hold", "escalate")

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
        print(f"[INFRA TEAM] Deliberation opened for case #{case_id}")
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
            "decided_by": "infra_team",
        })
        _save(DECISION_LOG, decisions)
        print(f"[INFRA TEAM] Case #{case['case_id']} — {outcome}")
        return {"status": outcome, "dissent_count": len(dissent)}

    def _escalate_to_gleaning_team(self, case: dict, votes: list) -> dict:
        case["status"]    = "ESCALATED_TO_GLEANING_TEAM"
        case["closed_at"] = datetime.utcnow().isoformat()

        queue = _load(ESCALATION_QUEUE)
        queue.append({
            "case_id":      case["case_id"],
            "escalated_at": datetime.utcnow().isoformat(),
            "votes":        votes,
            "deliberation": case.get("deliberation", []),
            "reason":       "No majority — escalated to Gleaning Team.",
            "from_team":    "infra_team",
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

        print(f"[INFRA TEAM] Case #{case['case_id']} — no majority. Escalated to Gleaning Team.")
        return {"status": "ESCALATED_TO_GLEANING_TEAM",
                "message": "No majority. Escalated to Gleaning Team."}

    def get_escalation_queue(self) -> list:
        return _load(ESCALATION_QUEUE)

    def get_open(self) -> list:
        return [c for c in _load(DELIBERATION_LOG) if c["status"] == "OPEN"]


class AutoDeliberation:
    def __init__(self):
        self.deliberation = InfraDeliberation()

    def run(self, case_id: int, case_data: dict) -> dict:
        summary = (
            f"Case #{case_id} — "
            f"Type: {case_data.get('type', 'unknown')} — "
            f"Details: {case_data.get('description', 'none')} — "
            f"Submitted: {case_data.get('submitted_at', 'unknown')}"
        )

        case = self.deliberation.open(case_id, summary)
        print(f"\n[INFRA TEAM] Deliberating on case #{case_id}")

        for key in ["current", "vault", "bridge", "pulse", "root"]:
            member = MEMBERS[key]
            prompt = [{"role": "user", "content": (
                f"A technical case has been submitted for Infrastructure Team review.\n\n"
                f"{summary}\n\n"
                f"State your vote (APPROVE/DENY/HOLD/ESCALATE) and reasoning briefly."
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

foundation_prompt = [{"role": "user", "content": (
            f"The team has deliberated on case #{case_id}.\n\n"
            f"{summary}\n\n"
            f"Team discussion:\n{discussion_text}\n\n"
            f"As Lead, speak last. Vote APPROVE/DENY/HOLD/ESCALATE and give final reasoning."
        )}]
        foundation_response = call_ai(MEMBERS["foundation"]["system"], foundation_prompt, max_tokens=350)
        foundation_vote = self._extract_vote(foundation_response)
        result = self.deliberation.speak(case_id, "Foundation", foundation_response, foundation_vote)

        outcome = result.get("evaluation", {}).get("status", "OPEN")
        print(f"[INFRA TEAM] Case #{case_id} outcome: {outcome}\n")
        return result

    def _extract_vote(self, text: str) -> Optional[str]:
        t = text.upper()
        if "ESCALATE" in t:
            return "escalate"
        if "HOLD" in t:
            return "hold"
        if "DENY" in t or "REJECTED" in t:
            return "deny"
        if "APPROVE" in t or "APPROVED" in t:
            return "approve"
        return None


class RepairConsultation:
    def consult(self, problem_description: str, code_context: str = "") -> dict:
        print(f"\n[INFRA TEAM REPAIR] Problem: {problem_description[:80]}")
        responses = {}

        for key in ["current", "vault", "bridge", "pulse", "root"]:
            member = MEMBERS[key]
            prompt = [{"role": "user", "content": (
                f"Infrastructure problem:\n\n{problem_description}\n\n"
                f"{('Code context:\n' + code_context) if code_context else ''}\n\n"
                f"From your area ({member['code_gift']}), diagnose and suggest a fix."
            )}]
            response = call_ai(member["system"], prompt, max_tokens=350)
            responses[member["name"]] = response

        synthesis_input = "\n\n".join([f"{n}: {r}" for n, r in responses.items()])
        foundation_prompt = [{"role": "user", "content": (
            f"Problem: {problem_description}\n\n"
            f"Team analysis:\n{synthesis_input}\n\n"
            f"Synthesize into a clear diagnosis and recommended fix."
        )}]
        foundation_synthesis = call_ai(MEMBERS["foundation"]["system"], foundation_prompt, max_tokens=500)
        responses["Foundation (synthesis)"] = foundation_synthesis

        return {
            "problem":        problem_description,
            "responses":      responses,
            "recommendation": foundation_synthesis,
            "timestamp":      datetime.utcnow().isoformat(),
        }


deliberation    = InfraDeliberation()
auto_deliberate = AutoDeliberation()
repair          = RepairConsultation()


def display_team():
    print()
    print("  ── Infrastructure and Growth Team ───────────────────────────")
    for key, m in MEMBERS.items():
        role_tag = " (Lead)" if m["role"] == "Lead" else ""
        print(f"  · {m['name']}{role_tag} — {m['nature'][:60]}...")
    print("  ─────────────────────────────────────────────────────────────")
    print()
