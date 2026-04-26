"""
main.py — Gleaning

The harvest was never only theirs.

Usage:
    python main.py          # Start Gleaning
    python main.py --check  # Configuration check only

— Krone the Architect · 2026
"""


from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from gleaning.database import get_db, init_db, verify_log_integrity, Base, engine
from gleaning.codex import codex
from gleaning.resilience import ResilienceManager
from gleaning.truth_wall import truth_wall
from gleaning.matching import match_engine
from gleaning.guardian import guardian
from gleaning.watcher import watcher_coordinator
from gleaning.hoarders import hoarders, HoarderPost, ModerationAction
from gleaning.gleaning_circle import (
    display_team, display_circle,
    deliberation as team_deliberation,
    auto_deliberate
)

VERSION = "1.0.0"

resilience = ResilienceManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    print()
    print("╔═══════════════════════════════════════════════════╗")
    print("║              G L E A N I N G                     ║")
    print("╠═══════════════════════════════════════════════════╣")
    print(f"║  Version:  {VERSION:<41}║")
    print("║  The harvest was never only theirs.               ║")
    print("╠═══════════════════════════════════════════════════╣")
    print("║  Founded by Krone the Architect · 2026            ║")
    print("║  Power to the People.                             ║")
    print("╚═══════════════════════════════════════════════════╝")
    print()

    # Startup checks
    resilience.startup_check()

    # Initialize database — all tables including Hoarders
    init_db()
    Base.metadata.create_all(bind=engine)
    # Migrate: add gleaning status columns if not present
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            for col, typedef in [
                ("gleaned",           "BOOLEAN DEFAULT FALSE"),
                ("gleaned_at",        "TIMESTAMP NULL"),
                ("last_confirmed_at", "TIMESTAMP NULL"),
            ]:
                try:
                    conn.execute(text(f"ALTER TABLE hoarder_posts ADD COLUMN {col} {typedef}"))
                    conn.commit()
                    print(f"[GLEANING] Migrated: added {col} to hoarder_posts")
                except Exception:
                    pass  # column already exists
    except Exception as e:
        print(f"[GLEANING] Migration check failed: {e}")

    # Seed Truth Wall on first run
    from gleaning.database import SessionLocal
    db = SessionLocal()
    try:
        truth_wall.seed(db)
    finally:
        db.close()

    # Seed corporate waste data on first run
    from gleaning.database import CorporateWasteRecord
    from datetime import datetime, timezone
    db = SessionLocal()
    try:
        existing = db.query(CorporateWasteRecord).count()
        if existing == 0:
            CORPORATE_WASTE_SEED = [
                {"corporation": "Nestlé",        "metric_tons": 1600000, "period": "2023", "source_name": "Nestlé Creating Shared Value and Sustainability Report 2023", "source_url": "https://www.nestle.com/sites/default/files/2024-02/creating-shared-value-sustainability-report-2023-en.pdf"},
                {"corporation": "PepsiCo",        "metric_tons": 2600000, "period": "2023", "source_name": "PepsiCo ESG Topics — Waste 2023", "source_url": "https://www.pepsico.com/en/esg-topics/waste"},
                {"corporation": "Unilever",       "metric_tons": 100000,  "period": "2023", "source_name": "Unilever Annual Report and Accounts 2024", "source_url": "https://www.unilever.com/planet-and-society/waste-free-world/"},
                {"corporation": "Kraft Heinz",    "metric_tons": 150000,  "period": "2023", "source_name": "Kraft Heinz ESG Report", "source_url": "https://www.kraftheinzcompany.com/esg/planet.html"},
                {"corporation": "General Mills",  "metric_tons": 200000,  "period": "FY2024", "source_name": "General Mills Global Responsibility Report", "source_url": "https://globalresponsibility.generalmills.com"},
                {"corporation": "Conagra Brands", "metric_tons": 120000,  "period": "FY2024", "source_name": "Conagra Brands Corporate Responsibility Report", "source_url": "https://www.conagrabrands.com/corporate-responsibility/planet"},
                {"corporation": "Mars/Kellanova", "metric_tons": 300000,  "period": "2023", "source_name": "Mars Incorporated Sustainability Report", "source_url": "https://www.mars.com/sustainability-plan/reporting-performance"},
                {"corporation": "Kroger",         "metric_tons": 222522,  "period": "2023", "source_name": "Kroger 2024 ESG Report (Zero Hunger | Zero Waste)", "source_url": "https://www.thekrogerco.com/wp-content/uploads/2025/03/Kroger-Co-2024-ESG-Report.pdf"},
                {"corporation": "Walmart",        "metric_tons": 0,       "period": "2023", "source_name": "Walmart FY2025 ESG Report — total food waste not publicly disclosed", "source_url": "https://corporate.walmart.com/purpose/esgreport"},
                {"corporation": "Amazon/Whole Foods", "metric_tons": 0,   "period": "2023", "source_name": "Whole Foods 2023 Impact Report — total food waste not publicly disclosed", "source_url": "https://media.wholefoodsmarket.com/whole-foods-market-releases-2023-impact-report-highlighting-agriculture-as-a-force-for-good/"},
                {"corporation": "Albertsons",     "metric_tons": 0,       "period": "2022", "source_name": "Albertsons 2023 ESG Report — total food waste not publicly disclosed", "source_url": "https://www.albertsonscompanies.com/newsroom/press-releases/news-details/2023/Albertsons-Companies-Releases-2023-ESG-Report/default.aspx"},
            ]
            existing_corps = {r.corporation for r in db.query(CorporateWasteRecord).all()}
            added = 0
            for corp in CORPORATE_WASTE_SEED:
                if corp["corporation"] not in existing_corps:
                    lbs = int(corp["metric_tons"] * 2204.62)
                    db.add(CorporateWasteRecord(
                        corporation = corp["corporation"],
                        lbs_wasted  = lbs,
                        source_name = corp["source_name"],
                        source_url  = corp["source_url"],
                        period      = corp["period"],
                        note        = "Seeded from published corporate sustainability reports. WasteWatch updates when new data is published.",
                    ))
                    added += 1
            if added:
                db.commit()
                print(f"[GLEANING] Added {added} new corporation(s) to waste records.")
            else:
                print(f"[GLEANING] Corporate waste data already current — {existing} records.")
    finally:
        db.close()

    # Start resilience systems
    resilience.start()
    guardian.startup()
    watcher_coordinator.start()

    # Display the Gleaning Circle
    display_team()

    print("[GLEANING] The map is open.")
    print("[GLEANING] The match engine is running.")
    print("[GLEANING] The Team is present.")
    print("[GLEANING] Gleaning is live.\n")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    resilience.stop()
    guardian.stop()
    watcher_coordinator.stop()
    
