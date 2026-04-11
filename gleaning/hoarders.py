"""
hoarders.py — Hoarders

They had enough to feed hundreds.
They chose the landfill.

This is the record.
Photo. Pin. Timestamp. Corporation named.
Families that could have been fed — calculated honestly.

Moderation: Circle and Consultants review first.
Unsure cases forward to the Founder.
No post goes live without a timestamp and location.
No post goes live that isn't food waste.

— Krone the Architect · 2026
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Session, relationship
from .database import Base, engine, log_event, hash_entry

# ── Constants ─────────────────────────────────────────────────────────────────

# USDA-based food consumption figures — family of 4, two adults two children
LBS_PER_DAY_FAMILY_4  = 5.5
LBS_PER_WEEK_FAMILY_4 = 38.0
LBS_PER_YEAR_FAMILY_4 = 2000.0

# Post status
STATUS_PENDING  = "PENDING"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"
STATUS_ESCALATED = "ESCALATED"  # forwarded to Founder

# ── Models ────────────────────────────────────────────────────────────────────

class HoarderPost(Base):
    """
    A documented instance of food waste.
    Photo. Pin. Timestamp. Corporation.
    The record of what they chose to do.
    """
    __tablename__ = "hoarder_posts"

    id              = Column(Integer, primary_key=True, index=True)

    # Who posted
    posted_by       = Column(String(300), default="Anonymous")
    contact         = Column(String(300), default="")  # optional

    # What they saw
    description     = Column(Text, nullable=False)
    corporation     = Column(String(300), default="Unknown")
    store_name      = Column(String(300), default="")
    estimated_lbs   = Column(Float, nullable=False)  # poster's estimate

    # Where and when — REQUIRED, blocked at form if missing
    latitude        = Column(Float, nullable=False)
    longitude       = Column(Float, nullable=False)
    location_label  = Column(String(300), default="")  # city/neighborhood
    photo_path      = Column(String(500), default="")

    # Timestamp — server side, cannot be faked
    posted_at       = Column(DateTime, nullable=False,
                             default=lambda: datetime.now(timezone.utc))

    # Moderation
    status          = Column(String(50), default=STATUS_PENDING)
    reviewed_by     = Column(String(300), default="")
    reviewed_at     = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, default="")
    moderator_notes = Column(Text, default="")
    escalated       = Column(Boolean, default=False)
    escalation_note = Column(Text, default="")

    # Verified weight — moderator can adjust estimate
    verified_lbs    = Column(Float, nullable=True)

    # Integrity
    integrity_hash  = Column(String(64), default="")


class ModerationAction(Base):
    """
    Every moderation action logged.
    Transparent. Accountable. Permanent.
    """
    __tablename__ = "moderation_actions"

    id          = Column(Integer, primary_key=True, index=True)
    post_id     = Column(Integer, ForeignKey("hoarder_posts.id"))
    moderator   = Column(String(300), nullable=False)
    action      = Column(String(50), nullable=False)  # APPROVE | REJECT | ESCALATE | ADJUST
    note        = Column(Text, default="")
    acted_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Calculations ──────────────────────────────────────────────────────────────

def calculate_families_fed(lbs: float) -> dict:
    """
    How many families of 4 could this have fed?
    Honest estimates. We round down. Never inflate.

    Based on USDA food consumption data:
    Family of 4 (2 adults, 2 children) needs approximately:
      5.5 lbs/day · 38 lbs/week · 2,000 lbs/year
    """
    if not lbs or lbs <= 0:
        return {"days": 0, "weeks": 0, "years": 0}

    return {
        "days":  int(lbs / LBS_PER_DAY_FAMILY_4),
        "weeks": int(lbs / LBS_PER_WEEK_FAMILY_4),
        "years": round(lbs / LBS_PER_YEAR_FAMILY_4, 2),
        "lbs":   lbs,
        "basis": (
            "Based on USDA food consumption data. "
            "Family of 4: two adults, two children. "
            f"{LBS_PER_DAY_FAMILY_4} lbs/day · "
            f"{LBS_PER_WEEK_FAMILY_4} lbs/week · "
            f"{LBS_PER_YEAR_FAMILY_4} lbs/year. "
            "We round down. We never inflate."
        )
    }


def calculate_total_waste(posts: list) -> dict:
    """
    Running total across all approved posts.
    The full account of what they chose to do.
    """
    total_lbs = sum(
        (p.verified_lbs or p.estimated_lbs)
        for p in posts
        if p.status == STATUS_APPROVED
    )
    families  = calculate_families_fed(total_lbs)
    return {
        "total_lbs":      total_lbs,
        "total_posts":    len([p for p in posts if p.status == STATUS_APPROVED]),
        "families_days":  families["days"],
        "families_weeks": families["weeks"],
        "families_years": families["years"],
        "note": (
            f"{total_lbs:,.0f} lbs of documented food waste. "
            f"Could have fed {families['weeks']:,} families of four "
            f"for one week. Every number here is documented. "
            f"Nothing is inflated."
        )
    }


# ── Hoarders System ───────────────────────────────────────────────────────────

class Hoarders:
    """
    The full Hoarders system.
    Submit. Moderate. Display. Calculate.
    """

    def submit(self, db: Session,
               description: str,
               estimated_lbs: float,
               latitude: float,
               longitude: float,
               location_label: str = "",
               corporation: str = "Unknown",
               store_name: str = "",
               photo_path: str = "",
               posted_by: str = "Anonymous",
               contact: str = "") -> dict:
        """
        Submit a food waste report.
        Timestamp is server-side — cannot be faked.
        Location is required — blocked at form if missing.
        """
        # Validate required fields
        if not description or not description.strip():
            return {"ok": False, "error": "Description is required."}
        if not estimated_lbs or estimated_lbs <= 0:
            return {"ok": False, "error": "Estimated weight is required."}
        if latitude is None or longitude is None:
            return {"ok": False,
                    "error": "Location is required. No location, no post."}

        data = {
            "description":  description,
            "corporation":  corporation,
            "estimated_lbs": estimated_lbs,
            "latitude":     latitude,
            "longitude":    longitude,
            "posted_at":    datetime.now(timezone.utc).isoformat(),
        }
        entry_hash = hash_entry(data)

        post = HoarderPost(
            posted_by      = posted_by,
            contact        = contact,
            description    = description,
            corporation    = corporation,
            store_name     = store_name,
            estimated_lbs  = estimated_lbs,
            latitude       = latitude,
            longitude      = longitude,
            location_label = location_label,
            photo_path     = photo_path,
            status         = STATUS_PENDING,
            integrity_hash = entry_hash,
        )
        db.add(post)
        db.commit()
        db.refresh(post)

        log_event(db, "HOARDERS_SUBMITTED", posted_by,
                  corporation,
                  f"{estimated_lbs}lbs @ {location_label}")

        print(f"[HOARDERS] Post submitted: {estimated_lbs}lbs "
              f"at {location_label} — pending review")

        return {
            "ok":      True,
            "post_id": post.id,
            "status":  STATUS_PENDING,
            "note":    "Your report is pending moderation. "
                       "Thank you for documenting this."
        }

    def moderate(self, db: Session,
                 post_id: int,
                 moderator: str,
                 action: str,
                 note: str = "",
                 verified_lbs: float = None) -> dict:
        """
        Moderator reviews a pending post.
        APPROVE | REJECT | ESCALATE to Founder
        """
        post = db.query(HoarderPost).filter(
            HoarderPost.id == post_id
        ).first()
        if not post:
            return {"ok": False, "error": "Post not found."}
        if post.status != STATUS_PENDING and action != "ESCALATE":
            return {"ok": False,
                    "error": f"Post is already {post.status}."}

        if action == "APPROVE":
            post.status      = STATUS_APPROVED
            post.reviewed_by = moderator
            post.reviewed_at = datetime.now(timezone.utc)
            post.moderator_notes = note
            if verified_lbs:
                post.verified_lbs = verified_lbs
            print(f"[HOARDERS] Post {post_id} approved by {moderator}")

        elif action == "REJECT":
            post.status           = STATUS_REJECTED
            post.reviewed_by      = moderator
            post.reviewed_at      = datetime.now(timezone.utc)
            post.rejection_reason = note
            print(f"[HOARDERS] Post {post_id} rejected by {moderator}")

        elif action == "ESCALATE":
            post.escalated       = True
            post.status          = STATUS_ESCALATED
            post.escalation_note = note
            print(f"[HOARDERS] Post {post_id} escalated to Founder")

        else:
            return {"ok": False, "error": "Action must be APPROVE, REJECT, or ESCALATE."}

        # Log the moderation action
        mod_action = ModerationAction(
            post_id   = post_id,
            moderator = moderator,
            action    = action,
            note      = note,
        )
        db.add(mod_action)
        db.commit()

        log_event(db, f"HOARDERS_{action}", moderator,
                  str(post_id), note[:80] if note else "")

        return {"ok": True, "post_id": post_id, "status": post.status}

    def get_approved(self, db: Session,
                     corporation: str = None,
                     limit: int = 50) -> list:
        """Get approved posts for public display."""
        query = db.query(HoarderPost).filter(
            HoarderPost.status == STATUS_APPROVED
        )
        if corporation:
            query = query.filter(
                HoarderPost.corporation.ilike(f"%{corporation}%")
            )
        posts = query.order_by(
            HoarderPost.posted_at.desc()
        ).limit(limit).all()

        return [self._format(post) for post in posts]

    def get_pending(self, db: Session) -> list:
        """Get posts awaiting moderation."""
        posts = db.query(HoarderPost).filter(
            HoarderPost.status.in_([STATUS_PENDING, STATUS_ESCALATED])
        ).order_by(HoarderPost.posted_at.asc()).all()
        return [self._format(post) for post in posts]

    def get_escalated(self, db: Session) -> list:
        """Get posts escalated to Founder."""
        posts = db.query(HoarderPost).filter(
            HoarderPost.escalated == True
        ).order_by(HoarderPost.posted_at.asc()).all()
        return [self._format(post) for post in posts]

    def get_totals(self, db: Session) -> dict:
        """Running totals — the full account."""
        posts = db.query(HoarderPost).all()
        return calculate_total_waste(posts)

    def get_by_corporation(self, db: Session,
                           corporation: str) -> dict:
        """All waste documented for one corporation."""
        posts = db.query(HoarderPost).filter(
            HoarderPost.corporation.ilike(f"%{corporation}%"),
            HoarderPost.status == STATUS_APPROVED
        ).all()
        total = calculate_total_waste(posts)
        return {
            "corporation": corporation,
            "posts":       [self._format(p) for p in posts],
            "totals":      total,
        }

    def _format(self, post: HoarderPost) -> dict:
        lbs = post.verified_lbs or post.estimated_lbs
        fed = calculate_families_fed(lbs)
        return {
            "id":              post.id,
            "description":     post.description,
            "corporation":     post.corporation,
            "store_name":      post.store_name,
            "location":        post.location_label,
            "latitude":        post.latitude,
            "longitude":       post.longitude,
            "photo":           post.photo_path,
            "posted_at":       post.posted_at.isoformat(),
            "posted_by":       post.posted_by,
            "estimated_lbs":   post.estimated_lbs,
            "verified_lbs":    post.verified_lbs,
            "display_lbs":     lbs,
            "families_days":   fed["days"],
            "families_weeks":  fed["weeks"],
            "families_years":  fed["years"],
            "status":          post.status,
            "escalated":       post.escalated,
        }


# ── Calculation methodology — public ─────────────────────────────────────────

METHODOLOGY = """
HOW WE CALCULATE FAMILIES FED

We use USDA food consumption data for a family of four
(two adults, two children):

  · 5.5 lbs per day
  · 38 lbs per week
  · 2,000 lbs per year

Every post includes a weight estimate from the person who
documented the waste. Moderators may adjust estimates up or
down based on the photo and description. We always note whether
a figure is estimated or verified.

We round down. We never inflate.
If anything, the real numbers are higher than what we show.

The corporations know exactly how much they throw away.
They choose not to tell you.
We do.

— Krone the Architect · Gleaning · 2026
"""


hoarders = Hoarders()
