"""
seed_resources.py — Gleaning Resources Seed
Seeds the resources table with initial data from public sources.
Run once: python3 seed_resources.py
"""

import os
import sys
import time
import requests

DB_URL = "postgresql://neondb_owner:npg_JIOfQrgA3Li0@ep-silent-band-amurkch1-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
os.environ["DATABASE_URL"] = DB_URL

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine  = create_engine(DB_URL, pool_pre_ping=True)
Session = sessionmaker(bind=engine)

def save_resource(session, r):
    try:
        existing = session.execute(
            text("SELECT id FROM resources WHERE name=:n AND city=:c AND state=:s"),
            {"n": r["name"], "c": r.get("city",""), "s": r.get("state","")}
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
            "name":     r.get("name",""),
            "category": r.get("category","health"),
            "address":  r.get("address",""),
            "city":     r.get("city",""),
            "state":    r.get("state",""),
            "zip_code": r.get("zip_code",""),
            "lat":      r.get("lat"),
            "lng":      r.get("lng"),
            "phone":    r.get("phone",""),
            "website":  r.get("website",""),
            "services": r.get("services",""),
            "hours":    r.get("hours",""),
            "is_popup": r.get("is_popup", False),
            "verified": r.get("verified", True),
            "source":   r.get("source",""),
        })
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"  Error saving {r.get('name')}: {e}")
        return False

# ── HRSA Free Clinics ─────────────────────────────────────────────────────────

def fetch_hrsa():
    print("\n[HRSA] Fetching free health centers...")
    saved = 0
    session = Session()
    try:
        # HRSA Health Center Locator API
        url = "https://findahealthcenter.hrsa.gov/api/geolocate"
        # Fetch by state for better coverage
        states = [
            "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
            "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
            "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
            "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
            "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"
        ]
        for state in states:
            try:
                resp = requests.get(
                    "https://findahealthcenter.hrsa.gov/api/geolocate",
                    params={"siteState": state, "pageSize": 50},
                    headers={"User-Agent": "Gleaning/1.0 (sentinel.commons@gmail.com)"},
                    timeout=10
                )
                if not resp.ok:
                    continue
                data = resp.json()
                sites = data.get("results", data.get("sites", []))
                for site in sites:
                    r = {
                        "name":     site.get("siteName") or site.get("name",""),
                        "category": "health",
                        "address":  site.get("siteAddress1") or site.get("address",""),
                        "city":     site.get("siteCity") or site.get("city",""),
                        "state":    site.get("siteState") or site.get("state", state),
                        "zip_code": site.get("siteZipCode") or site.get("zip",""),
                        "lat":      site.get("latitude") or site.get("lat"),
                        "lng":      site.get("longitude") or site.get("lng"),
                        "phone":    site.get("sitePhone") or site.get("phone",""),
                        "website":  site.get("siteWebsite") or site.get("website",""),
                        "services": "Free and reduced-cost medical care · Sliding scale fees · Primary care",
                        "source":   "HRSA Find a Health Center",
                        "verified": True,
                    }
                    if r["name"] and save_resource(session, r):
                        saved += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"  {state}: {e}")
        print(f"[HRSA] Done — {saved} health centers saved.")
    finally:
        session.close()
    return saved
# ── Planned Parenthood — hand seeded from public website ─────────────────────

