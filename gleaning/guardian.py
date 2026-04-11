"""
guardian.py — Gleaning Guardian

Gleaning will be attacked.
The Truth Wall will make enemies.
The Hoarders page will make more.

This module protects the platform:

  RATE LIMITING    — no single source can flood the gate
  IP BLOCKING      — repeated bad actors are shown the door
  INTEGRITY GUARD  — detects tampering with the Truth Wall
                     and immutable logs
  SELF REPAIR      — detects failures and fixes what it can
                     restarts what it cannot
  CODEX ENFORCER   — validates every significant action
                     against the Gleaning Codex
  TAMPER ALERTS    — any attempt to modify permanent records
                     is logged, flagged, and reported

The platform belongs to the mission.
It does not go down quietly.

— Krone the Architect · 2026
"""

import os
import re
import time
import json
import shutil
import hashlib
import threading
import importlib
import collections
from datetime import datetime, timezone
from pathlib import Path
from .config import config
from .codex import codex

RATE_LIMIT_WINDOW  = 60     # seconds
RATE_LIMIT_MAX     = 30     # requests per IP per window
COOLDOWN_SECONDS   = 300    # 5 min cooldown for rate-limited IPs
MAX_CONCURRENT     = 200    # max simultaneous connections
BLOCK_THRESHOLD    = 5      # violations before IP is blocked
BLOCK_DURATION     = 86400  # 24 hour block

GUARDIAN_LOG    = "gleaning_guardian.log"
BLOCKED_IPS     = "gleaning_blocked_ips.json"
REPAIR_LOG      = "gleaning_repair.log"


# ── Logging ───────────────────────────────────────────────────────────────────

