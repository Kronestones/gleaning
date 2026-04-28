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
    total += seed_safe_parking()
    total += seed_housing()
    total += seed_education()
    total += seed_community()
    total += seed_safety()

    print(f"\n✓ Total resources seeded: {total}")
    print("Refresh the Resources page to see dots on the map.")

# ── Safe Parking Programs ─────────────────────────────────────────────────────

SAFE_PARKING = [
    {"name":"Jewish Family Service Safe Parking","city":"San Diego","state":"CA","lat":32.7832,"lng":-117.1500,"phone":"858-637-3373","website":"https://www.jfssd.org/our-services/safe-parking","services":"Safe overnight parking · 5 secured lots · 7 nights/week · Enrollment required · Case management","category":"parking"},
    {"name":"Safe Parking LA","city":"Los Angeles","state":"CA","lat":34.0522,"lng":-118.2437,"phone":"213-389-1500","website":"https://safeparkingla.org","services":"Safe overnight parking · 6 lots · San Fernando Valley · Hollywood · Downtown · West LA · Veterans Administration campus","category":"parking"},
    {"name":"Dreams for Change Safe Parking","city":"San Diego","state":"CA","lat":32.7157,"lng":-117.1611,"phone":"619-344-0027","website":"https://dreamsforchange.org","services":"Safe overnight parking · Referral required · Coordinated entry","category":"parking"},
    {"name":"New Beginnings Safe Parking","city":"Santa Barbara","state":"CA","lat":34.4208,"lng":-119.6982,"phone":"805-963-7777","website":"https://newbeginningscounselingcenter.org","services":"Safe overnight parking · 200+ spaces · 27 lots · Churches and businesses · Rapid rehousing","category":"parking"},
    {"name":"40 Prado Safe Parking","city":"San Luis Obispo","state":"CA","lat":35.2828,"lng":-120.6596,"phone":"805-544-6400","website":"https://capslo.org/safe-parking","services":"Safe overnight parking · 24 spaces · Showers · Meals · Health services · Case management · 6pm-7am","category":"parking"},
    {"name":"Safe Ground Sacramento","city":"Sacramento","state":"CA","lat":38.5816,"lng":-121.4944,"phone":"916-319-9451","website":"https://www.cityofsacramento.org","services":"Safe overnight parking and camping · 24/7 · 60 vehicles · Port-a-potties · Storage · Meal access · Case managers on site","category":"parking"},
    {"name":"HOPICS Safe Parking","city":"Los Angeles","state":"CA","lat":33.9731,"lng":-118.2479,"phone":"323-752-2211","website":"https://www.hopics.org","services":"Safe overnight parking · Single adults and families · Secured space · Showers · Hygiene supplies · Housing support · Walk-ins welcome","category":"parking"},
    {"name":"Long Beach Safe Parking","city":"Long Beach","state":"CA","lat":33.7701,"lng":-118.1937,"phone":"562-570-4500","website":"https://www.longbeach.gov","services":"Safe overnight parking · Multi-Service Center · South Shore Launch Ramp · Dignified environment · Services connection","category":"parking"},
    {"name":"LifeMoves Safe RV Parking","city":"Redwood City","state":"CA","lat":37.4852,"lng":-122.2364,"phone":"650-681-6441","website":"https://www.lifemoves.org","services":"Safe overnight RV parking · Families and individuals · Oversized vehicles welcome","category":"parking"},
    {"name":"Safe Park Indy","city":"Indianapolis","state":"IN","lat":39.7684,"lng":-86.1581,"phone":"317-988-7777","website":"https://www.safeparkindy.org","services":"Safe overnight parking · Faith community lots · Case management · Housing stability services","category":"parking"},
    {"name":"Just Compassion Safe Parking","city":"Bend","state":"OR","lat":44.0582,"lng":-121.3153,"phone":"541-306-6988","website":"https://justcompassion.org","services":"Safe overnight parking · Case management · Services connection","category":"parking"},
    {"name":"Safe Bay Duluth","city":"Duluth","state":"MN","lat":46.7867,"lng":-92.1005,"phone":"218-722-7766","website":"https://www.hrduluth.org","services":"Safe overnight parking · Outreach worker · Housing connection · Seasonal program","category":"parking"},
    {"name":"Seattle Safe Parking — North/West/Central","city":"Seattle","state":"WA","lat":47.6062,"lng":-122.3321,"phone":"206-694-6700","website":"https://www.desc.org","services":"Safe overnight parking · Multiple lots · North · West · Central Seattle","category":"parking"},
    {"name":"Pierce County Safe Parking","city":"Tacoma","state":"WA","lat":47.2529,"lng":-122.4443,"phone":"253-798-4455","website":"https://www.co.pierce.wa.us","services":"Safe overnight parking · Portable toilets · Hand washing · Garbage · Outreach · Individuals · Couples · Families","category":"parking"},
    {"name":"Alameda County Safe Parking","city":"San Leandro","state":"CA","lat":37.7249,"lng":-122.1561,"phone":"510-593-4660","website":"https://www.achch.org","services":"Safe overnight parking · 24 hour program · Fairmont Campus · Day and night parking · Services connection","category":"parking"},
]