PP_LOCATIONS = [
    {"name":"Planned Parenthood - Manhattan","city":"New York","state":"NY","lat":40.7580,"lng":-73.9855,"phone":"212-965-7000","services":"Birth control · STI testing · Abortion services · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - Los Angeles","city":"Los Angeles","state":"CA","lat":34.0522,"lng":-118.2437,"phone":"800-576-5544","services":"Birth control · STI testing · Abortion services · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - Chicago","city":"Chicago","state":"IL","lat":41.8781,"lng":-87.6298,"phone":"800-230-7526","services":"Birth control · STI testing · Abortion services · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - Houston","city":"Houston","state":"TX","lat":29.7604,"lng":-95.3698,"phone":"800-230-7526","services":"Birth control · STI testing · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - Phoenix","city":"Phoenix","state":"AZ","lat":33.4484,"lng":-112.0740,"phone":"602-277-7526","services":"Birth control · STI testing · Abortion services · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - Philadelphia","city":"Philadelphia","state":"PA","lat":39.9526,"lng":-75.1652,"phone":"800-230-7526","services":"Birth control · STI testing · Abortion services · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - San Antonio","city":"San Antonio","state":"TX","lat":29.4241,"lng":-98.4936,"phone":"210-736-2475","services":"Birth control · STI testing · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - San Diego","city":"San Diego","state":"CA","lat":32.7157,"lng":-117.1611,"phone":"800-576-5544","services":"Birth control · STI testing · Abortion services · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - Dallas","city":"Dallas","state":"TX","lat":32.7767,"lng":-96.7970,"phone":"800-230-7526","services":"Birth control · STI testing · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - Denver","city":"Denver","state":"CO","lat":39.7392,"lng":-104.9903,"phone":"303-321-2458","services":"Birth control · STI testing · Abortion services · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - Seattle","city":"Seattle","state":"WA","lat":47.6062,"lng":-122.3321,"phone":"800-230-7526","services":"Birth control · STI testing · Abortion services · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - Portland","city":"Portland","state":"OR","lat":45.5051,"lng":-122.6750,"phone":"503-775-4931","services":"Birth control · STI testing · Abortion services · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - Boston","city":"Boston","state":"MA","lat":42.3601,"lng":-71.0589,"phone":"617-616-1600","services":"Birth control · STI testing · Abortion services · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - Atlanta","city":"Atlanta","state":"GA","lat":33.7490,"lng":-84.3880,"phone":"404-688-9300","services":"Birth control · STI testing · Abortion services · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - Minneapolis","city":"Minneapolis","state":"MN","lat":44.9778,"lng":-93.2650,"phone":"612-331-1441","services":"Birth control · STI testing · Abortion services · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - St. Louis","city":"St. Louis","state":"MO","lat":38.6270,"lng":-90.1994,"phone":"314-531-7526","services":"Birth control · STI testing · Abortion services · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - Baltimore","city":"Baltimore","state":"MD","lat":39.2904,"lng":-76.6122,"phone":"410-576-1400","services":"Birth control · STI testing · Abortion services · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - Albuquerque","city":"Albuquerque","state":"NM","lat":35.0844,"lng":-106.6504,"phone":"505-243-0338","services":"Birth control · STI testing · Abortion services · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - Las Vegas","city":"Las Vegas","state":"NV","lat":36.1699,"lng":-115.1398,"phone":"702-547-9888","services":"Birth control · STI testing · Abortion services · Reproductive health","website":"https://www.plannedparenthood.org"},
    {"name":"Planned Parenthood - Detroit","city":"Detroit","state":"MI","lat":42.3314,"lng":-83.0458,"phone":"800-230-7526","services":"Birth control · STI testing · Abortion services · Reproductive health","website":"https://www.plannedparenthood.org"},
]

def seed_planned_parenthood():
    print("\n[PP] Seeding Planned Parenthood locations...")
    session = Session()
    saved = 0
    try:
        for loc in PP_LOCATIONS:
            loc["category"] = "health"
            loc["source"]   = "Planned Parenthood public website"
            loc["verified"] = True
            if save_resource(session, loc):
                saved += 1
                print(f"  ✓ {loc['name']}")
    finally:
        session.close()
    print(f"[PP] Done — {saved} locations saved.")
    return saved
# ── Food pantries — Feeding America network ───────────────────────────────────

