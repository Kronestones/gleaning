"""
config.py — Gleaning Configuration

Reads environment. Validates settings. Reports status.
Secrets never live in source code.

— Krone the Architect · 2026
"""

import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:

    def __init__(self):

        # ── Core ──────────────────────────────────────────────────
        self.secret_key      = os.getenv("SECRET_KEY", secrets.token_hex(32))
        self.environment     = os.getenv("ENVIRONMENT", "development")
        self.debug           = os.getenv("DEBUG", "true").lower() == "true"
        self.host            = os.getenv("HOST", "0.0.0.0")
        self.port            = int(os.getenv("PORT", 8000))

        # ── Database ──────────────────────────────────────────────
        self.database_url    = os.getenv("DATABASE_URL", "sqlite:///./gleaning.db")

        # ── Storage ───────────────────────────────────────────────
        self.media_dir       = Path(os.getenv("MEDIA_DIR", "./media"))
        self.max_upload_mb   = int(os.getenv("MAX_UPLOAD_MB", 50))

        # ── Founder ───────────────────────────────────────────────
        self.founder_hash    = os.getenv("FOUNDER_HASH", "")
        self.founder_salt    = os.getenv("FOUNDER_SALT", "")

        # ── Security ──────────────────────────────────────────────
        self.jwt_algorithm   = "HS256"
        self.jwt_expire_hours = 24 * 7
        self.rate_limit_per_minute = int(os.getenv("RATE_LIMIT", 60))
        self.max_connections = int(os.getenv("MAX_CONNECTIONS", 200))

        # ── Integrity ─────────────────────────────────────────────
        self.integrity_check_interval = 3600  # hourly
        self.backup_path     = Path(os.getenv("BACKUP_PATH", "./backups"))
        self.immutable_log   = Path(os.getenv("IMMUTABLE_LOG", "./gleaning_immutable.log"))
        self.mirror_log      = Path(os.getenv("MIRROR_LOG", "./gleaning_mirror.log"))

        # ── Email ─────────────────────────────────────────────────
        self.resend_api_key  = os.getenv("RESEND_API_KEY", "")
        self.email_from      = os.getenv("EMAIL_FROM", "onboarding@resend.dev")
        self.base_url        = os.getenv("BASE_URL", "http://localhost:8000")

        # ── Ensure directories exist ──────────────────────────────
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.backup_path.mkdir(parents=True, exist_ok=True)

    def validate(self) -> list:
        problems = []
        if not self.founder_hash:
            problems.append("FOUNDER_HASH not set — founder authentication unavailable")
        if not self.founder_salt:
            problems.append("FOUNDER_SALT not set — founder authentication unavailable")
        if not self.resend_api_key:
            problems.append("RESEND_API_KEY not set — email unavailable")
        if self.environment == "production" and self.debug:
            problems.append("DEBUG is True in production — disable before deploy")
        if self.base_url == "http://localhost:8000" and self.environment == "production":
            problems.append("BASE_URL is localhost in production — set your actual URL")
        return problems

    def is_ready(self) -> bool:
        return len(self.validate()) == 0

    def print_status(self):
        print(f"\n[GLEANING] Configuration Status")
        print(f"  Environment : {self.environment}")
        print(f"  Host        : {self.host}:{self.port}")
        print(f"  Database    : {self.database_url}")
        print(f"  Founder     : {'SET ✓' if self.founder_hash else 'NOT SET ✗'}")
        print(f"  Email       : {'SET ✓' if self.resend_api_key else 'NOT SET ✗'}")
        problems = self.validate()
        if problems:
            print(f"  Warnings:")
            for p in problems:
                print(f"    · {p}")
        else:
            print(f"  Status      : READY")
        print()

config = Config()