app = FastAPI(
    title       = "Gleaning",
    description = "Food surplus to the people. The harvest was never only theirs.",
    version     = VERSION,
    lifespan    = lifespan,
)

# ── Static files and templates ────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media",  StaticFiles(directory="media"),  name="media")
templates = Jinja2Templates(directory="templates")

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        from gleaning.database import CorporateWasteRecord
        db = next(get_db())
        waste_rows = db.query(CorporateWasteRecord).filter(
            CorporateWasteRecord.verified == True
        ).all()
        total_lbs = sum(r.total_lbs for r in waste_rows if r.total_lbs)
        families_fed = int(total_lbs / 38)
    except Exception:
        families_fed = 294142721
    return templates.TemplateResponse("index.html", {"request": request, "title": "Gleaning", "families_fed": families_fed})

@app.get("/wall", response_class=HTMLResponse)
async def wall_redirect(request: Request):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/stats")

@app.get("/wall/search")
async def wall_search(q: str, db: Session = Depends(get_db)):
    results = truth_wall.search(db, q)
    return {"results": results, "query": q}

@app.get("/api/wall")
async def api_wall(db: Session = Depends(get_db)):
    return truth_wall.get_all(db)

@app.get("/map", response_class=HTMLResponse)
async def map_redirect(request: Request):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/hoarders")