def seed_safe_parking():
    print("\n[PARKING] Seeding safe parking programs...")
    session = Session()
    saved = 0
    try:
        for loc in SAFE_PARKING:
            loc["source"]   = "National Vehicle Residency Collective · vehicleresidency.org · Public records"
            loc["verified"] = True
            if save_resource(session, loc):
                saved += 1
                print(f"  ✓ {loc['name']}")
    finally:
        session.close()
    print(f"[PARKING] Done — {saved} locations saved.")
    return saved

# ── Housing & Shelters ────────────────────────────────────────────────────────

HOUSING = [
    {"name":"National Domestic Violence Hotline","city":"Austin","state":"TX","lat":30.2672,"lng":-97.7431,"phone":"1-800-799-7233","website":"https://www.thehotline.org","services":"24/7 crisis support · Safety planning · Shelter referrals · Chat available","category":"housing"},
    {"name":"New York City shelter system","city":"New York","state":"NY","lat":40.7128,"lng":-74.0059,"phone":"311","website":"https://www.nyc.gov/shelter","services":"Emergency shelter · Families · Singles · Veterans · LGBTQ+ specific shelters","category":"housing"},
    {"name":"LA Family Housing","city":"Los Angeles","state":"CA","lat":34.1867,"lng":-118.3801,"phone":"818-982-7460","website":"https://lafh.org","services":"Emergency shelter · Transitional housing · Rapid rehousing · Case management","category":"housing"},
    {"name":"Chicago Housing Authority Emergency","city":"Chicago","state":"IL","lat":41.8781,"lng":-87.6298,"phone":"312-742-8500","website":"https://www.thecha.org","services":"Emergency housing · Transitional shelter · Case management","category":"housing"},
    {"name":"Covenant House — New York","city":"New York","state":"NY","lat":40.7614,"lng":-74.0013,"phone":"212-727-4000","website":"https://www.covenanthouse.org","services":"Youth shelter · Ages 16-24 · Meals · Education · Job training · LGBTQ+ affirming","category":"housing"},
    {"name":"Covenant House — Los Angeles","city":"Los Angeles","state":"CA","lat":34.0983,"lng":-118.3273,"phone":"323-461-3131","website":"https://www.covenanthouselosangeles.org","services":"Youth shelter · Ages 18-24 · Meals · Education · Job training · LGBTQ+ affirming","category":"housing"},
    {"name":"YW Boston — Women's Shelter","city":"Boston","state":"MA","lat":42.3467,"lng":-71.0697,"phone":"617-351-1100","website":"https://www.ywboston.org","services":"Women only · Emergency shelter · Case management · Legal advocacy","category":"housing"},
    {"name":"SafeHaven of Tarrant County","city":"Fort Worth","state":"TX","lat":32.7555,"lng":-97.3308,"phone":"877-701-7233","website":"https://www.safehaventc.org","services":"DV shelter · Women and children · Legal advocacy · Counseling · Housing assistance","category":"housing"},
    {"name":"House of Ruth Maryland","city":"Baltimore","state":"MD","lat":39.2904,"lng":-76.6122,"phone":"410-889-7884","website":"https://hruth.org","services":"DV shelter · Women only · Legal services · Economic empowerment · Children's programs","category":"housing"},
    {"name":"Rosie's Place — Women's Shelter","city":"Boston","state":"MA","lat":42.3354,"lng":-71.0636,"phone":"617-442-9322","website":"https://rosiesplace.org","services":"Women only · Emergency shelter · Meals · Legal aid · Job training · No ID required","category":"housing"},
    {"name":"Denver Human Services Emergency","city":"Denver","state":"CO","lat":39.7392,"lng":-104.9903,"phone":"720-944-3666","website":"https://www.denvergov.org/shelter","services":"Emergency shelter · Families · Singles · Case management","category":"housing"},
    {"name":"Houston Area Women's Center","city":"Houston","state":"TX","lat":29.7372,"lng":-95.4152,"phone":"713-528-6798","website":"https://hawc.org","services":"DV and sexual assault shelter · Women and children · Legal advocacy · Counseling","category":"housing"},
]