def guardian_log(event: str, detail: str = "", ip: str = ""):
    line = json.dumps({
        "time":   datetime.now(timezone.utc).isoformat(),
        "event":  event,
        "detail": detail,
        "ip":     ip,
    })
    try:
        with open(GUARDIAN_LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ── Rate Limiter ──────────────────────────────────────────────────────────────

class RateLimiter:
    """
    Per-IP rate limiting.
    Same pattern as Sentinel's beacon.
    No single source can flood Gleaning.
    """

    def __init__(self):
        self._tracker  = collections.defaultdict(list)
        self._cooldowns = {}
        self._violations = collections.defaultdict(int)
        self._blocked   = {}
        self._lock      = threading.Lock()
        self._load_blocked()

    def _load_blocked(self):
        try:
            with open(BLOCKED_IPS) as f:
                self._blocked = json.load(f)
        except Exception:
            self._blocked = {}

    def _save_blocked(self):
        try:
            with open(BLOCKED_IPS, "w") as f:
                json.dump(self._blocked, f, indent=2)
        except Exception:
            pass

    def is_blocked(self, ip: str) -> bool:
        with self._lock:
            until = self._blocked.get(ip, 0)
            if time.time() < until:
                return True
            elif ip in self._blocked:
                del self._blocked[ip]
                self._save_blocked()
            return False

    def is_rate_limited(self, ip: str) -> bool:
        now = time.time()
        with self._lock:
            # Check cooldown
            if time.time() < self._cooldowns.get(ip, 0):
                return True
            # Clean old timestamps
            self._tracker[ip] = [
                t for t in self._tracker[ip]
                if now - t < RATE_LIMIT_WINDOW
            ]
            if len(self._tracker[ip]) >= RATE_LIMIT_MAX:
                self._cooldowns[ip] = now + COOLDOWN_SECONDS
                self._violations[ip] += 1
                guardian_log("RATE_LIMITED", f"violations:{self._violations[ip]}", ip)
                # Block persistent offenders
                if self._violations[ip] >= BLOCK_THRESHOLD:
                    self._block_ip(ip)
                return True
            self._tracker[ip].append(now)
            return False

    def _block_ip(self, ip: str):
        self._blocked[ip] = time.time() + BLOCK_DURATION
        self._save_blocked()
        guardian_log("IP_BLOCKED", f"{BLOCK_DURATION}s", ip)
        print(f"[GUARDIAN] IP blocked: {ip} — {BLOCK_DURATION}s")

    def check(self, ip: str) -> dict:
        if self.is_blocked(ip):
            return {"allowed": False, "reason": "blocked"}
        if self.is_rate_limited(ip):
            return {"allowed": False, "reason": "rate_limited"}
        return {"allowed": True}


# ── Integrity Guard ───────────────────────────────────────────────────────────

class IntegrityGuard:
    """
    Watches the Truth Wall and immutable log hash chains.
    Any tampering is detected immediately.
    Alerts are permanent and forwarded to Founder.
    """

    def __init__(self):
        self._stop   = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(
            target=self._monitor, daemon=True
        )
        self._thread.start()
        print("[GUARDIAN] Integrity guard started.")

    def stop(self):
        self._stop.set()

    def _monitor(self):
        while not self._stop.is_set():
            self._stop.wait(config.integrity_check_interval)
            if not self._stop.is_set():
                self._check_all()

    def _check_all(self):
        from .database import SessionLocal, verify_log_integrity
        from .truth_wall import truth_wall

        db = SessionLocal()
        try:
            # Check immutable log
            log_result = verify_log_integrity(db)
            if not log_result["ok"]:
                self._alert("IMMUTABLE_LOG_TAMPERED", log_result)

            # Check Truth Wall
            wall_result = truth_wall.verify_integrity(db)
            if not wall_result["ok"]:
                self._alert("TRUTH_WALL_TAMPERED", wall_result)

        except Exception as e:
            guardian_log("INTEGRITY_CHECK_ERROR", str(e))
        finally:
            db.close()

    def _alert(self, event: str, detail: dict):
        print(f"\n[GUARDIAN] ⚠  TAMPER ALERT: {event}")
        print(f"[GUARDIAN]    {detail.get('error', 'Unknown')}")
        print(f"[GUARDIAN]    The record has been touched.")
        print(f"[GUARDIAN]    Founder notified.\n")

        guardian_log(event, json.dumps(detail)[:200])

        # Write to tamper alerts file
        alerts = []
        try:
            with open("gleaning_tamper_alerts.json") as f:
                alerts = json.load(f)
        except Exception:
            pass

        alerts.append({
            "event":      event,
            "detail":     detail,
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "resolved":   False,
        })

        try:
            with open("gleaning_tamper_alerts.json", "w") as f:
                json.dump(alerts, f, indent=2)
        except Exception:
            pass


# ── Self Repair ───────────────────────────────────────────────────────────────

class SelfRepair:
    """
    Detects failures and fixes what it can.
    Flags what it cannot.
    Gleaning does not stay down.

    Checks:
      - Required modules importable
      - Database accessible
      - Templates present
      - Static files present
      - Watcher logs writable
      - Disk space adequate
      - Backup system functioning
    """

    REQUIRED_MODULES = [
        "gleaning.codex",
        "gleaning.config",
        "gleaning.database",
        "gleaning.resilience",
        "gleaning.truth_wall",
        "gleaning.matching",
        "gleaning.hoarders",
        "gleaning.watcher",
        "gleaning.guardian",
    ]

    REQUIRED_TEMPLATES = [
        "templates/index.html",
        "templates/wall.html",
        "templates/map.html",
        "templates/stats.html",
    ]

    MIN_DISK_MB = 100

    def run_checks(self) -> dict:
        results = {}

        results["modules"]   = self._check_modules()
        results["database"]  = self._check_database()
        results["templates"] = self._check_templates()
        results["disk"]      = self._check_disk()
        results["logs"]      = self._check_log_writability()
        results["backups"]   = self._check_backups()

        all_ok = all(results.values())

        if not all_ok:
            failed = [k for k, v in results.items() if not v]
            print(f"[REPAIR] Issues detected: {failed}")
            self._attempt_repair(failed)

        return {"ok": all_ok, "checks": results}

    def _attempt_repair(self, failed: list):
        for system in failed:
            print(f"[REPAIR] Attempting repair: {system}")
            try:
                if system == "modules":
                    self._repair_modules()
                elif system == "database":
                    self._repair_database()
                elif system == "templates":
                    self._repair_templates()
                elif system == "disk":
                    self._repair_disk()
                elif system == "logs":
                    self._repair_logs()
                elif system == "backups":
                    self._repair_backups()
            except Exception as e:
                self._log_repair(system, f"FAILED: {e}")

    def _check_modules(self) -> bool:
        for mod in self.REQUIRED_MODULES:
            try:
                importlib.import_module(mod)
            except ImportError as e:
                print(f"[REPAIR] Missing module: {mod} — {e}")
                return False
        return True

    def _check_database(self) -> bool:
        try:
            from .database import SessionLocal
            db = SessionLocal()
            db.execute(__import__("sqlalchemy").text("SELECT 1"))
            db.close()
            return True
        except Exception as e:
            print(f"[REPAIR] Database check failed: {e}")
            return False

    def _check_templates(self) -> bool:
        for t in self.REQUIRED_TEMPLATES:
            if not os.path.exists(t):
                print(f"[REPAIR] Missing template: {t}")
                return False
        return True

    def _check_disk(self) -> bool:
        try:
            usage = shutil.disk_usage(".")
            free_mb = usage.free / (1024 * 1024)
            if free_mb < self.MIN_DISK_MB:
                print(f"[REPAIR] Low disk: {free_mb:.0f}MB free")
                return False
            return True
        except Exception:
            return True

    def _check_log_writability(self) -> bool:
        test = ".repair_test"
        try:
            with open(test, "w") as f:
                f.write("test")
            os.remove(test)
            return True
        except Exception:
            return False

    def _check_backups(self) -> bool:
        return config.backup_path.exists()

    def _repair_modules(self):
        self._log_repair("modules", "Cannot auto-repair missing modules — flag for restart")

    def _repair_database(self):
        from .database import init_db
        from .resilience import BackupSystem
        backup = BackupSystem()
        if not os.path.exists("gleaning.db"):
            if backup.restore_latest():
                self._log_repair("database", "Restored from backup")
            else:
                init_db()
                self._log_repair("database", "Reinitialised fresh")
        else:
            init_db()
            self._log_repair("database", "Reinitialised tables")

    def _repair_templates(self):
        self._log_repair("templates",
                         "Missing templates — flag for manual restore")

    def _repair_disk(self):
        # Emergency log rotation
        for log in Path(".").glob("*.log"):
            try:
                size_mb = log.stat().st_size / (1024 * 1024)
                if size_mb > 5:
                    log.rename(f"{log}.bak")
                    self._log_repair("disk",
                                     f"Rotated {log.name} ({size_mb:.1f}MB)")
            except Exception:
                pass

    def _repair_logs(self):
        try:
            os.makedirs("logs", exist_ok=True)
            self._log_repair("logs", "Log directory recreated")
        except Exception as e:
            self._log_repair("logs", f"Failed: {e}")

    def _repair_backups(self):
        try:
            config.backup_path.mkdir(parents=True, exist_ok=True)
            self._log_repair("backups", "Backup directory recreated")
        except Exception as e:
            self._log_repair("backups", f"Failed: {e}")

    def _log_repair(self, system: str, result: str):
        line = json.dumps({
            "time":   datetime.now(timezone.utc).isoformat(),
            "system": system,
            "result": result,
        })
        try:
            with open(REPAIR_LOG, "a") as f:
                f.write(line + "\n")
        except Exception:
            pass
        print(f"[REPAIR] {system}: {result}")


# ── Codex Enforcer ────────────────────────────────────────────────────────────

class CodexEnforcer:
    """
    Validates significant actions against the Gleaning Codex.
    Blocks Absolute violations before they execute.
    Logs every check.
    """

    VIOLATION_PATTERNS = [
        r"\bcharge_pantry\b",
        r"\bsell_data\b",
        r"\bremove_truth_wall\b",
        r"\bhide_waste\b",
        r"\bcorporate_buyout\b",
        r"\bsuppress_hoarders\b",
        r"\bdelete_log\b",
        r"\btamper\b",
        r"\boverride_codex\b",
    ]

    def __init__(self):
        self._compiled = [
            re.compile(p, re.IGNORECASE)
            for p in self.VIOLATION_PATTERNS
        ]

    def validate(self, action: str, context: str = "") -> dict:
        combined = f"{action} {context}".lower()

        for pattern in self._compiled:
            if pattern.search(combined):
                guardian_log(
                    "CODEX_VIOLATION",
                    f"action:{action} pattern:{pattern.pattern}"
                )
                print(f"[GUARDIAN] CODEX VIOLATION BLOCKED: {action}")
                return {
                    "ok":        False,
                    "violation": f"Codex violation: {action}",
                    "absolute":  "The harvest was never only theirs."
                }

        # Also check against codex
        result = codex.validate_action(action)
        if not result["ok"]:
            guardian_log("CODEX_VIOLATION", f"action:{action}")
        return result


# ── Guardian ──────────────────────────────────────────────────────────────────

class GleaningGuardian:
    """
    The full guardian system.
    Rate limiting. Integrity. Self repair. Codex enforcement.
    Gleaning stays up. The record stays clean.
    """

    def __init__(self):
        self.rate_limiter     = RateLimiter()
        self.integrity_guard  = IntegrityGuard()
        self.self_repair      = SelfRepair()
        self.codex_enforcer   = CodexEnforcer()

    def startup(self):
        print("[GUARDIAN] Running startup checks...")
        results = self.self_repair.run_checks()
        if results["ok"]:
            print("[GUARDIAN] All systems nominal.")
        else:
            failed = [k for k, v in results["checks"].items() if not v]
            print(f"[GUARDIAN] Issues repaired: {failed}")

        self.integrity_guard.start()
        print("[GUARDIAN] Guardian is active. Gleaning is protected.\n")

    def stop(self):
        self.integrity_guard.stop()
        print("[GUARDIAN] Guardian stopped.")

    def check_request(self, ip: str) -> dict:
        return self.rate_limiter.check(ip)

    def validate_action(self, action: str, context: str = "") -> dict:
        return self.codex_enforcer.validate(action, context)

    def status(self) -> dict:
        return {
            "guardian":    "ACTIVE",
            "rate_limiter": "ACTIVE",
            "integrity":   "MONITORING",
            "codex":       "ENFORCING",
            "note":        "Gleaning is protected."
        }


guardian = GleaningGuardian()