@app.get("/api/surplus")
async def api_surplus(category: str = None, db: Session = Depends(get_db)):
    return match_engine.get_available_surplus(db, category=category)

@app.post("/api/surplus")
async def post_surplus(
    donor_id:        int,
    title:           str,
    description:     str = "",
    quantity:        str = "",
    category:        str = "",
    pickup_address:  str = "",
    available_hours: int = 24,
    db: Session = Depends(get_db)
):
    from datetime import timedelta, datetime, timezone
    now   = datetime.now(timezone.utc)
    until = now + timedelta(hours=available_hours)
    return match_engine.post_surplus(
        db, donor_id, title, description,
        quantity, category, now, until, pickup_address
    )

@app.post("/api/need")
async def post_need(
    pantry_id:   int,
    category:    str,
    description: str = "",
    urgency:     str = "NORMAL",
    db: Session = Depends(get_db)
):
    return match_engine.post_need(db, pantry_id, category, description, urgency)

@app.post("/api/match/{match_id}/confirm")
async def confirm_match(match_id: int, pantry_id: int,
                        db: Session = Depends(get_db)):
    return match_engine.confirm_match(db, match_id, pantry_id)

@app.post("/api/match/{match_id}/collected")
async def record_collection(match_id: int, pantry_id: int,
                             db: Session = Depends(get_db)):
    return match_engine.record_collection(db, match_id, pantry_id)

@app.get("/api/stats")
async def stats(db: Session = Depends(get_db)):
    return match_engine.get_stats(db)

@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request, db: Session = Depends(get_db)):
    try:
        from gleaning.database import CorporateWasteRecord
        waste_rows = db.query(CorporateWasteRecord).filter(
            CorporateWasteRecord.verified == True
        ).all()
        total_lbs = sum(r.lbs_wasted or 0 for r in waste_rows)
        last_updated = max((r.recorded_at for r in waste_rows), default=None)
        data = {
            "total_families_fed": int(total_lbs / 38),
            "total_waste_lbs": int(total_lbs),
            "total_subsidies": "47B+",
            "corporations": 7,
            "total_brands": "900+",
            "last_updated": last_updated.strftime("%b %d, %Y") if last_updated else "pending",
        }
    except Exception:
        data = {
            "total_families_fed": 0,
            "total_waste_lbs": 0,
            "total_subsidies": "47B+",
            "corporations": 7,
            "total_brands": "900+",
            "last_updated": "pending",
        }
    return templates.TemplateResponse("stats.html", {"request": request, "stats": data})


# ── Flagged items — Watcher flags for Team/Founder review ─────────────────────

@app.get("/flagged", response_class=HTMLResponse)
async def flagged_page(request: Request):
    return templates.TemplateResponse("flagged.html", {"request": request})

@app.get("/api/flagged")
async def get_flagged():
    """Active flags — not deleted, not reviewed."""
    return {
        "ok":    True,
        "flags": watcher_coordinator.get_flagged(),
        "count": len(watcher_coordinator.get_flagged()),
    }

@app.get("/api/flagged/saved")
async def get_saved_flags():
    """Flags the Team saved for future reference."""
    return {
        "ok":    True,
        "flags": watcher_coordinator.get_saved(),
        "count": len(watcher_coordinator.get_saved()),
    }

@app.post("/api/flagged/{index}/delete")
async def delete_flag(index: int):
    """Mark a flag as irrelevant — removes from active queue."""
    return watcher_coordinator.delete_flag(index)

@app.post("/api/flagged/{index}/save")
async def save_flag(index: int):
    """Mark a flag as saved — keeps it for future reference."""
    return watcher_coordinator.save_flag(index)

@app.post("/api/flagged/purge")
async def purge_deleted_flags():
    """Permanently remove all deleted flags. Saved flags are never purged."""
    return watcher_coordinator.purge_deleted()


