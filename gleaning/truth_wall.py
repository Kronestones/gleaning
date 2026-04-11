"""
truth_wall.py — The Truth Wall

You think you're choosing between forty brands.
You're choosing between three owners.

This wall names them.
It does not come down.
No corporation may buy their way off it.
No legal threat changes what is true.

The data here is public record.
Corporate ownership is not a secret —
it is just inconvenient for them that we say it clearly.

— Krone the Architect · 2026
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .database import TruthWallEntry, hash_entry, log_event

# ── Seed data — the big three and their brands ────────────────────────────────
# This is public record. All of it verifiable.
# Sources: SEC filings, corporate annual reports, public databases.

SEED_DATA = [

    # ── Kraft Heinz ───────────────────────────────────────────────────────────
    ("Kraft Heinz", "Kraft", "Condiments & Dairy", "1903", "kraftheinzcompany.com"),
    ("Kraft Heinz", "Heinz", "Condiments", "1869", "kraftheinzcompany.com"),
    ("Kraft Heinz", "Oscar Mayer", "Meat", "1883", "kraftheinzcompany.com"),
    ("Kraft Heinz", "Philadelphia Cream Cheese", "Dairy", "1872", "kraftheinzcompany.com"),
    ("Kraft Heinz", "Velveeta", "Processed Cheese", "1918", "kraftheinzcompany.com"),
    ("Kraft Heinz", "Jell-O", "Dessert", "1897", "kraftheinzcompany.com"),
    ("Kraft Heinz", "Kool-Aid", "Beverages", "1927", "kraftheinzcompany.com"),
    ("Kraft Heinz", "Maxwell House", "Coffee", "1892", "kraftheinzcompany.com"),
    ("Kraft Heinz", "Capri Sun", "Beverages", "1969", "kraftheinzcompany.com"),
    ("Kraft Heinz", "Lunchables", "Snacks", "1988", "kraftheinzcompany.com"),
    ("Kraft Heinz", "Planters", "Nuts & Snacks", "1906", "kraftheinzcompany.com"),
    ("Kraft Heinz", "Grey Poupon", "Condiments", "1777", "kraftheinzcompany.com"),
    ("Kraft Heinz", "A.1. Sauce", "Condiments", "1824", "kraftheinzcompany.com"),
    ("Kraft Heinz", "Bagel Bites", "Frozen Snacks", "1985", "kraftheinzcompany.com"),
    ("Kraft Heinz", "Ore-Ida", "Frozen Potatoes", "1951", "kraftheinzcompany.com"),

    # ── Nestlé ────────────────────────────────────────────────────────────────
    ("Nestlé", "KitKat", "Candy", "1935", "nestle.com"),
    ("Nestlé", "Nescafé", "Coffee", "1938", "nestle.com"),
    ("Nestlé", "Toll House", "Baking", "1939", "nestle.com"),
    ("Nestlé", "Stouffer's", "Frozen Meals", "1922", "nestle.com"),
    ("Nestlé", "Lean Cuisine", "Frozen Meals", "1981", "nestle.com"),
    ("Nestlé", "Hot Pockets", "Frozen Snacks", "1983", "nestle.com"),
    ("Nestlé", "DiGiorno", "Frozen Pizza", "1995", "nestle.com"),
    ("Nestlé", "Dreyer's", "Ice Cream", "1928", "nestle.com"),
    ("Nestlé", "Häagen-Dazs", "Ice Cream", "1961", "nestle.com"),
    ("Nestlé", "Coffee-Mate", "Creamers", "1961", "nestle.com"),
    ("Nestlé", "Carnation", "Dairy", "1899", "nestle.com"),
    ("Nestlé", "Gerber", "Baby Food", "1927", "nestle.com"),
    ("Nestlé", "Pure Life", "Water", "1998", "nestle.com"),
    ("Nestlé", "Perrier", "Water", "1903", "nestle.com"),
    ("Nestlé", "Poland Spring", "Water", "1845", "nestle.com"),
    ("Nestlé", "Butterfinger", "Candy", "1923", "nestle.com"),
    ("Nestlé", "Baby Ruth", "Candy", "1921", "nestle.com"),
    ("Nestlé", "Crunch", "Candy", "1938", "nestle.com"),
    ("Nestlé", "Wonka", "Candy", "1971", "nestle.com"),

    # ── Unilever ──────────────────────────────────────────────────────────────
    ("Unilever", "Hellmann's", "Condiments", "1913", "unilever.com"),
    ("Unilever", "Ben & Jerry's", "Ice Cream", "1978", "unilever.com"),
    ("Unilever", "Breyers", "Ice Cream", "1866", "unilever.com"),
    ("Unilever", "Good Humor", "Ice Cream", "1920", "unilever.com"),
    ("Unilever", "Klondike", "Ice Cream", "1922", "unilever.com"),
    ("Unilever", "Popsicle", "Frozen Treats", "1923", "unilever.com"),
    ("Unilever", "Knorr", "Soups & Sauces", "1838", "unilever.com"),
    ("Unilever", "Lipton", "Tea", "1890", "unilever.com"),
    ("Unilever", "Bertolli", "Olive Oil & Pasta", "1865", "unilever.com"),
    ("Unilever", "Country Crock", "Spreads", "1981", "unilever.com"),
    ("Unilever", "I Can't Believe It's Not Butter", "Spreads", "1981", "unilever.com"),
    ("Unilever", "Talenti", "Gelato", "2003", "unilever.com"),

    # ── General Mills ─────────────────────────────────────────────────────────
    ("General Mills", "Cheerios", "Cereal", "1941", "generalmills.com"),
    ("General Mills", "Wheaties", "Cereal", "1922", "generalmills.com"),
    ("General Mills", "Lucky Charms", "Cereal", "1964", "generalmills.com"),
    ("General Mills", "Cocoa Puffs", "Cereal", "1958", "generalmills.com"),
    ("General Mills", "Trix", "Cereal", "1954", "generalmills.com"),
    ("General Mills", "Betty Crocker", "Baking", "1921", "generalmills.com"),
    ("General Mills", "Pillsbury", "Baking", "1869", "generalmills.com"),
    ("General Mills", "Häagen-Dazs (US)", "Ice Cream", "1961", "generalmills.com"),
    ("General Mills", "Yoplait", "Yogurt", "1965", "generalmills.com"),
    ("General Mills", "Nature Valley", "Snack Bars", "1975", "generalmills.com"),
    ("General Mills", "Progresso", "Soup", "1925", "generalmills.com"),
    ("General Mills", "Old El Paso", "Mexican Food", "1917", "generalmills.com"),
    ("General Mills", "Annie's", "Organic", "1989", "generalmills.com"),
    ("General Mills", "Larabar", "Snack Bars", "2000", "generalmills.com"),

    # ── Kellogg's (now Kellanova) ──────────────────────────────────────────────
    ("Kellanova", "Frosted Flakes", "Cereal", "1952", "kellanova.com"),
    ("Kellanova", "Corn Flakes", "Cereal", "1894", "kellanova.com"),
    ("Kellanova", "Froot Loops", "Cereal", "1963", "kellanova.com"),
    ("Kellanova", "Rice Krispies", "Cereal", "1927", "kellanova.com"),
    ("Kellanova", "Pop-Tarts", "Pastry", "1964", "kellanova.com"),
    ("Kellanova", "Eggo", "Frozen Waffles", "1953", "kellanova.com"),
    ("Kellanova", "Pringles", "Chips", "1968", "kellanova.com"),
    ("Kellanova", "Cheez-It", "Crackers", "1921", "kellanova.com"),
    ("Kellanova", "Special K", "Cereal", "1955", "kellanova.com"),
    ("Kellanova", "Nutri-Grain", "Snack Bars", "1975", "kellanova.com"),
    ("Kellanova", "MorningStar Farms", "Plant-Based", "1975", "kellanova.com"),

    # ── PepsiCo / Frito-Lay ───────────────────────────────────────────────────
    ("PepsiCo", "Lay's", "Chips", "1932", "pepsico.com"),
    ("PepsiCo", "Doritos", "Chips", "1964", "pepsico.com"),
    ("PepsiCo", "Cheetos", "Snacks", "1948", "pepsico.com"),
    ("PepsiCo", "Fritos", "Chips", "1932", "pepsico.com"),
    ("PepsiCo", "Tostitos", "Chips", "1979", "pepsico.com"),
    ("PepsiCo", "Ruffles", "Chips", "1958", "pepsico.com"),
    ("PepsiCo", "Quaker Oats", "Oatmeal", "1877", "pepsico.com"),
    ("PepsiCo", "Life Cereal", "Cereal", "1961", "pepsico.com"),
    ("PepsiCo", "Cap'n Crunch", "Cereal", "1963", "pepsico.com"),
    ("PepsiCo", "Tropicana", "Juice", "1947", "pepsico.com"),
    ("PepsiCo", "Gatorade", "Sports Drinks", "1965", "pepsico.com"),
    ("PepsiCo", "Aunt Jemima (Pearl Milling)", "Breakfast", "1888", "pepsico.com"),

    # ── Conagra ───────────────────────────────────────────────────────────────
    ("Conagra", "Birds Eye", "Frozen Vegetables", "1922", "conagrabrands.com"),
    ("Conagra", "Duncan Hines", "Baking", "1951", "conagrabrands.com"),
    ("Conagra", "Hunt's", "Tomatoes", "1890", "conagrabrands.com"),
    ("Conagra", "Chef Boyardee", "Canned Pasta", "1928", "conagrabrands.com"),
    ("Conagra", "Slim Jim", "Meat Snacks", "1928", "conagrabrands.com"),
    ("Conagra", "Vlasic", "Pickles", "1942", "conagrabrands.com"),
    ("Conagra", "Orville Redenbacher's", "Popcorn", "1970", "conagrabrands.com"),
    ("Conagra", "ACT II", "Popcorn", "1976", "conagrabrands.com"),
    ("Conagra", "Hebrew National", "Meat", "1905", "conagrabrands.com"),
    ("Conagra", "Marie Callender's", "Frozen Meals", "1948", "conagrabrands.com"),
    ("Conagra", "Healthy Choice", "Frozen Meals", "1988", "conagrabrands.com"),
    ("Conagra", "P.F. Chang's (frozen)", "Frozen Meals", "1993", "conagrabrands.com"),
]



# ── Corporate executives — public record ──────────────────────────────────────
# People have a right to know who is responsible behind the logo.
# Sources: company press releases, regulatory filings, public news coverage.
# Verified: April 2026. Update when leadership changes.

EXECUTIVES = {
    "Nestlé": {
        "name":  "Philipp Navratil",
        "title": "Chief Executive Officer",
        "since": "September 2025",
    },
    "Nestle": {
        "name":  "Philipp Navratil",
        "title": "Chief Executive Officer",
        "since": "September 2025",
    },
    "Unilever": {
        "name":  "Fernando Fernandez",
        "title": "Chief Executive Officer",
        "since": "March 2025",
    },
    "Kraft Heinz": {
        "name":  "Steve Cahillane",
        "title": "Chief Executive Officer",
        "since": "January 2026",
    },
    "General Mills": {
        "name":  "Jeff Harmening",
        "title": "Chairman & Chief Executive Officer",
        "since": "2017",
    },
    "Conagra": {
        "name":  "Sean Connolly",
        "title": "President & Chief Executive Officer",
        "since": "2015",
    },
    "ConAgra Brands": {
        "name":  "Sean Connolly",
        "title": "President & Chief Executive Officer",
        "since": "2015",
    },
    "PepsiCo": {
        "name":  "Ramon Laguarta",
        "title": "Chairman & Chief Executive Officer",
        "since": "2018",
    },
    "Kellanova": {
        "name":  "Poul Weihrauch",
        "title": "CEO, Mars Incorporated (parent — acquired Kellanova December 2025)",
        "since": "2022",
    },
}


class TruthWall:
    """
    The Truth Wall.
    Corporate ownership records, public and permanent.
    """

    def seed(self, db: Session) -> dict:
        """
        Seed the Truth Wall with known corporate ownership data.
        Called once on first run.
        """
        existing = db.query(TruthWallEntry).count()
        if existing > 0:
            return {"ok": True, "note": "Already seeded.", "count": existing}

        prev_hash = "0" * 64
        added = 0

        for corp, brand, category, since, source in SEED_DATA:
            data = {
                "corporation": corp,
                "brand":       brand,
                "category":    category,
                "owned_since": since,
            }
            entry_hash = hash_entry(data, prev_hash)

            entry = TruthWallEntry(
                corporation    = corp,
                brand          = brand,
                category       = category,
                owned_since    = since,
                source         = source,
                integrity_hash = entry_hash,
                prev_hash      = prev_hash,
                added_by       = "Krone the Architect",
            )
            db.add(entry)
            prev_hash = entry_hash
            added += 1

        db.commit()
        log_event(db, "TRUTH_WALL_SEEDED", "Krone the Architect",
                  "", f"{added} entries added")
        print(f"[TRUTH WALL] Seeded with {added} entries.")
        return {"ok": True, "added": added}

    def get_by_corporation(self, db: Session, corporation: str) -> list:
        entries = db.query(TruthWallEntry).filter(
            TruthWallEntry.corporation.ilike(f"%{corporation}%")
        ).order_by(TruthWallEntry.brand).all()
        return [self._format(e) for e in entries]

    def get_all(self, db: Session) -> dict:
        """
        Full Truth Wall — grouped by corporation.
        """
        entries = db.query(TruthWallEntry).order_by(
            TruthWallEntry.corporation,
            TruthWallEntry.brand
        ).all()

        grouped = {}
        for e in entries:
            if e.corporation not in grouped:
                grouped[e.corporation] = []
            grouped[e.corporation].append(self._format(e))

        return {
            "corporations": len(grouped),
            "brands":       len(entries),
            "wall":         grouped,
            "note":         "The harvest was never only theirs."
        }

    def search(self, db: Session, query: str) -> list:
        entries = db.query(TruthWallEntry).filter(
            TruthWallEntry.brand.ilike(f"%{query}%") |
            TruthWallEntry.corporation.ilike(f"%{query}%") |
            TruthWallEntry.category.ilike(f"%{query}%")
        ).all()
        return [self._format(e) for e in entries]

    def add_entry(self, db: Session, corporation: str,
                  brand: str, category: str,
                  owned_since: str, source: str,
                  added_by: str = "Krone the Architect") -> dict:
        """Add a new entry to the Truth Wall."""
        from sqlalchemy import desc
        last = db.query(TruthWallEntry).order_by(
            desc(TruthWallEntry.id)
        ).first()
        prev_hash = last.integrity_hash if last else "0" * 64

        data = {
            "corporation": corporation,
            "brand":       brand,
            "category":    category,
            "owned_since": owned_since,
        }
        entry_hash = hash_entry(data, prev_hash)

        entry = TruthWallEntry(
            corporation    = corporation,
            brand          = brand,
            category       = category,
            owned_since    = owned_since,
            source         = source,
            integrity_hash = entry_hash,
            prev_hash      = prev_hash,
            added_by       = added_by,
        )
        db.add(entry)
        db.commit()

        log_event(db, "TRUTH_WALL_ENTRY_ADDED", added_by,
                  brand, f"Owned by {corporation}")
        return {"ok": True, "brand": brand, "corporation": corporation}

    def verify_integrity(self, db: Session) -> dict:
        """Verify the Truth Wall hash chain."""
        from sqlalchemy import asc
        entries = db.query(TruthWallEntry).order_by(
            asc(TruthWallEntry.id)
        ).all()

        if not entries:
            return {"ok": True, "note": "No entries yet."}

        prev_hash = "0" * 64
        for i, entry in enumerate(entries):
            data = {
                "corporation": entry.corporation,
                "brand":       entry.brand,
                "category":    entry.category,
                "owned_since": entry.owned_since,
            }
            computed = hash_entry(data, prev_hash)
            if computed != entry.integrity_hash:
                return {
                    "ok":    False,
                    "error": f"Truth Wall tampered at entry {i+1}: {entry.brand}",
                }
            prev_hash = entry.integrity_hash

        return {"ok": True, "entries": len(entries), "chain": "intact"}

    def _format(self, entry: TruthWallEntry) -> dict:
        return {
            "corporation": entry.corporation,
            "brand":       entry.brand,
            "category":    entry.category,
            "owned_since": entry.owned_since,
            "source":      entry.source,
            "added_at":    entry.added_at.isoformat(),
        }


truth_wall = TruthWall()
