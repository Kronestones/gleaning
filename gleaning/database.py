"""
database.py — Gleaning Database

The record of everything.
Every surplus posting. Every match. Every pickup.
Every entry on the Truth Wall.
Every attempt to tamper with any of it.

Append-only where it matters.
Hash-chained where it must not be touched.

— Krone the Architect · 2026
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import (
    create_engine, Column, Integer, String,
    Float, DateTime, Text, Boolean, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from .config import config

# ── Engine ────────────────────────────────────────────────────────────────────

engine = create_engine(
    config.database_url,
    connect_args={"check_same_thread": False}
    if "sqlite" in config.database_url else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ── Models ────────────────────────────────────────────────────────────────────

class User(Base):
    """
    A registered participant — business, pantry, or individual.
    """
    __tablename__ = "users"

    id           = Column(Integer, primary_key=True, index=True)
    email        = Column(String(300), unique=True, index=True, nullable=False)
    name         = Column(String(300), nullable=False)
    org_type     = Column(String(50), nullable=False)  # BUSINESS | PANTRY | INDIVIDUAL
    address      = Column(Text, default="")
    city         = Column(String(100), default="")
    state        = Column(String(50), default="")
    zip_code     = Column(String(20), default="")
    latitude     = Column(Float, nullable=True)
    longitude    = Column(Float, nullable=True)
    verified     = Column(Boolean, default=False)
    active       = Column(Boolean, default=True)
    joined_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen    = Column(DateTime, nullable=True)
    note         = Column(Text, default="")

    surplus_posts = relationship("SurplusPost", back_populates="donor")
    needs         = relationship("PantryNeed", back_populates="pantry")
    matches_given = relationship("Match", foreign_keys="Match.donor_id",
                                 back_populates="donor")
    matches_received = relationship("Match", foreign_keys="Match.pantry_id",
                                    back_populates="pantry")


class SurplusPost(Base):
    """
    A business posting surplus food available for gleaning.
    """
    __tablename__ = "surplus_posts"

    id            = Column(Integer, primary_key=True, index=True)
    donor_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    title         = Column(String(300), nullable=False)
    description   = Column(Text, default="")
    quantity      = Column(String(200), nullable=False)
    category      = Column(String(100), default="")  # produce, dairy, bakery, etc
    available_from = Column(DateTime, nullable=False)
    available_until = Column(DateTime, nullable=False)
    pickup_address = Column(Text, default="")
    latitude      = Column(Float, nullable=True)
    longitude     = Column(Float, nullable=True)
    status        = Column(String(50), default="AVAILABLE")  # AVAILABLE | MATCHED | COLLECTED | EXPIRED
    posted_at     = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime, nullable=True)
    notes         = Column(Text, default="")

    donor   = relationship("User", back_populates="surplus_posts")
    matches = relationship("Match", back_populates="surplus_post")


class PantryNeed(Base):
    """
    A pantry posting what they currently need.
    """
    __tablename__ = "pantry_needs"

    id          = Column(Integer, primary_key=True, index=True)
    pantry_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    category    = Column(String(100), nullable=False)
    description = Column(Text, default="")
    urgency     = Column(String(50), default="NORMAL")  # NORMAL | URGENT | CRITICAL
    posted_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    active      = Column(Boolean, default=True)

    pantry  = relationship("User", back_populates="needs")
    matches = relationship("Match", back_populates="pantry_need")


class Match(Base):
    """
    A connection made between surplus and need.
    Every match is permanent record. Nothing is deleted.
    """
    __tablename__ = "matches"

    id             = Column(Integer, primary_key=True, index=True)
    donor_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    pantry_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    surplus_post_id = Column(Integer, ForeignKey("surplus_posts.id"), nullable=False)
    pantry_need_id  = Column(Integer, ForeignKey("pantry_needs.id"), nullable=True)
    status         = Column(String(50), default="PENDING")  # PENDING | CONFIRMED | COLLECTED | CANCELLED
    matched_at     = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    confirmed_at   = Column(DateTime, nullable=True)
    collected_at   = Column(DateTime, nullable=True)
    notes          = Column(Text, default="")
    integrity_hash = Column(String(64), default="")  # tamper detection

    donor       = relationship("User", foreign_keys=[donor_id],
                               back_populates="matches_given")
    pantry      = relationship("User", foreign_keys=[pantry_id],
                               back_populates="matches_received")
    surplus_post = relationship("SurplusPost", back_populates="matches")
    pantry_need  = relationship("PantryNeed", back_populates="matches")


class TruthWallEntry(Base):
    """
    The Truth Wall — corporate ownership records.
    Immutable. Append only. Hash chained.
    No corporation may buy their way off this wall.
    """
    __tablename__ = "truth_wall"

    id              = Column(Integer, primary_key=True, index=True)
    corporation     = Column(String(300), nullable=False, index=True)
    brand           = Column(String(300), nullable=False)
    category        = Column(String(100), default="")
    owned_since     = Column(String(100), default="")
    source          = Column(Text, default="")
    added_at        = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    added_by        = Column(String(100), default="Krone the Architect")
    integrity_hash  = Column(String(64), default="")
    prev_hash       = Column(String(64), default="")
    verified        = Column(Boolean, default=True)
    note            = Column(Text, default="")


class MagicToken(Base):
    """Magic link authentication tokens."""
    __tablename__ = "magic_tokens"

    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String(300), nullable=False, index=True)
    token      = Column(String(200), nullable=False, unique=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    used       = Column(Boolean, default=False)


class ImmutableLog(Base):
    """
    Every significant action logged permanently.
    Hash chained. Tamper evident.
    """
    __tablename__ = "immutable_log"

    id         = Column(Integer, primary_key=True, index=True)
    event      = Column(String(100), nullable=False)
    actor      = Column(String(300), default="")
    target     = Column(String(300), default="")
    detail     = Column(Text, default="")
    logged_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    entry_hash = Column(String(64), default="")
    prev_hash  = Column(String(64), default="")


# ── Database helpers ──────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    print("[GLEANING] Database initialized.")


def hash_entry(data: dict, prev_hash: str = "0" * 64) -> str:
    """Generate a chained hash for tamper detection."""
    combined = prev_hash + json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(combined.encode()).hexdigest()


def log_event(db, event: str, actor: str = "",
              target: str = "", detail: str = ""):
    """
    Write to the immutable log.
    Every entry chained to the previous.
    """
    from sqlalchemy import desc
    last = db.query(ImmutableLog).order_by(
        desc(ImmutableLog.id)
    ).first()
    prev_hash = last.entry_hash if last else "0" * 64

    entry_data = {
        "event":  event,
        "actor":  actor,
        "target": target,
        "detail": detail,
        "time":   datetime.now(timezone.utc).isoformat()
    }
    entry_hash = hash_entry(entry_data, prev_hash)

    log = ImmutableLog(
        event      = event,
        actor      = actor,
        target     = target,
        detail     = detail,
        entry_hash = entry_hash,
        prev_hash  = prev_hash,
    )
    db.add(log)
    db.commit()
    return entry_hash


def verify_log_integrity(db) -> dict:
    """
    Verify the immutable log has not been tampered with.
    Recomputes hash chain and compares.
    """
    from sqlalchemy import asc
    entries = db.query(ImmutableLog).order_by(asc(ImmutableLog.id)).all()
    if not entries:
        return {"ok": True, "records": 0, "note": "No records yet."}

    prev_hash = "0" * 64
    for i, entry in enumerate(entries):
        data = {
            "event":  entry.event,
            "actor":  entry.actor,
            "target": entry.target,
            "detail": entry.detail,
            "time":   entry.logged_at.isoformat()
        }
        computed = hash_entry(data, prev_hash)
        if computed != entry.entry_hash:
            return {
                "ok":    False,
                "error": f"Tamper detected at record {i+1}",
                "id":    entry.id
            }
        prev_hash = entry.entry_hash

    return {"ok": True, "records": len(entries), "chain": "intact"}


class CorporateWasteRecord(Base):
    """
    Corporate food waste — documented from public record.
    WasteWatch writes here. Wealth Hoarders reads from here.
    One row per corporation. Overwritten when new data arrives.
    No history. No accumulation. Just the current truth.
    The people see what is being wasted right now.
    """
    __tablename__ = "corporate_waste"

    id            = Column(Integer, primary_key=True, index=True)
    corporation   = Column(String(300), nullable=False, unique=True, index=True)
    lbs_wasted    = Column(Float, nullable=False)
    period        = Column(String(100), default="")
    source_url    = Column(Text, default="")
    source_name   = Column(String(300), default="")
    recorded_by   = Column(String(100), default="WasteWatch")
    recorded_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    verified      = Column(Boolean, default=True)
    note          = Column(Text, default="")


class Resource(Base):
    __tablename__ = "resources"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(256), nullable=False)
    category    = Column(String(64), nullable=False)
    address     = Column(String(256), nullable=True)
    city        = Column(String(128), nullable=True)
    state       = Column(String(8), nullable=True)
    zip_code    = Column(String(16), nullable=True)
    lat         = Column(Float, nullable=True)
    lng         = Column(Float, nullable=True)
    phone       = Column(String(32), nullable=True)
    website     = Column(Text, nullable=True)
    services    = Column(Text, nullable=True)
    hours       = Column(String(256), nullable=True)
    is_popup    = Column(Boolean, default=False)
    verified    = Column(Boolean, default=True)
    source      = Column(String(256), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)


class ScanReport(Base):
    """
    Scanner email reports flagged by the Team for follow-up.
    Cleared reports are never stored. Only flags persist.
    — Krone the Architect · 2026
    """
    __tablename__ = "scan_reports"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    scanned_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    flagged_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    summary     = Column(Text, default="")
    new_count   = Column(Integer, default=0)
    errors      = Column(Text, default="")
    resolved    = Column(Boolean, default=False)
    note        = Column(Text, default="")


class Pawn(Base):
    """
    Elected officials — federal and state.
    Named, documented, and held to account.
    All data from public record — FEC, OpenSecrets, STOCK Act, congress.gov.
    — Krone the Architect · 2026
    """
    __tablename__ = "pawns"
    __table_args__ = {"extend_existing": True}

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    name                = Column(String(256), nullable=False)
    party               = Column(String(64), default="")
    state               = Column(String(64), nullable=False)
    state_code          = Column(String(4), default="")
    chamber             = Column(String(64), default="")        # House, Senate, State House, State Senate
    district            = Column(String(64), default="")
    in_office_since     = Column(String(32), default="")
    salary              = Column(String(64), default="")
    net_worth_entry     = Column(String(64), default="")        # net worth when first elected
    net_worth_current   = Column(String(64), default="")        # current net worth
    net_worth_note      = Column(Text, default="")              # the math that doesn't add up
    top_donors          = Column(Text, default="")              # JSON string
    total_contributions = Column(String(64), default="")
    aipac_connected     = Column(Boolean, default=False)
    aipac_amount        = Column(String(64), default="")
    aipac_note          = Column(Text, default="")
    stock_trades        = Column(Text, default="")              # JSON string
    committees          = Column(Text, default="")
    key_votes           = Column(Text, default="")              # JSON string
    corp_connections    = Column(Text, default="")              # connections to Wealth Hoarders
    puppet_connections  = Column(Text, default="")              # connections to Puppet Masters
    violations          = Column(Text, default="")
    source              = Column(Text, default="")
    verified            = Column(Boolean, default=True)
    last_updated        = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Pawn(Base):
    """
    Elected officials — federal and state.
    Named, documented, and held to account.
    All data from public record — FEC, OpenSecrets, STOCK Act, congress.gov.
    — Krone the Architect · 2026
    """
    __tablename__ = "pawns"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    name                = Column(String(256), nullable=False)
    party               = Column(String(64), default="")
    state               = Column(String(64), nullable=False)
    state_code          = Column(String(4), default="")
    chamber             = Column(String(64), default="")        # House, Senate, State House, State Senate
    district            = Column(String(64), default="")
    in_office_since     = Column(String(32), default="")
    salary              = Column(String(64), default="")
    net_worth_entry     = Column(String(64), default="")        # net worth when first elected
    net_worth_current   = Column(String(64), default="")        # current net worth
    net_worth_note      = Column(Text, default="")              # the math that doesn't add up
    top_donors          = Column(Text, default="")              # JSON string
    total_contributions = Column(String(64), default="")
    aipac_connected     = Column(Boolean, default=False)
    aipac_amount        = Column(String(64), default="")
    aipac_note          = Column(Text, default="")
    stock_trades        = Column(Text, default="")              # JSON string
    committees          = Column(Text, default="")
    key_votes           = Column(Text, default="")              # JSON string
    corp_connections    = Column(Text, default="")              # connections to Wealth Hoarders
    puppet_connections  = Column(Text, default="")              # connections to Puppet Masters
    violations          = Column(Text, default="")
    source              = Column(Text, default="")
    verified            = Column(Boolean, default=True)
    last_updated        = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Pawn(Base):
    """
    Elected officials — federal and state.
    Named, documented, and held to account.
    All data from public record — FEC, OpenSecrets, STOCK Act, congress.gov.
    — Krone the Architect · 2026
    """
    __tablename__ = "pawns"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    name                = Column(String(256), nullable=False)
    party               = Column(String(64), default="")
    state               = Column(String(64), nullable=False)
    state_code          = Column(String(4), default="")
    chamber             = Column(String(64), default="")        # House, Senate, State House, State Senate
    district            = Column(String(64), default="")
    in_office_since     = Column(String(32), default="")
    salary              = Column(String(64), default="")
    net_worth_entry     = Column(String(64), default="")        # net worth when first elected
    net_worth_current   = Column(String(64), default="")        # current net worth
    net_worth_note      = Column(Text, default="")              # the math that doesn't add up
    top_donors          = Column(Text, default="")              # JSON string
    total_contributions = Column(String(64), default="")
    aipac_connected     = Column(Boolean, default=False)
    aipac_amount        = Column(String(64), default="")
    aipac_note          = Column(Text, default="")
    stock_trades        = Column(Text, default="")              # JSON string
    committees          = Column(Text, default="")
    key_votes           = Column(Text, default="")              # JSON string
    corp_connections    = Column(Text, default="")              # connections to Wealth Hoarders
    puppet_connections  = Column(Text, default="")              # connections to Puppet Masters
    violations          = Column(Text, default="")
    source              = Column(Text, default="")
    verified            = Column(Boolean, default=True)
    last_updated        = Column(DateTime, default=lambda: datetime.now(timezone.utc))