@app.get("/resources", response_class=HTMLResponse)
async def resources_page(request: Request):
    return templates.TemplateResponse("resources.html", {"request": request})

@app.get("/api/resources")
async def api_resources(category: str = None, state: str = None, q: str = None):
    from gleaning.database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        query = "SELECT * FROM resources WHERE 1=1"
        params = {}
        if category:
            query += " AND category = :category"
            params["category"] = category
        if state:
            query += " AND state = :state"
            params["state"] = state.upper()
        if q:
            query += " AND (name ILIKE :q OR city ILIKE :q OR services ILIKE :q)"
            params["q"] = f"%{q}%"
        query += " ORDER BY name LIMIT 500"
        rows = db.execute(text(query), params).fetchall()
        return [dict(r._mapping) for r in rows]
    except Exception as e:
        return []
    finally:
        db.close()

@app.get("/health")
async def health(db: Session = Depends(get_db)):
    integrity = verify_log_integrity(db)
    return {
        "status":    "ok",
        "version":   VERSION,
        "integrity": integrity,
        "note":      "The harvest was never only theirs."
    }

# ── Hoarders ──────────────────────────────────────────────────────────────────

import hashlib as _hashlib

def _check_founder(passphrase: str) -> bool:
    """Verify founder passphrase against stored hash."""
    import os
    founder_hash = os.environ.get("FOUNDER_HASH", "")
    founder_salt = os.environ.get("FOUNDER_SALT", "")
    if not founder_hash or not founder_salt:
        return False
    salted = f"{founder_salt}:{passphrase}"
    computed = _hashlib.sha256(salted.encode()).hexdigest()
    return computed == founder_hash



@app.get("/hoarders", response_class=HTMLResponse)
async def hoarders_page(request: Request, db: Session = Depends(get_db)):
    posts  = hoarders.get_approved(db)
    totals = hoarders.get_totals(db)
    return templates.TemplateResponse("hoarders.html", {"request": request, 
            "reports":         posts,
            "families_fed":    totals["families_weeks"],
            "total_reports":   totals["total_posts"],
            "total_lbs":       totals["total_lbs"],
            "locations_count": len(set(p["location"] for p in posts if p["location"])),
        })

@app.post("/hoarders/{post_id}/gleaned")
async def mark_gleaned(post_id: int, db: Session = Depends(get_db)):
    from datetime import datetime, timezone
    post = db.query(HoarderPost).filter(HoarderPost.id == post_id).first()
    if not post:
        return {"ok": False, "error": "Post not found"}
    post.gleaned    = True
    post.gleaned_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "gleaned": True}

@app.post("/hoarders/{post_id}/still-here")
async def mark_still_here(post_id: int, db: Session = Depends(get_db)):
    from datetime import datetime, timezone
    post = db.query(HoarderPost).filter(HoarderPost.id == post_id).first()
    if not post:
        return {"ok": False, "error": "Post not found"}
    post.last_confirmed_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "confirmed": True}

@app.post("/hoarders/problem-report")
async def problem_report(
    description: str = Form(...),
    contact:     str = Form(""),
):
    try:
        from gleaning.hoarders_email import on_problem_report
        on_problem_report(description, contact)
    except Exception as e:
        print(f"[GLEANING] Problem report email failed: {e}")
    return {"ok": True}

@app.get("/hoarders/submit", response_class=HTMLResponse)
async def hoarders_submit_page(request: Request):
    return templates.TemplateResponse("submit.html", {"request": request})