def seed_housing():
    print("\n[HOUSING] Seeding housing and shelter resources...")
    session = Session()
    saved = 0
    try:
        for loc in HOUSING:
            loc["source"]   = "Public records · Organization websites"
            loc["verified"] = True
            if save_resource(session, loc):
                saved += 1
                print(f"  ✓ {loc['name']}")
    finally:
        session.close()
    print(f"[HOUSING] Done — {saved} saved.")
    return saved

# ── Education ─────────────────────────────────────────────────────────────────

EDUCATION = [
    {"name":"New York Public Library — Free Programs","city":"New York","state":"NY","lat":40.7532,"lng":-73.9822,"phone":"917-275-6975","website":"https://www.nypl.org","services":"Free internet · English classes · GED prep · Job training · Citizenship classes · Computer access","category":"education"},
    {"name":"Los Angeles Public Library","city":"Los Angeles","state":"CA","lat":34.0497,"lng":-118.2534,"phone":"213-228-7000","website":"https://www.lapl.org","services":"Free internet · English classes · GED prep · Job training · Citizenship classes · Computer access","category":"education"},
    {"name":"Chicago Public Library","city":"Chicago","state":"IL","lat":41.8731,"lng":-87.6284,"phone":"312-747-4300","website":"https://www.chipublib.org","services":"Free internet · English classes · GED prep · Job training · Computer access · Free hotspot lending","category":"education"},
    {"name":"Houston Public Library","city":"Houston","state":"TX","lat":29.7530,"lng":-95.3677,"phone":"832-393-1313","website":"https://houstonlibrary.org","services":"Free internet · English classes · GED prep · Job training · Computer access","category":"education"},
    {"name":"Free Library of Philadelphia","city":"Philadelphia","state":"PA","lat":39.9580,"lng":-75.1727,"phone":"215-686-5322","website":"https://www.freelibrary.org","services":"Free internet · English classes · GED prep · Computer access · Job resources","category":"education"},
    {"name":"San Francisco Public Library","city":"San Francisco","state":"CA","lat":37.7788,"lng":-122.4156,"phone":"415-557-4400","website":"https://sfpl.org","services":"Free internet · English classes · GED prep · Computer access · Social worker on staff","category":"education"},
    {"name":"Literacy Partners — NYC","city":"New York","state":"NY","lat":40.7128,"lng":-74.0059,"phone":"212-944-9840","website":"https://literacypartners.org","services":"Free adult literacy · English classes · GED prep · One-on-one tutoring","category":"education"},
    {"name":"ProLiteracy — National Network","city":"Syracuse","state":"NY","lat":43.0481,"lng":-76.1474,"phone":"315-422-9121","website":"https://proliteracy.org","services":"Free adult literacy programs · Find local programs nationwide · English as second language","category":"education"},
    {"name":"National Education Association — Free Resources","city":"Washington","state":"DC","lat":38.9072,"lng":-77.0369,"phone":"202-833-4000","website":"https://www.nea.org","services":"Free educational resources · Find local programs · Adult education referrals","category":"education"},
    {"name":"Khan Academy — Free Online Education","city":"Mountain View","state":"CA","lat":37.3861,"lng":-122.0839,"phone":"","website":"https://www.khanacademy.org","services":"Free online education · K-12 · GED prep · SAT prep · College courses · No cost ever","category":"education"},
    {"name":"Seattle Public Library","city":"Seattle","state":"WA","lat":47.6064,"lng":-122.3329,"phone":"206-386-4636","website":"https://www.spl.org","services":"Free internet · English classes · GED prep · Computer access · Job resources · Free hotspot lending","category":"education"},
    {"name":"Denver Public Library","city":"Denver","state":"CO","lat":39.7316,"lng":-104.9877,"phone":"720-865-1111","website":"https://www.denverlibrary.org","services":"Free internet · English classes · GED prep · Computer access · Social worker on staff","category":"education"},
]

