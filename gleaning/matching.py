"""
matching.py — The Gleaning Match Engine

Surplus posted. Need posted.
Match made. Pickup arranged.

No middleman. No fee. No delay.
The food moves from where it would be wasted
to where it is needed.

That is all this does.
That is enough.

— Krone the Architect · 2026
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from .database import (
    SurplusPost, PantryNeed, Match, User,
    log_event, hash_entry
)


class MatchEngine:
    """
    Connects surplus to need.
    Every match is logged. Every pickup recorded.
    Nothing is hidden. Nothing is deleted.
    """

    def post_surplus(self, db: Session, donor_id: int,
                     title: str, description: str,
                     quantity: str, category: str,
                     available_from: datetime,
                     available_until: datetime,
                     pickup_address: str,
                     latitude: float = None,
                     longitude: float = None,
                     notes: str = "") -> dict:
        """
        A business posts surplus food available for gleaning.
        """
        donor = db.query(User).filter(User.id == donor_id).first()
        if not donor:
            return {"ok": False, "error": "Donor not found."}

        post = SurplusPost(
            donor_id        = donor_id,
            title           = title,
            description     = description,
            quantity        = quantity,
            category        = category,
            available_from  = available_from,
            available_until = available_until,
            pickup_address  = pickup_address,
            latitude        = latitude,
            longitude       = longitude,
            notes           = notes,
            status          = "AVAILABLE",
        )
        db.add(post)
        db.commit()
        db.refresh(post)

        log_event(db, "SURPLUS_POSTED", donor.name,
                  title, f"{quantity} — {category}")

        print(f"[MATCH] Surplus posted: {title} by {donor.name}")

        # Auto-match if pantry needs exist
        matches = self._auto_match(db, post)

        return {
            "ok":      True,
            "post_id": post.id,
            "matches": len(matches),
            "note":    f"{len(matches)} pantry match(es) found." if matches
                       else "Posted. Waiting for a pantry match."
        }

    def post_need(self, db: Session, pantry_id: int,
                  category: str, description: str,
                  urgency: str = "NORMAL") -> dict:
        """
        A pantry posts what they need.
        """
        pantry = db.query(User).filter(User.id == pantry_id).first()
        if not pantry:
            return {"ok": False, "error": "Pantry not found."}
        if pantry.org_type != "PANTRY":
            return {"ok": False, "error": "Only pantries can post needs."}

        need = PantryNeed(
            pantry_id   = pantry_id,
            category    = category,
            description = description,
            urgency     = urgency,
            active      = True,
        )
        db.add(need)
        db.commit()
        db.refresh(need)

        log_event(db, "NEED_POSTED", pantry.name,
                  category, urgency)

        return {"ok": True, "need_id": need.id}

    def _auto_match(self, db: Session,
                    post: SurplusPost) -> list:
        """
        When surplus is posted — find matching pantry needs.
        Match on category. Prioritize urgent needs.
        """
        needs = db.query(PantryNeed).filter(
            and_(
                PantryNeed.active == True,
                or_(
                    PantryNeed.category.ilike(f"%{post.category}%"),
                    PantryNeed.category.ilike("%any%"),
                    PantryNeed.category.ilike("%all%"),
                )
            )
        ).order_by(
            PantryNeed.urgency.desc(),
            PantryNeed.posted_at.asc()
        ).all()

        matches_made = []
        for need in needs[:3]:  # cap at 3 auto-matches per post
            match = self._create_match(db, post, need)
            if match:
                matches_made.append(match)

        return matches_made

    def _create_match(self, db: Session,
                      post: SurplusPost,
                      need: PantryNeed) -> dict:
        """Create a match between surplus and need."""
        # Check not already matched
        existing = db.query(Match).filter(
            and_(
                Match.surplus_post_id == post.id,
                Match.pantry_id == need.pantry_id,
                Match.status.in_(["PENDING", "CONFIRMED"])
            )
        ).first()
        if existing:
            return None

        match_data = {
            "donor_id":        post.donor_id,
            "pantry_id":       need.pantry_id,
            "surplus_post_id": post.id,
            "pantry_need_id":  need.id,
            "matched_at":      datetime.now(timezone.utc).isoformat(),
        }
        match_hash = hash_entry(match_data)

        match = Match(
            donor_id        = post.donor_id,
            pantry_id       = need.pantry_id,
            surplus_post_id = post.id,
            pantry_need_id  = need.id,
            status          = "PENDING",
            integrity_hash  = match_hash,
        )
        db.add(match)
        db.commit()
        db.refresh(match)

        donor  = db.query(User).filter(User.id == post.donor_id).first()
        pantry = db.query(User).filter(User.id == need.pantry_id).first()

        log_event(db, "MATCH_CREATED",
                  donor.name if donor else str(post.donor_id),
                  pantry.name if pantry else str(need.pantry_id),
                  f"Post: {post.title}")

        print(f"[MATCH] Match created: {post.title} → "
              f"{pantry.name if pantry else 'pantry'}")

        return {"match_id": match.id, "status": "PENDING"}

    def confirm_match(self, db: Session,
                      match_id: int, pantry_id: int) -> dict:
        """Pantry confirms they will collect the surplus."""
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match:
            return {"ok": False, "error": "Match not found."}
        if match.pantry_id != pantry_id:
            return {"ok": False, "error": "Not your match."}
        if match.status != "PENDING":
            return {"ok": False, "error": f"Match is {match.status}."}

        match.status       = "CONFIRMED"
        match.confirmed_at = datetime.now(timezone.utc)

        # Mark surplus post as matched
        post = db.query(SurplusPost).filter(
            SurplusPost.id == match.surplus_post_id
        ).first()
        if post:
            post.status = "MATCHED"

        db.commit()

        pantry = db.query(User).filter(User.id == pantry_id).first()
        log_event(db, "MATCH_CONFIRMED",
                  pantry.name if pantry else str(pantry_id),
                  str(match_id), "Pickup confirmed")

        return {"ok": True, "match_id": match_id, "status": "CONFIRMED"}

    def record_collection(self, db: Session,
                          match_id: int, pantry_id: int) -> dict:
        """Record that food was actually collected."""
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match:
            return {"ok": False, "error": "Match not found."}
        if match.pantry_id != pantry_id:
            return {"ok": False, "error": "Not your match."}

        match.status       = "COLLECTED"
        match.collected_at = datetime.now(timezone.utc)

        post = db.query(SurplusPost).filter(
            SurplusPost.id == match.surplus_post_id
        ).first()
        if post:
            post.status = "COLLECTED"

        need = db.query(PantryNeed).filter(
            PantryNeed.id == match.pantry_need_id
        ).first()
        if need:
            need.active = False

        db.commit()

        pantry = db.query(User).filter(User.id == pantry_id).first()
        log_event(db, "FOOD_COLLECTED",
                  pantry.name if pantry else str(pantry_id),
                  str(match_id),
                  f"Post {match.surplus_post_id} collected")

        print(f"[MATCH] ✓ Food collected — match {match_id}")
        return {"ok": True, "match_id": match_id, "status": "COLLECTED"}

    def get_available_surplus(self, db: Session,
                               city: str = None,
                               category: str = None) -> list:
        """Get all available surplus posts."""
        now = datetime.now(timezone.utc)
        query = db.query(SurplusPost).filter(
            and_(
                SurplusPost.status == "AVAILABLE",
                SurplusPost.available_until >= now,
            )
        )
        if category:
            query = query.filter(
                SurplusPost.category.ilike(f"%{category}%")
            )
        posts = query.order_by(
            SurplusPost.available_until.asc()
        ).all()

        return [self._format_post(db, p) for p in posts]

    def get_pantry_matches(self, db: Session,
                           pantry_id: int) -> list:
        """Get all matches for a pantry."""
        matches = db.query(Match).filter(
            Match.pantry_id == pantry_id
        ).order_by(Match.matched_at.desc()).all()
        return [self._format_match(db, m) for m in matches]

    def get_donor_posts(self, db: Session,
                        donor_id: int) -> list:
        """Get all surplus posts by a donor."""
        posts = db.query(SurplusPost).filter(
            SurplusPost.donor_id == donor_id
        ).order_by(SurplusPost.posted_at.desc()).all()
        return [self._format_post(db, p) for p in posts]

    def get_stats(self, db: Session) -> dict:
        """Platform-wide gleaning statistics."""
        total_posts     = db.query(SurplusPost).count()
        collected       = db.query(SurplusPost).filter(
            SurplusPost.status == "COLLECTED"
        ).count()
        total_matches   = db.query(Match).count()
        confirmed       = db.query(Match).filter(
            Match.status.in_(["CONFIRMED", "COLLECTED"])
        ).count()
        active_pantries = db.query(User).filter(
            and_(User.org_type == "PANTRY", User.active == True)
        ).count()
        active_donors   = db.query(User).filter(
            and_(User.org_type == "BUSINESS", User.active == True)
        ).count()

        return {
            "surplus_posts":    total_posts,
            "food_collected":   collected,
            "matches_made":     total_matches,
            "matches_confirmed": confirmed,
            "active_pantries":  active_pantries,
            "active_donors":    active_donors,
            "note": "Every number here is food that didn't go to a landfill."
        }

    def _format_post(self, db: Session,
                     post: SurplusPost) -> dict:
        donor = db.query(User).filter(
            User.id == post.donor_id
        ).first()
        return {
            "id":              post.id,
            "title":           post.title,
            "description":     post.description,
            "quantity":        post.quantity,
            "category":        post.category,
            "donor":           donor.name if donor else "Unknown",
            "city":            donor.city if donor else "",
            "pickup_address":  post.pickup_address,
            "available_until": post.available_until.isoformat(),
            "status":          post.status,
            "posted_at":       post.posted_at.isoformat(),
        }

    def _format_match(self, db: Session, match: Match) -> dict:
        post  = db.query(SurplusPost).filter(
            SurplusPost.id == match.surplus_post_id
        ).first()
        donor = db.query(User).filter(
            User.id == match.donor_id
        ).first()
        return {
            "match_id":      match.id,
            "status":        match.status,
            "food":          post.title if post else "Unknown",
            "quantity":      post.quantity if post else "",
            "from":          donor.name if donor else "Unknown",
            "pickup":        post.pickup_address if post else "",
            "matched_at":    match.matched_at.isoformat(),
            "confirmed_at":  match.confirmed_at.isoformat()
                             if match.confirmed_at else None,
            "collected_at":  match.collected_at.isoformat()
                             if match.collected_at else None,
        }


match_engine = MatchEngine()