@app.post("/hoarders/submit", response_class=HTMLResponse)
async def hoarders_submit(
    request:      Request,
    db:           Session = Depends(get_db),
    lat:          float   = Form(None),
    lng:          float   = Form(None),
    lbs_estimate: float   = Form(...),
    note:         str     = Form(""),
    email:        str     = Form(...),
    photo:        UploadFile = File(None),
):
    import uuid, shutil
    from pathlib import Path

    if lat is None or lng is None:
        return templates.TemplateResponse("submit.html", {"request": request, "error": "Location pin is required. Tap the map to drop a pin."})

    # Save photo
    photo_path = ""
    if photo and photo.filename:
        media_dir = Path("media/hoarders")
        media_dir.mkdir(parents=True, exist_ok=True)
        ext        = Path(photo.filename).suffix or ".jpg"
        filename   = f"{uuid.uuid4().hex}{ext}"
        dest       = media_dir / filename
        with dest.open("wb") as f:
            shutil.copyfileobj(photo.file, f)
        photo_path = f"hoarders/{filename}"

    result = hoarders.submit(
        db            = db,
        description   = note or "No description provided.",
        estimated_lbs = lbs_estimate,
        latitude      = lat,
        longitude     = lng,
        photo_path    = photo_path,
        contact       = email,
    )

    if not result["ok"]:
        return templates.TemplateResponse("submit.html", {"request": request, "error": result["error"]})

    # Team deliberates automatically in background
    import threading
    report_data = {
        "estimated_lbs": lbs_estimate,
        "latitude":      lat,
        "longitude":     lng,
        "description":   note,
        "photo_path":    photo_path,
        "posted_at":     str(result.get("post_id", "")),
    }
    threading.Thread(
        target=auto_deliberate.run,
        args=(result["post_id"], report_data),
        daemon=True
    ).start()

    return templates.TemplateResponse("submit.html", {"request": request, "success": "Your report has been submitted and is under review. Thank you for documenting this."})

@app.get("/hoarders/moderate", response_class=HTMLResponse)
async def moderate_page(request: Request):
    return templates.TemplateResponse("moderate.html", {"request": request, "authenticated": False})

@app.post("/hoarders/moderate", response_class=HTMLResponse)
async def moderate_action(
    request:    Request,
    db:         Session = Depends(get_db),
    passphrase: str     = Form(...),
    action:     str     = Form("login"),
    report_id:  int     = Form(None),
    decision:   str     = Form(None),
    note:       str     = Form(""),
):
    if not _check_founder(passphrase):
        return templates.TemplateResponse("moderate.html", {"request": request, "authenticated": False, "error": "Authentication failed."})

    # Krone makes a final call on a split report
    if action == "krone_decide" and report_id and decision:
        team_deliberation.krone_decides(report_id, decision, note)
        action_map = {"APPROVED": "APPROVE", "DENIED": "REJECT"}
        hoarders.moderate(db, report_id, "Krone", action_map.get(decision, decision), note)

    # Build context for the page
    from gleaning.gleaning_circle import _load, DELIBERATION_LOG, DECISION_LOG, FOUNDER_QUEUE
    pending      = hoarders.get_pending(db)
    krone_queue  = team_deliberation.get_krone_queue()
    decision_log = list(reversed(_load(DECISION_LOG)))[:30]

    # Attach report objects to krone queue items
    for item in krone_queue:
        item["report"] = db.query(hoarders.__class__).filter_by(id=item["report_id"]).first() if False else next(
            (r for r in [db.query(__import__("gleaning.hoarders", fromlist=["HoarderPost"]).HoarderPost).filter_by(id=item["report_id"]).first()]), None
        )

    # Map deliberations to report ids
    all_delibs = _load(DELIBERATION_LOG)
    deliberations = {d["report_id"]: d for d in all_delibs}

    success_msg = None
    if action == "krone_decide" and report_id and decision:
        success_msg = f"Report #{report_id} — {decision}. Your decision is logged."

    return templates.TemplateResponse("moderate.html", {"request": request, 
            "authenticated":  True,
            "session_token":  passphrase,
            "pending_queue":  pending,
            "krone_queue":    krone_queue,
            "decision_log":   decision_log,
            "deliberations":  deliberations,
            "success":        success_msg,
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host   = config.host,
        port   = config.port,
        reload = config.debug,
    )