def seed_education():
    print("\n[EDUCATION] Seeding education resources...")
    session = Session()
    saved = 0
    try:
        for loc in EDUCATION:
            loc["source"]   = "Public records · Organization websites"
            loc["verified"] = True
            if save_resource(session, loc):
                saved += 1
                print(f"  ✓ {loc['name']}")
    finally:
        session.close()
    print(f"[EDUCATION] Done — {saved} saved.")
    return saved

# ── Community ─────────────────────────────────────────────────────────────────

COMMUNITY = [
    {"name":"NAACP — National Headquarters","city":"Baltimore","state":"MD","lat":39.2904,"lng":-76.6122,"phone":"410-580-5777","website":"https://naacp.org","services":"Civil rights advocacy · Legal referrals · Find local chapter · Voting rights · Community programs","category":"community"},
    {"name":"ACLU — National Office","city":"New York","state":"NY","lat":40.7306,"lng":-74.0031,"phone":"212-549-2500","website":"https://www.aclu.org","services":"Free legal advocacy · Civil rights · Find local affiliate · Know your rights resources","category":"community"},
    {"name":"Urban League — National","city":"New York","state":"NY","lat":40.8076,"lng":-73.9454,"phone":"212-558-5300","website":"https://nul.org","services":"Job training · Housing assistance · Education · Find local affiliate","category":"community"},
    {"name":"National Council of La Raza — UnidosUS","city":"Washington","state":"DC","lat":38.9072,"lng":-77.0369,"phone":"202-785-1670","website":"https://www.unidosus.org","services":"Latino civil rights · Education · Health · Housing · Find local affiliate","category":"community"},
    {"name":"Black Lives Matter — Resources","city":"Los Angeles","state":"CA","lat":34.0522,"lng":-118.2437,"phone":"","website":"https://blacklivesmatter.com","services":"Community resources · Know your rights · Find local chapter · Mutual aid network","category":"community"},
    {"name":"National Indigenous Women's Resource Center","city":"Lame Deer","state":"MT","lat":45.6280,"lng":-106.6558,"phone":"406-477-3896","website":"https://www.niwrc.org","services":"MMIW resources · DV advocacy · Legal referrals · Tribal programs · Safety planning","category":"community"},
    {"name":"Western Service Workers Association","city":"Los Angeles","state":"CA","lat":34.0522,"lng":-118.2437,"phone":"323-733-9779","website":"https://wswa.org","services":"Worker rights · Benefits access · Food assistance · Housing referrals · Community programs","category":"community"},
    {"name":"National Alliance on Mental Illness","city":"Arlington","state":"VA","lat":38.8799,"lng":-77.1068,"phone":"1-800-950-6264","website":"https://www.nami.org","services":"Free mental health support · Helpline · Find local chapter · Support groups · No cost peer programs","category":"community"},
    {"name":"Feeding America — Find Your Food Bank","city":"Chicago","state":"IL","lat":41.8781,"lng":-87.6298,"phone":"800-771-2303","website":"https://www.feedingamerica.org/find-your-local-foodbank","services":"Find local food bank · Emergency food · SNAP enrollment · 200 food banks nationwide","category":"community"},
    {"name":"211 — National Helpline","city":"Atlanta","state":"GA","lat":33.7490,"lng":-84.3880,"phone":"211","website":"https://www.211.org","services":"Free referral service · Food · Housing · Utilities · Health · 24/7 · All states · English and Spanish","category":"community"},
    {"name":"Salvation Army — National","city":"Alexandria","state":"VA","lat":38.8048,"lng":-77.0469,"phone":"703-684-5500","website":"https://www.salvationarmyusa.org","services":"Emergency assistance · Food · Shelter · Clothing · Disaster relief · Find local center","category":"community"},
    {"name":"Catholic Charities USA","city":"Alexandria","state":"VA","lat":38.8048,"lng":-77.0469,"phone":"703-549-1390","website":"https://www.catholiccharitiesusa.org","services":"Food · Shelter · Immigration · Refugee services · No religion required · Find local office","category":"community"},
    {"name":"Islamic Society of North America","city":"Plainfield","state":"IN","lat":39.6953,"lng":-86.3633,"phone":"317-839-8157","website":"https://www.isna.net","services":"Find local mosque · Community services · Food assistance · Refugee support · No religion required","category":"community"},
]

