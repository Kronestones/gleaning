"""
resource_scanner.py — Gleaning Active Resource Scanner

Runs as a background thread. Wakes every 24 hours and fetches
live resources from public APIs. Deduplicates against existing DB.
Sends team email summary after each scan.

Threading pattern adapted from Themis resilience.py.
— Krone the Architect · 2026
"""

import threading
import time
import os
import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone

SCAN_INTERVAL_HOURS = 24
FOUNDER_EMAIL = os.environ.get("FOUNDER_EMAIL", "")
TEAM_EMAIL = os.environ.get("TEAM_EMAIL", FOUNDER_EMAIL)
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_ADDRESS = os.environ.get("FROM_ADDRESS", "Gleaning <noreply@gleaning.onrender.com>")

_stop_event = threading.Event()


def _send_summary(added: list, errors: list):
    if not TEAM_EMAIL or not RESEND_API_KEY:
        print("[SCANNER] Email not configured — skipping summary.")
        return
    if not added and not errors:
        return
    rows = "".join(
        f"<tr><td style='padding:6px 10px;color:#ccc'>{r['name']}</td>"
        f"<td style='padding:6px 10px;color:#666'>{r['category']}</td>"
        f"<td style='padding:6px 10px;color:#666'>{r.get('city','')}, {r.get('state','')}</td></tr>"
        for r in added[:50]
    )
    error_html = ""
    if errors:
        error_html = f"<p style='color:#e74c3c;margin-top:16px'>⚠ {len(errors)} source(s) failed: {', '.join(errors)}</p>"
    html = f"""
    <div style="background:#0a0a0a;color:#e8e8e8;font-family:sans-serif;padding:32px;max-width:700px;margin:0 auto">
      <h2 style="color:#7cb87c;margin-bottom:4px">🌾 Gleaning — Resource Scanner Report</h2>
      <p style="color:#666;margin-bottom:24px">{datetime.now(timezone.utc).strftime("%b %d, %Y %H:%M UTC")}</p>
      <p style="color:#aaa;margin-bottom:16px"><strong style="color:#fff">{len(added)}</strong> new resources added.</p>
      {("<table style='width:100%;border-collapse:collapse'><thead><tr><th style='padding:8px;color:#666;text-align:left'>Name</th><th style='padding:8px;color:#666;text-align:left'>Category</th><th style='padding:8px;color:#666;text-align:left'>Location</th></tr></thead><tbody>" + rows + "</tbody></table>") if added else ""}
      {error_html}
      <p style="color:#444;font-size:12px;margin-top:24px">Gleaning Resource Scanner · Runs every 24 hours · Escalate to Krone if needed</p>
    </div>
    """
    payload = json.dumps({
        "from": FROM_ADDRESS,
        "to": [TEAM_EMAIL],
        "subject": f"[Gleaning] Scanner: {len(added)} new resources found",
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
            print(f"[SCANNER] Summary email sent — status {resp.status}")
    except Exception as e:
        print(f"[SCANNER] Summary email failed: {e}")


def _save_resource(session, r: dict) -> bool:
    try:
        from sqlalchemy import text
        existing = session.execute(
            text("SELECT id FROM resources WHERE name=:n AND city=:c AND state=:s"),
            {"n": r["name"], "c": r.get("city", ""), "s": r.get("state", "")}
        ).fetchone()
        if existing:
            return False
        session.execute(text("""
            INSERT INTO resources
            (name, category, address, city, state, zip_code, lat, lng,
             phone, website, services, hours, is_popup, verified, source)
            VALUES
            (:name,:category,:address,:city,:state,:zip_code,:lat,:lng,
             :phone,:website,:services,:hours,:is_popup,:verified,:source)
        """), {
            "name": r.get("name",""), "category": r.get("category","health"),
            "address": r.get("address",""), "city": r.get("city",""),
            "state": r.get("state",""), "zip_code": r.get("zip_code",""),
            "lat": r.get("lat"), "lng": r.get("lng"),
            "phone": r.get("phone",""), "website": r.get("website",""),
            "services": r.get("services",""), "hours": r.get("hours",""),
            "is_popup": r.get("is_popup", False), "verified": r.get("verified", True),
            "source": r.get("source",""),
        })
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"[SCANNER] Save error for {r.get('name')}: {e}")
        return False


def _fetch_hrsa(session) -> tuple:
    added, errors = [], []
    states = ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
              "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
              "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
              "VA","WA","WV","WI","WY","DC"]
    for state in states:
        if _stop_event.is_set():
            break
        try:
            url = f"https://findahealthcenter.hrsa.gov/api/geolocate?siteState={state}&pageSize=100"
            req = urllib.request.Request(url, headers={"User-Agent": "Gleaning/1.0 (sentinel.commons@gmail.com)"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            for site in data.get("results", data.get("sites", [])):
                r = {
                    "name": site.get("siteName") or site.get("name",""),
                    "category": "health",
                    "address": site.get("siteAddress1") or site.get("address",""),
                    "city": site.get("siteCity") or site.get("city",""),
                    "state": site.get("siteState") or state,
                    "zip_code": site.get("siteZipCode") or site.get("zip",""),
                    "lat": site.get("latitude") or site.get("lat"),
                    "lng": site.get("longitude") or site.get("lng"),
                    "phone": site.get("sitePhone") or site.get("phone",""),
                    "website": site.get("siteWebsite") or site.get("website",""),
                    "services": "Free/low-cost health care · FQHC · Sliding scale · No one turned away",
                    "source": "HRSA findahealthcenter.hrsa.gov",
                    "verified": True,
                }
                if r["name"] and _save_resource(session, r):
                    added.append(r)
            time.sleep(0.5)
        except Exception as e:
            errors.append(f"HRSA-{state}")
            print(f"[SCANNER] HRSA {state} failed: {e}")
    print(f"[SCANNER] HRSA: {len(added)} new centers")
    return added, errors


def _fetch_ram(session) -> tuple:
    added, errors = [], []
    try:
        import re
        url = "https://www.ramusa.org/events/"
        req = urllib.request.Request(url, headers={"User-Agent": "Gleaning/1.0 (sentinel.commons@gmail.com)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        events = re.findall(r'<h[23][^>]*>(.*?)</h[23]>.*?(\w[\w\s]+,\s*[A-Z]{2})', html, re.DOTALL)
        for title, location in events[:20]:
            title = re.sub(r'<[^>]+>', '', title).strip()
            if not title or len(title) < 5:
                continue
            parts = location.split(",")
            r = {
                "name": f"RAM Free Clinic — {title}",
                "category": "health",
                "city": parts[0].strip() if parts else "",
                "state": parts[1].strip()[:2] if len(parts) > 1 else "",
                "website": "https://www.ramusa.org/events/",
                "services": "Free popup clinic · Dental · Vision · Medical · No insurance required",
                "is_popup": True,
                "source": "Remote Area Medical · ramusa.org",
                "verified": True,
            }
            if r["city"] and _save_resource(session, r):
                added.append(r)
    except Exception as e:
        errors.append("RAM")
        print(f"[SCANNER] RAM failed: {e}")
    print(f"[SCANNER] RAM: {len(added)} new clinics")
    return added, errors


def _fetch_211(session) -> tuple:
    added, errors = [], []
    searches = [
        ("free clinic", "health"), ("food pantry", "food"),
        ("emergency shelter", "housing"), ("free legal aid", "legal"),
        ("job training", "education"), ("utility assistance", "community"),
        ("free dental", "health"), ("mental health free", "health"),
        ("prescription assistance", "health"), ("free vision", "health"),
    ]
    for query, category in searches:
        if _stop_event.is_set():
            break
        try:
            url = f"https://api.211.org/search/v1/search?keyword={urllib.parse.quote(query)}&pageSize=50"
            req = urllib.request.Request(url, headers={"User-Agent": "Gleaning/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            for item in data.get("records", data.get("results", [])):
                name = item.get("agencyName") or item.get("name","")
                if not name:
                    continue
                r = {
                    "name": name, "category": category,
                    "address": item.get("streetAddress",""),
                    "city": item.get("city",""), "state": item.get("stateProvince",""),
                    "zip_code": item.get("postalCode",""),
                    "lat": item.get("latitude"), "lng": item.get("longitude"),
                    "phone": item.get("phoneNumber",""), "website": item.get("website",""),
                    "services": item.get("serviceName",""),
                    "source": "211.org API · Public record", "verified": True,
                }
                if _save_resource(session, r):
                    added.append(r)
            time.sleep(1)
        except Exception as e:
            errors.append(f"211-{query}")
            print(f"[SCANNER] 211 '{query}' failed: {e}")
    print(f"[SCANNER] 211: {len(added)} new resources")
    return added, errors


def _run_scan():
    print(f"[SCANNER] Scan starting — {datetime.now(timezone.utc).strftime('%b %d %H:%M UTC')}")
    try:
        from gleaning.database import SessionLocal
        session = SessionLocal()
        all_added, all_errors = [], []
        try:
            a, e = _fetch_hrsa(session);  all_added += a; all_errors += e
            a, e = _fetch_ram(session);   all_added += a; all_errors += e
            a, e = _fetch_211(session);   all_added += a; all_errors += e
        finally:
            session.close()
        print(f"[SCANNER] Complete — {len(all_added)} new resources")
        _send_summary(all_added, all_errors)
    except Exception as e:
        print(f"[SCANNER] Scan failed: {e}")


def _scanner_loop():
    print("[SCANNER] Resource scanner starting...")
    time.sleep(30)
    while not _stop_event.is_set():
        _run_scan()
        for _ in range(SCAN_INTERVAL_HOURS * 360):
            if _stop_event.is_set():
                break
            time.sleep(10)
    print("[SCANNER] Stopped.")


def start():
    _stop_event.clear()
    thread = threading.Thread(target=_scanner_loop, daemon=True, name="ResourceScanner")
    thread.start()
    print("[SCANNER] Thread launched — first scan in 30s.")


def stop():
    _stop_event.set()
    print("[SCANNER] Stop signal sent.")