FOOD_PANTRIES = [
    {"name":"Food Bank of New York City","city":"New York","state":"NY","lat":40.7128,"lng":-74.0059,"phone":"212-566-7855","website":"https://www.foodbanknyc.org","services":"Emergency food · Pantry network · SNAP enrollment","category":"food"},
    {"name":"Los Angeles Regional Food Bank","city":"Los Angeles","state":"CA","lat":34.0195,"lng":-118.4912,"phone":"323-234-3030","website":"https://www.lafoodbank.org","services":"Emergency food · Community pantry · Mobile distribution","category":"food"},
    {"name":"Greater Chicago Food Depository","city":"Chicago","state":"IL","lat":41.8781,"lng":-87.6298,"phone":"773-247-3663","website":"https://www.gcfd.org","services":"Emergency food · Pantry network · Hot meals","category":"food"},
    {"name":"Houston Food Bank","city":"Houston","state":"TX","lat":29.7604,"lng":-95.3698,"phone":"713-223-3700","website":"https://www.houstonfoodbank.org","services":"Emergency food · Mobile pantry · SNAP enrollment","category":"food"},
    {"name":"Capital Area Food Bank","city":"Washington","state":"DC","lat":38.9072,"lng":-77.0369,"phone":"202-526-5344","website":"https://www.capitalareafoodbank.org","services":"Emergency food · Community pantry · Children's programs","category":"food"},
    {"name":"Atlanta Community Food Bank","city":"Atlanta","state":"GA","lat":33.7490,"lng":-84.3880,"phone":"404-892-9822","website":"https://www.acfb.org","services":"Emergency food · Pantry network · Mobile distribution","category":"food"},
    {"name":"Second Harvest Food Bank — San Jose","city":"San Jose","state":"CA","lat":37.3382,"lng":-121.8863,"phone":"408-266-8866","website":"https://www.shfb.org","services":"Emergency food · Mobile pantry · Senior programs","category":"food"},
    {"name":"Feeding Tampa Bay","city":"Tampa","state":"FL","lat":27.9506,"lng":-82.4572,"phone":"813-254-1190","website":"https://feedingtampabay.org","services":"Emergency food · Community pantry · Mobile distribution","category":"food"},
    {"name":"Denver Food Rescue","city":"Denver","state":"CO","lat":39.7392,"lng":-104.9903,"phone":"303-355-2575","website":"https://www.foodrescue.us","services":"Free food · No paperwork required · Bike delivery available","category":"food"},
    {"name":"Seattle's Table","city":"Seattle","state":"WA","lat":47.6062,"lng":-122.3321,"phone":"206-448-5767","website":"https://www.seattlestable.org","services":"Emergency food · Restaurant surplus · Community meals","category":"food"},
    {"name":"St. Anthony Foundation","city":"San Francisco","state":"CA","lat":37.7749,"lng":-122.4194,"phone":"415-241-2600","website":"https://www.stanthonysf.org","services":"Free meals · Food pantry · Social services","category":"food"},
    {"name":"Boston Food Bank","city":"Boston","state":"MA","lat":42.3601,"lng":-71.0589,"phone":"617-427-5800","website":"https://www.gbfb.org","services":"Emergency food · Pantry network · Mobile distribution","category":"food"},
    {"name":"Phoenix Rescue Mission","city":"Phoenix","state":"AZ","lat":33.4484,"lng":-112.0740,"phone":"602-346-3000","website":"https://www.phoenixrescuemission.org","services":"Free meals · Emergency food · Social services","category":"food"},
    {"name":"Minnesota Food Bank","city":"Minneapolis","state":"MN","lat":44.9778,"lng":-93.2650,"phone":"612-870-5400","website":"https://www.mnfoodbank.org","services":"Emergency food · Pantry network · Mobile distribution","category":"food"},
    {"name":"Oregon Food Bank","city":"Portland","state":"OR","lat":45.5051,"lng":-122.6750,"phone":"503-282-0555","website":"https://www.oregonfoodbank.org","services":"Emergency food · Pantry network · SNAP enrollment","category":"food"},
]

