"""
barter.py — Gleaning Barter System

Commons members post what they have and what they want.
No money. No prohibited items. Gleaning is the facilitator only.
Team moderates all listings before they go live.
Auto-expires listings after 60 days of inactivity.
— Krone the Architect · 2026
"""

import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Optional

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
TEAM_EMAIL     = os.environ.get("TEAM_EMAIL", os.environ.get("FOUNDER_EMAIL", ""))
FROM_ADDRESS   = os.environ.get("FROM_ADDRESS", "Gleaning <noreply@gleaning.onrender.com>")
COMMONS_URL    = os.environ.get("COMMONS_URL", "https://the-commons.onrender.com")

PROHIBITED_KEYWORDS = [
    "alcohol","beer","wine","liquor","whiskey","vodka","weed","cannabis",
    "marijuana","cocaine","meth","heroin","drug","drugs","pill","pills",
    "gun","guns","rifle","pistol","ammo","ammunition","weapon","weapons",
    "knife","knives","bomb","explosive","nazi","kkk","confederate","hate",
    "sex","sexual","escort","adult","porn","tobacco","cigarette","vape",
]

CATEGORIES = [
    "Food & Produce",
    "Tools & Equipment",
    "Clothing & Accessories",
    "Books & Media",
    "Seeds & Plants",
    "Furniture & Home",
    "Baby & Kids",
    "Electronics",
    "Art & Crafts",
    "Skills & Labor",
    "Garden & Outdoor",
    "Other",
]

def check_prohibited(text: str) -> Optional[str]:
    """Returns the prohibited keyword found, or None if clean."""
    text_lower = text.lower()
    for kw in PROHIBITED_KEYWORDS:
        if kw in text_lower:
            return kw
    return None

def verify_commons_token(token: str) -> Optional[dict]:
    """Verify a Commons JWT token and return the payload."""
    try:
        from jose import jwt, JWTError
        secret = os.environ.get("SECRET_KEY", "")
        if not secret:
            return None
        return jwt.decode(token, secret, algorithms=["HS256"])
    except Exception:
        return None

def _send_email(to: str, subject: str, html: str) -> bool:
    if not RESEND_API_KEY or not to:
        return False
    payload = json.dumps({
        "from": FROM_ADDRESS,
        "to": [to],
        "subject": subject,
        "html": html,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 201)
    except Exception as e:
        print(f"[BARTER] Email failed: {e}")
        return False

def notify_team_new_listing(listing) -> bool:
    """Notify team of a new listing pending moderation."""
    subject = f"[Gleaning Barter] New listing — {listing.title}"
    html = f"""
    <div style="background:#0a0a0a;color:#e8e8e8;font-family:sans-serif;padding:32px;max-width:600px;margin:0 auto">
      <h2 style="color:#4a9e6b">🌾 Gleaning Barter — New Listing</h2>
      <p style="color:#999">A Commons member has posted a new barter listing pending your review.</p>
      <div style="background:#111;border:1px solid #1e1e1e;border-radius:8px;padding:20px;margin:20px 0">
        <p><strong>Title:</strong> {listing.title}</p>
        <p><strong>Offering:</strong> {listing.offering}</p>
        <p><strong>Seeking:</strong> {listing.seeking}</p>
        <p><strong>Category:</strong> {listing.category}</p>
        <p><strong>Location:</strong> {listing.city}, {listing.state}</p>
        <p><strong>Posted by:</strong> {listing.commons_username}</p>
      </div>
      <div style="display:flex;gap:12px;margin-top:20px">
        <a href="https://gleaning.onrender.com/barter/moderate/{listing.id}/approve"
           style="background:#4a9e6b;color:#000;padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:700">
           ✓ Approve
        </a>
        <a href="https://gleaning.onrender.com/barter/moderate/{listing.id}/reject"
           style="background:#c0392b;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:700">
           ✗ Reject
        </a>
      </div>
      <p style="color:#444;font-size:12px;margin-top:24px">
        Gleaning Barter · Team moderation · Escalate to Krone if unresolved
      </p>
    </div>
    """
    return _send_email(TEAM_EMAIL, subject, html)

def notify_team_flag(listing, reason: str) -> bool:
    """Notify team that a listing has been flagged."""
    subject = f"[Gleaning Barter] ⚠ Flagged listing — {listing.title}"
    html = f"""
    <div style="background:#0a0a0a;color:#e8e8e8;font-family:sans-serif;padding:32px;max-width:600px;margin:0 auto">
      <h2 style="color:#e74c3c">⚠ Gleaning Barter — Flagged Listing</h2>
      <div style="background:#111;border:1px solid #2a2a2a;border-radius:8px;padding:20px;margin:20px 0">
        <p><strong>Title:</strong> {listing.title}</p>
        <p><strong>Posted by:</strong> {listing.commons_username}</p>
        <p><strong>Flag reason:</strong> {reason}</p>
      </div>
      <a href="https://gleaning.onrender.com/barter/moderate/{listing.id}/remove"
         style="background:#c0392b;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:700">
         Remove Listing
      </a>
      <p style="color:#444;font-size:12px;margin-top:24px">Escalate to Krone if needed.</p>
    </div>
    """
    return _send_email(TEAM_EMAIL, subject, html)

def notify_poster_approved(username: str, title: str) -> bool:
    """Notify Commons user their listing is live."""
    # We notify via Commons — no email stored in Gleaning
    print(f"[BARTER] Listing approved: {title} by {username}")
    return True

def expire_old_listings(db) -> int:
    """Auto-expire listings with no activity for 60 days."""
    from sqlalchemy import text
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=60)
        result = db.execute(text("""
            UPDATE barter_listings
            SET status = 'expired'
            WHERE status = 'active'
            AND last_active < :cutoff
        """), {"cutoff": cutoff})
        db.commit()
        count = result.rowcount
        if count:
            print(f"[BARTER] Expired {count} inactive listings")
        return count
    except Exception as e:
        print(f"[BARTER] Expiry error: {e}")
        return 0