def seed_community():
    print("\n[COMMUNITY] Seeding community resources...")
    session = Session()
    saved = 0
    try:
        for loc in COMMUNITY:
            loc["source"]   = "Public records · Organization websites"
            loc["verified"] = True
            if save_resource(session, loc):
                saved += 1
                print(f"  ✓ {loc['name']}")
    finally:
        session.close()
    print(f"[COMMUNITY] Done — {saved} saved.")
    return saved

# ── Safety ────────────────────────────────────────────────────────────────────

SAFETY = [
    {"name":"National DV Hotline","city":"Austin","state":"TX","lat":30.2672,"lng":-97.7431,"phone":"1-800-799-7233","website":"https://www.thehotline.org","services":"24/7 crisis line · Safety planning · Shelter referrals · Text BEGIN to 88788 · Chat available","category":"safety"},
    {"name":"RAINN National Sexual Assault Hotline","city":"Washington","state":"DC","lat":38.9072,"lng":-77.0369,"phone":"1-800-656-4673","website":"https://www.rainn.org","services":"24/7 crisis support · Sexual assault · Find local provider · Online chat · Confidential","category":"safety"},
    {"name":"National Center for Victims of Crime","city":"Washington","state":"DC","lat":38.9072,"lng":-77.0369,"phone":"1-855-484-2846","website":"https://victimsofcrime.org","services":"Crime victim resources · Legal referrals · Find local services · Stalking resource center","category":"safety"},
    {"name":"Safe Horizon — New York","city":"New York","state":"NY","lat":40.7128,"lng":-74.0059,"phone":"212-577-7777","website":"https://www.safehorizon.org","services":"DV · Sexual assault · Stalking · Human trafficking · Legal advocacy · Shelter referrals","category":"safety"},
    {"name":"Futures Without Violence","city":"San Francisco","state":"CA","lat":37.7749,"lng":-122.4194,"phone":"415-252-8900","website":"https://www.futureswithoutviolence.org","services":"DV prevention · Health care resources · Find local programs · Training and education","category":"safety"},
    {"name":"National Network to End Domestic Violence","city":"Washington","state":"DC","lat":38.9072,"lng":-77.0369,"phone":"202-543-5566","website":"https://nnedv.org","services":"DV advocacy · Safety Net tech safety · Find local coalition · Policy and legal resources","category":"safety"},
    {"name":"Asian Pacific Islander DV Resource Project","city":"Washington","state":"DC","lat":38.9072,"lng":-77.0369,"phone":"202-464-4477","website":"https://www.dvrp.org","services":"DV resources for API communities · Bilingual services · Find local programs","category":"safety"},
    {"name":"StrongHearts Native Helpline","city":"","state":"","lat":44.9778,"lng":-93.2650,"phone":"1-844-762-8483","website":"https://www.strongheartshelpline.org","services":"24/7 DV and sexual assault helpline · Indigenous specific · Culturally appropriate · Confidential","category":"safety"},
    {"name":"Trans Lifeline","city":"","state":"","lat":37.7749,"lng":-122.4194,"phone":"877-565-8860","website":"https://translifeline.org","services":"24/7 crisis hotline · Trans people · Staffed by trans people · Peer support · Document name change help","category":"safety"},
    {"name":"Crisis Text Line","city":"New York","state":"NY","lat":40.7128,"lng":-74.0059,"phone":"Text HOME to 741741","website":"https://www.crisistextline.org","services":"24/7 text crisis support · Free · All issues · Confidential · Connect with trained counselor","category":"safety"},
]

def seed_safety():
    print("\n[SAFETY] Seeding safety resources...")
    session = Session()
    saved = 0
    try:
        for loc in SAFETY:
            loc["source"]   = "Public records · Organization websites"
            loc["verified"] = True
            if save_resource(session, loc):
                saved += 1
                print(f"  ✓ {loc['name']}")
    finally:
        session.close()
    print(f"[SAFETY] Done — {saved} saved.")
    return saved