def seed_food_pantries():
    print("\n[FOOD] Seeding food pantries...")
    session = Session()
    saved = 0
    try:
        for loc in FOOD_PANTRIES:
            loc["source"]   = "Feeding America network · Public records"
            loc["verified"] = True
            if save_resource(session, loc):
                saved += 1
                print(f"  ✓ {loc['name']}")
    finally:
        session.close()
    print(f"[FOOD] Done — {saved} locations saved.")
    return saved
# ── Legal aid ─────────────────────────────────────────────────────────────────

LEGAL_AID = [
    {"name":"Legal Aid Society of New York","city":"New York","state":"NY","lat":40.7128,"lng":-74.0059,"phone":"212-577-3300","website":"https://www.legalaidnyc.org","services":"Free civil legal services · Immigration · Housing · Family law","category":"legal"},
    {"name":"Bet Tzedek Legal Services","city":"Los Angeles","state":"CA","lat":34.0522,"lng":-118.2437,"phone":"323-939-0506","website":"https://www.bettzedek.org","services":"Free legal aid · Elder law · Immigration · Housing","category":"legal"},
    {"name":"Chicago Legal Clinic","city":"Chicago","state":"IL","lat":41.8781,"lng":-87.6298,"phone":"773-731-1762","website":"https://www.clclaw.org","services":"Free legal services · Housing · Family law · Employment","category":"legal"},
    {"name":"Houston Volunteer Lawyers","city":"Houston","state":"TX","lat":29.7604,"lng":-95.3698,"phone":"713-228-0732","website":"https://www.hvlp.org","services":"Pro bono legal services · Family law · Immigration · Housing","category":"legal"},
    {"name":"DC Bar Pro Bono Center","city":"Washington","state":"DC","lat":38.9072,"lng":-77.0369,"phone":"202-737-4700","website":"https://www.lawhelp.org/dc","services":"Free legal help · Housing · Immigration · Family law","category":"legal"},
    {"name":"Bay Area Legal Aid","city":"San Francisco","state":"CA","lat":37.7749,"lng":-122.4194,"phone":"415-982-1300","website":"https://baylegal.org","services":"Free civil legal services · Housing · Immigration · Benefits","category":"legal"},
    {"name":"Atlanta Legal Aid Society","city":"Atlanta","state":"GA","lat":33.7490,"lng":-84.3880,"phone":"404-524-5811","website":"https://atlantalegalaid.org","services":"Free civil legal services · Housing · Family · Immigration","category":"legal"},
    {"name":"Northwest Justice Project","city":"Seattle","state":"WA","lat":47.6062,"lng":-122.3321,"phone":"206-464-1519","website":"https://nwjustice.org","services":"Free legal aid · Housing · Family law · Immigration","category":"legal"},
    {"name":"Community Legal Services Philadelphia","city":"Philadelphia","state":"PA","lat":39.9526,"lng":-75.1652,"phone":"215-981-3700","website":"https://clsphila.org","services":"Free civil legal services · Housing · Benefits · Immigration","category":"legal"},
    {"name":"Legal Aid of Colorado","city":"Denver","state":"CO","lat":39.7392,"lng":-104.9903,"phone":"303-837-1313","website":"https://legalaidco.org","services":"Free legal services · Housing · Family · Immigration","category":"legal"},
]

def seed_legal_aid():
    print("\n[LEGAL] Seeding legal aid organizations...")
    session = Session()
    saved = 0
    try:
        for loc in LEGAL_AID:
            loc["source"]   = "Legal Services Corporation · Public records"
            loc["verified"] = True
            if save_resource(session, loc):
                saved += 1
                print(f"  ✓ {loc['name']}")
    finally:
        session.close()
    print(f"[LEGAL] Done — {saved} locations saved.")
    return saved
# ── LGBTQ+ resources ──────────────────────────────────────────────────────────

LGBTQ = [
    {"name":"The Trevor Project — Crisis Line","city":"Los Angeles","state":"CA","lat":34.0522,"lng":-118.2437,"phone":"1-866-488-7386","website":"https://www.thetrevorproject.org","services":"24/7 crisis support for LGBTQ+ youth · Text START to 678-678","category":"lgbtq"},
    {"name":"NYC LGBT Community Center","city":"New York","state":"NY","lat":40.7335,"lng":-74.0027,"phone":"212-620-7310","website":"https://gaycenter.org","services":"Mental health · Support groups · Legal aid · Food pantry · Housing","category":"lgbtq"},
    {"name":"The Center — Los Angeles","city":"Los Angeles","state":"CA","lat":34.0983,"lng":-118.3461,"phone":"323-993-7400","website":"https://thecenterla.org","services":"Health services · Mental health · Support groups · Legal aid","category":"lgbtq"},
    {"name":"Howard Brown Health","city":"Chicago","state":"IL","lat":41.9484,"lng":-87.6553,"phone":"773-388-1600","website":"https://howardbrown.org","services":"Primary care · Mental health · Trans health · HIV services","category":"lgbtq"},
    {"name":"Montrose Center","city":"Houston","state":"TX","lat":29.7498,"lng":-95.3843,"phone":"713-529-0037","website":"https://montrosecenter.org","services":"Mental health · Support groups · Substance abuse · Legal aid","category":"lgbtq"},
    {"name":"Seattle LGBT Community Center","city":"Seattle","state":"WA","lat":47.6101,"lng":-122.3344,"phone":"206-323-4270","website":"https://seattlelgbtcenter.org","services":"Support groups · Mental health · Community programs","category":"lgbtq"},
    {"name":"Fenway Health","city":"Boston","state":"MA","lat":42.3467,"lng":-71.0972,"phone":"617-267-0900","website":"https://fenwayhealth.org","services":"Primary care · Mental health · Trans health · HIV services","category":"lgbtq"},
    {"name":"Atlanta Volunteer Lawyers Foundation — LGBTQ","city":"Atlanta","state":"GA","lat":33.7490,"lng":-84.3880,"phone":"404-521-0790","website":"https://avlf.org","services":"Free legal services for LGBTQ+ individuals","category":"lgbtq"},
    {"name":"National Center for Transgender Equality","city":"Washington","state":"DC","lat":38.9072,"lng":-77.0369,"phone":"202-903-0112","website":"https://transequality.org","services":"Legal advocacy · Know your rights resources · ID document help","category":"lgbtq"},
    {"name":"Q Center — Portland","city":"Portland","state":"OR","lat":45.5231,"lng":-122.6765,"phone":"503-234-7837","website":"https://pdxqcenter.org","services":"Support groups · Mental health · Community programs · Trans resources","category":"lgbtq"},
]

def seed_lgbtq():
    print("\n[LGBTQ+] Seeding LGBTQ+ resources...")
    session = Session()
    saved = 0
    try:
        for loc in LGBTQ:
            loc["source"]   = "Public records · Organization websites"
            loc["verified"] = True
            if save_resource(session, loc):
                saved += 1
                print(f"  ✓ {loc['name']}")
    finally:
        session.close()
    print(f"[LGBTQ+] Done — {saved} locations saved.")
    return saved
# ── Unhoused services ─────────────────────────────────────────────────────────

UNHOUSED = [
    {"name":"Coalition for the Homeless — NYC","city":"New York","state":"NY","lat":40.7128,"lng":-74.0059,"phone":"212-776-2000","website":"https://www.coalitionforthehomeless.org","services":"Emergency shelter · Meals · Case management · Housing placement","category":"unhoused"},
    {"name":"LA Mission","city":"Los Angeles","state":"CA","lat":34.0484,"lng":-118.2369,"phone":"213-629-1227","website":"https://www.lamission.org","services":"Emergency shelter · Meals · Showers · Laundry · Recovery programs","category":"unhoused"},
    {"name":"Pacific Garden Mission","city":"Chicago","state":"IL","lat":41.8742,"lng":-87.6272,"phone":"312-492-9410","website":"https://www.pgm.org","services":"Emergency shelter · Meals · Showers · Case management","category":"unhoused"},
    {"name":"Star of Hope Mission","city":"Houston","state":"TX","lat":29.7514,"lng":-95.3594,"phone":"713-748-0700","website":"https://www.sohmission.org","services":"Emergency shelter · Meals · Showers · Job training","category":"unhoused"},
    {"name":"Central Union Mission","city":"Washington","state":"DC","lat":38.9014,"lng":-77.0177,"phone":"202-745-7118","website":"https://www.missiondc.org","services":"Emergency shelter · Meals · Showers · Case management","category":"unhoused"},
    {"name":"Atlanta Mission","city":"Atlanta","state":"GA","lat":33.7540,"lng":-84.3963,"phone":"404-367-7788","website":"https://www.atlantamission.org","services":"Emergency shelter · Meals · Showers · Recovery programs","category":"unhoused"},
    {"name":"Union Gospel Mission — Seattle","city":"Seattle","state":"WA","lat":47.6022,"lng":-122.3285,"phone":"206-723-0767","website":"https://www.ugm.org","services":"Emergency shelter · Meals · Showers · Medical clinic · Job training","category":"unhoused"},
    {"name":"Denver Rescue Mission","city":"Denver","state":"CO","lat":39.7553,"lng":-104.9848,"phone":"303-297-1815","website":"https://www.denverrescuemission.org","services":"Emergency shelter · Meals · Showers · Case management","category":"unhoused"},
    {"name":"Tenderloin Housing Clinic","city":"San Francisco","state":"CA","lat":37.7836,"lng":-122.4131,"phone":"415-771-9850","website":"https://www.thclinic.org","services":"Free legal services for unhoused · Housing advocacy","category":"unhoused"},
    {"name":"Phoenix Rescue Mission","city":"Phoenix","state":"AZ","lat":33.4679,"lng":-112.0631,"phone":"602-346-3000","website":"https://www.phoenixrescuemission.org","services":"Emergency shelter · Meals · Showers · Recovery · Job training","category":"unhoused"},
    {"name":"Transition Projects — Portland","city":"Portland","state":"OR","lat":45.5228,"lng":-122.6808,"phone":"503-280-4744","website":"https://tprojects.org","services":"Emergency shelter · Housing placement · Case management · Meals","category":"unhoused"},
    {"name":"Minneapolis Salvation Army Harbor Lights","city":"Minneapolis","state":"MN","lat":44.9746,"lng":-93.2588,"phone":"612-338-0113","website":"https://centralusa.salvationarmy.org","services":"Emergency shelter · Meals · Showers · Case management","category":"unhoused"},
]

def seed_unhoused():
    print("\n[UNHOUSED] Seeding unhoused services...")
    session = Session()
    saved = 0
    try:
        for loc in UNHOUSED:
            loc["source"]   = "Public records · Organization websites"
            loc["verified"] = True
            if save_resource(session, loc):
                saved += 1
                print(f"  ✓ {loc['name']}")
    finally:
        session.close()
    print(f"[UNHOUSED] Done — {saved} locations saved.")
    return saved
# ── Run all ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("╔══════════════════════════════════════════╗")
    print("║   Gleaning Resources — Seed Script       ║")
    print("║   The harvest was never only theirs.     ║")
    print("╚══════════════════════════════════════════╝")

    total = 0
    total += seed_planned_parenthood()
    total += seed_food_pantries()
    total += seed_legal_aid()
    total += seed_lgbtq()
    total += seed_unhoused()
    total += fetch_hrsa()

    print(f"\n✓ Total resources seeded: {total}")
    print("Refresh the Resources page to see dots on the map.")
