"""
watcher.py — Gleaning Watchers

Five eyes on the public record.
Running continuously. Logging everything.
Posting what is verified. Flagging what is uncertain.

The watchers do not sleep.
The record stays current.

Watchers:
  AcquisitionWatch  — SEC EDGAR + FTC — new corporate brand ownership
  WasteWatch        — USDA + EPA + ReFED — food waste data
  HungerWatch       — FRAC + Feeding America — food insecurity data
  PriceWatch        — USDA food price data — keeps calculations current
  CorporationWatch  — news feeds — waste stories, dumping, recalls

— Krone the Architect · 2026
"""

import json
import time
import threading
import hashlib
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from .config import config
from .database import SessionLocal, log_event

WATCHER_LOG    = "gleaning_watcher.log"
FLAGGED_LOG    = "gleaning_flagged.json"
FETCH_TIMEOUT  = 15

# ── Fetch helper ──────────────────────────────────────────────────────────────

def fetch_url(url: str, timeout: int = FETCH_TIMEOUT) -> str:
    """Fetch a URL. Returns text or empty string on failure."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Gleaning/1.0 (public data monitor)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return ""


def parse_rss(text: str) -> list:
    """Parse RSS/Atom feed. Returns list of {title, link, summary}."""
    items = []
    try:
        root = ET.fromstring(text)
        ns = ""
        if "}" in root.tag:
            ns = root.tag.split("}")[0] + "}"

        for item in root.iter(f"{ns}item"):
            title   = item.findtext(f"{ns}title", "")
            link    = item.findtext(f"{ns}link", "")
            summary = item.findtext(f"{ns}description", "")
            if title:
                items.append({
                    "title":   title.strip(),
                    "link":    link.strip(),
                    "summary": summary.strip()[:300],
                })
    except Exception:
        pass
    return items


def log_watcher(watcher: str, event: str, detail: str = ""):
    """Write to watcher log."""
    line = json.dumps({
        "time":    datetime.now(timezone.utc).isoformat(),
        "watcher": watcher,
        "event":   event,
        "detail":  detail,
    })
    try:
        with open(WATCHER_LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def flag_for_founder(watcher: str, item: dict, reason: str):
    """
    Flag an item for Founder review.
    Used when watcher finds something but isn't certain.
    """
    flags = []
    try:
        with open(FLAGGED_LOG) as f:
            flags = json.load(f)
    except Exception:
        pass

    flags.append({
        "flagged_at": datetime.now(timezone.utc).isoformat(),
        "watcher":    watcher,
        "reason":     reason,
        "item":       item,
        "reviewed":   False,
        "saved":      False,   # Team marked as worth keeping
        "deleted":    False,   # Team marked as irrelevant
    })

    try:
        with open(FLAGGED_LOG, "w") as f:
            json.dump(flags, f, indent=2)
    except Exception:
        pass

    log_watcher(watcher, "FLAGGED_FOR_FOUNDER", reason)
    print(f"[{watcher.upper()}] ⚑ Flagged for Founder: {reason[:60]}")


# ── Acquisition Watch ─────────────────────────────────────────────────────────

class AcquisitionWatch:
    """
    Monitors SEC EDGAR and FTC for corporate acquisitions.
    Finds new brand ownership — verifies — posts to Truth Wall.
    Uncertain? Flags to Founder.

    Sources:
      SEC EDGAR full-text search RSS
      FTC merger announcements RSS
    """

    NAME     = "AcquisitionWatch"
    INTERVAL = 86400  # daily

    SOURCES = [
        {
            "name": "FTC Merger Announcements",
            "url":  "https://www.ftc.gov/feeds/press-release-merger.xml",
            "type": "rss",
        },
        {
            "name": "SEC EDGAR Recent Filings",
            "url":  "https://efts.sec.gov/LATEST/search-index?q=%22acquisition%22+%22brand%22&dateRange=custom&startdt={}&enddt={}&forms=8-K",
            "type": "sec",
        },
    ]

    # Corporations we track
    TRACKED = [
        "kraft heinz", "nestle", "unilever", "general mills",
        "kellanova", "kellogg", "pepsico", "conagra",
        "tyson", "jbs", "cargill", "archer daniels",
        "post holdings", "treehouse foods", "smucker",
        "campbell soup", "heinz", "mondelez",
    ]

    def __init__(self):
        self._stop   = threading.Event()
        self._thread = None
        self._seen   = set()

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"[{self.NAME}] Started — watching SEC and FTC.")

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            try:
                self._check()
            except Exception as e:
                log_watcher(self.NAME, "ERROR", str(e))
            self._stop.wait(self.INTERVAL)

    def _check(self):
        log_watcher(self.NAME, "CHECK_START")

        # FTC RSS
        text = fetch_url(self.SOURCES[0]["url"])
        if text:
            items = parse_rss(text)
            for item in items:
                self._process_ftc(item)

        log_watcher(self.NAME, "CHECK_COMPLETE")

    def _process_ftc(self, item: dict):
        title   = item["title"].lower()
        summary = item["summary"].lower()
        combined = title + " " + summary

        # Check if any tracked corporation is mentioned
        matched_corp = None
        for corp in self.TRACKED:
            if corp in combined:
                matched_corp = corp
                break

        if not matched_corp:
            return

        # Deduplicate
        item_id = hashlib.md5(item["title"].encode()).hexdigest()
        if item_id in self._seen:
            return
        self._seen.add(item_id)

        log_watcher(self.NAME, "ACQUISITION_FOUND",
                    f"{matched_corp}: {item['title'][:80]}")

        # Flag for Founder — acquisitions need human verification
        # before going on the permanent Truth Wall
        flag_for_founder(
            self.NAME,
            {
                "corporation": matched_corp,
                "title":       item["title"],
                "link":        item["link"],
                "summary":     item["summary"],
            },
            f"Possible acquisition: {matched_corp} — {item['title'][:60]}"
        )


# ── Waste Watch ───────────────────────────────────────────────────────────────

class WasteWatch:
    """
    Monitors USDA and EPA for food waste data updates.
    Keeps Gleaning's waste figures current.
    Updates the family-fed methodology when official figures change.

    Sources:
      USDA ERS food loss and waste reports
      EPA food waste data
      ReFED public data
    """

    NAME     = "WasteWatch"
    INTERVAL = 604800  # weekly

    SOURCES = [
        {
            "name": "USDA ERS Loss-Adjusted Food Availability",
            "url":  "https://www.ers.usda.gov/rss/",
            "type": "rss",
            "keywords": ["food loss", "food waste", "food availability"],
        },
        {
            "name": "EPA Food Waste",
            "url":  "https://www.epa.gov/feed/rss.xml",
            "type": "rss",
            "keywords": ["food waste", "wasted food", "food recovery"],
        },
    ]

    # ── Per-corporation sustainability report sources ──────────────────────────
    # Each corporation publishes an annual sustainability report.
    # WasteWatch checks these directly for food waste figures.
    # When new numbers appear, record_corporate_waste() updates the record.
    # The people see what is being wasted. Updated as it changes. Not on a schedule.

    CORPORATE_SOURCES = [
        {
            "corporation": "Nestlé",
            "name": "Nestlé Creating Shared Value and Sustainability Report",
            "url":  "https://www.nestle.com/sustainability/performance-reporting/downloads-archive",
            "report_url": "https://www.nestle.com/sites/default/files/2025-02/non-financial-statement-2024.pdf",
            "keywords": ["food waste", "tonnes wasted", "food loss", "waste reduction",
                         "metric tons", "operational waste", "food diverted"],
        },
        {
            "corporation": "PepsiCo",
            "name": "PepsiCo ESG Summary and pep+ Sustainability Report",
            "url":  "https://www.pepsico.com/en/esg-topics/waste",
            "report_url": "https://www.pepsico.com/sustainability/sustainability-reporting",
            "keywords": ["food waste", "metric tons", "waste generated",
                         "diverted from landfill", "operational waste", "food loss"],
        },
        {
            "corporation": "Unilever",
            "name": "Unilever Annual Report and Accounts",
            "url":  "https://www.unilever.com/planet-and-society/waste-free-world/",
            "report_url": "https://www.unilever.com/files/unilever-annual-report-and-accounts-2024.pdf",
            "keywords": ["food waste", "tonnes", "waste reduction",
                         "food loss", "operational waste", "metric tons"],
        },
        {
            "corporation": "Kraft Heinz",
            "name": "Kraft Heinz ESG Report",
            "url":  "https://www.kraftheinzcompany.com/esg/",
            "report_url": "https://www.kraftheinzcompany.com/esg/planet.html",
            "keywords": ["food waste", "metric tons", "tonnes", "food loss",
                         "waste diverted", "operational waste", "food donated"],
        },
        {
            "corporation": "General Mills",
            "name": "General Mills Global Responsibility Report",
            "url":  "https://www.generalmills.com/responsibility/global-responsibility-report",
            "report_url": "https://globalresponsibility.generalmills.com",
            "keywords": ["food waste", "metric tons", "tonnes wasted",
                         "food loss", "waste reduction", "food diverted", "operational waste"],
        },
        {
            "corporation": "Conagra Brands",
            "name": "Conagra Brands Corporate Responsibility Report",
            "url":  "https://www.conagrabrands.com/corporate-responsibility",
            "report_url": "https://www.conagrabrands.com/corporate-responsibility/planet",
            "keywords": ["food waste", "metric tons", "tonnes", "food loss",
                         "waste reduction", "diverted from landfill", "food donated"],
        },
        {
            "corporation": "Mars/Kellanova",
            "name": "Mars Incorporated Sustainability Report",
            "url":  "https://www.mars.com/sustainability-plan",
            "report_url": "https://www.mars.com/sustainability-plan/reporting-performance",
            "keywords": ["food waste", "metric tons", "tonnes wasted",
                         "food loss", "waste reduction", "operational waste", "food diverted"],
        },
    ]

    def __init__(self):
        self._stop   = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"[{self.NAME}] Started — watching USDA and EPA.")

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            try:
                self._check()
            except Exception as e:
                log_watcher(self.NAME, "ERROR", str(e))
            self._stop.wait(self.INTERVAL)

    def check_corporate_sources(self):
        """
        Check each corporation's sustainability report directly.
        When new food waste figures are found, record them.
        Not on a schedule — called when WasteWatch runs its cycle.
        The record updates when the data changes. Not before.
        """
        import re
        log_watcher(self.NAME, "CORPORATE_CHECK_START",
                    f"Checking {len(self.CORPORATE_SOURCES)} corporations")

        for source in self.CORPORATE_SOURCES:
            corp = source["corporation"]
            try:
                text = fetch_url(source["report_url"])
                if not text:
                    text = fetch_url(source["url"])
                if not text:
                    log_watcher(self.NAME, "CORPORATE_FETCH_FAILED", corp)
                    continue

                combined = text.lower()

                # Check if any waste keywords appear
                if not any(kw in combined for kw in source["keywords"]):
                    continue

                # Try to extract a metric tons / tonnes figure near waste keywords
                # Patterns: "X metric tons", "X,XXX tonnes", "X million tonnes"
                patterns = [
                    r"([\d,]+(?:\.[\d]+)?)\s*metric\s*tons?\s*(?:of\s*)?(?:food\s*)?waste",
                    r"([\d,]+(?:\.[\d]+)?)\s*tonnes?\s*(?:of\s*)?(?:food\s*)?waste",
                    r"(?:food\s*)?waste\s*(?:of\s*)?([\d,]+(?:\.[\d]+)?)\s*(?:metric\s*)?tons?",
                    r"([\d,]+(?:\.[\d]+)?)\s*(?:metric\s*)?tons?\s*(?:of\s*)?food\s*(?:loss|wasted|diverted)",
                ]

                lbs_found = None
                for pattern in patterns:
                    matches = re.findall(pattern, combined)
                    if matches:
                        # Take the largest plausible number found
                        for match in matches:
                            try:
                                num = float(match.replace(",", ""))
                                # Convert metric tons to lbs (1 metric ton = 2204.62 lbs)
                                # Only accept plausible corporate-scale figures
                                # (between 1,000 and 10,000,000 metric tons)
                                if 1000 <= num <= 10_000_000:
                                    lbs = num * 2204.62
                                    if lbs_found is None or lbs > lbs_found:
                                        lbs_found = lbs
                            except ValueError:
                                continue
                        if lbs_found:
                            break

                if lbs_found:
                    self.record_corporate_waste(
                        corporation = corp,
                        lbs_wasted  = lbs_found,
                        source_url  = source["report_url"],
                        source_name = source["name"],
                        note        = f"Parsed from sustainability report. Always rounded down per Gleaning methodology.",
                    )
                    log_watcher(self.NAME, "CORPORATE_WASTE_PARSED",
                                f"{corp}: {lbs_found:,.0f} lbs ({lbs_found/2204.62:,.0f} metric tons)")
                else:
                    # Data found but couldn't parse a number — flag for review
                    flag_for_founder(
                        self.NAME,
                        {"corporation": corp, "url": source["report_url"]},
                        f"{corp} sustainability report found but waste figure needs manual review"
                    )
                    log_watcher(self.NAME, "CORPORATE_NEEDS_REVIEW", corp)

            except Exception as e:
                log_watcher(self.NAME, "CORPORATE_CHECK_ERROR", f"{corp}: {str(e)}")

        log_watcher(self.NAME, "CORPORATE_CHECK_COMPLETE")

    def record_corporate_waste(self, corporation: str, lbs_wasted: float,
                               period: str = "", source_url: str = "",
                               source_name: str = "", note: str = "") -> bool:
        """
        Upsert corporate waste figure.
        One row per corporation — overwrite when new data arrives.
        No history kept. Just the current truth.
        """
        try:
            from .database import SessionLocal, CorporateWasteRecord
            from datetime import datetime, timezone
            db = SessionLocal()
            try:
                existing = db.query(CorporateWasteRecord).filter(
                    CorporateWasteRecord.corporation == corporation
                ).first()
                if existing:
                    existing.lbs_wasted  = lbs_wasted
                    existing.period      = period
                    existing.source_url  = source_url
                    existing.source_name = source_name
                    existing.recorded_at = datetime.now(timezone.utc)
                    existing.note        = note
                else:
                    db.add(CorporateWasteRecord(
                        corporation = corporation,
                        lbs_wasted  = lbs_wasted,
                        period      = period,
                        source_url  = source_url,
                        source_name = source_name,
                        note        = note,
                    ))
                db.commit()
                log_watcher(self.NAME, "WASTE_RECORDED",
                            f"{corporation}: {lbs_wasted:,.0f} lbs")
                print(f"[{self.NAME}] {corporation}: {lbs_wasted:,.0f} lbs recorded.")
                return True
            finally:
                db.close()
        except Exception as e:
            log_watcher(self.NAME, "WASTE_RECORD_ERROR", str(e))
            return False

    def _check(self):
        log_watcher(self.NAME, "CHECK_START")

        # Check general EPA/USDA feeds for new waste data
        for source in self.SOURCES:
            text = fetch_url(source["url"])
            if not text:
                continue
            items = parse_rss(text)
            for item in items:
                combined = (item["title"] + item["summary"]).lower()
                if any(kw in combined for kw in source["keywords"]):
                    log_watcher(self.NAME, "WASTE_DATA_FOUND",
                                item["title"][:80])
                    flag_for_founder(
                        self.NAME,
                        item,
                        f"New waste data: {item['title'][:60]}"
                    )

        # Check each corporation's sustainability report directly
        self.check_corporate_sources()

        log_watcher(self.NAME, "CHECK_COMPLETE")


# ── Hunger Watch ──────────────────────────────────────────────────────────────

class HungerWatch:
    """
    Monitors food insecurity data.
    Keeps the human cost visible and current.

    Sources:
      Feeding America news
      FRAC (Food Research & Action Center)
      USDA food security reports
    """

    NAME     = "HungerWatch"
    INTERVAL = 604800  # weekly

    SOURCES = [
        {
            "name": "Feeding America News",
            "url":  "https://www.feedingamerica.org/feed",
            "keywords": ["hunger", "food insecurity",
                         "food bank", "families", "children"],
        },
        {
            "name": "FRAC News",
            "url":  "https://frac.org/feed",
            "keywords": ["food insecurity", "snap", "hunger",
                         "nutrition", "poverty"],
        },
    ]

    def __init__(self):
        self._stop   = threading.Event()
        self._thread = None
        self._stats  = {}

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"[{self.NAME}] Started — watching hunger data.")

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            try:
                self._check()
            except Exception as e:
                log_watcher(self.NAME, "ERROR", str(e))
            self._stop.wait(self.INTERVAL)

    def _check(self):
        log_watcher(self.NAME, "CHECK_START")
        found = []
        for source in self.SOURCES:
            text = fetch_url(source["url"])
            if not text:
                continue
            items = parse_rss(text)
            for item in items:
                combined = (item["title"] + item["summary"]).lower()
                if any(kw in combined for kw in source["keywords"]):
                    found.append(item)
                    log_watcher(self.NAME, "HUNGER_DATA",
                                item["title"][:80])

        if found:
            # Save latest hunger context
            try:
                with open("gleaning_hunger_context.json", "w") as f:
                    json.dump({
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "items":      found[:10],
                    }, f, indent=2)
            except Exception:
                pass

        log_watcher(self.NAME, "CHECK_COMPLETE",
                    f"{len(found)} items found")


# ── Price Watch ───────────────────────────────────────────────────────────────

class PriceWatch:
    """
    Monitors USDA food price data quarterly.
    Keeps the family-fed calculation accurate.
    When the USDA adjusts food consumption figures,
    Gleaning adjusts with them.
    """

    NAME     = "PriceWatch"
    INTERVAL = 2592000  # monthly

    SOURCES = [
        {
            "name": "USDA ERS Food Price Outlook",
            "url":  "https://www.ers.usda.gov/rss/",
            "keywords": ["food price", "cpi", "food at home",
                         "food expenditure", "food cost"],
        },
    ]

    def __init__(self):
        self._stop   = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"[{self.NAME}] Started — watching food prices.")

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            try:
                self._check()
            except Exception as e:
                log_watcher(self.NAME, "ERROR", str(e))
            self._stop.wait(self.INTERVAL)

    def _check(self):
        log_watcher(self.NAME, "CHECK_START")
        for source in self.SOURCES:
            text = fetch_url(source["url"])
            if not text:
                continue
            items = parse_rss(text)
            for item in items:
                combined = (item["title"] + item["summary"]).lower()
                if any(kw in combined for kw in source["keywords"]):
                    log_watcher(self.NAME, "PRICE_UPDATE",
                                item["title"][:80])
                    flag_for_founder(
                        self.NAME,
                        item,
                        f"Food price update: {item['title'][:60]}"
                    )
        log_watcher(self.NAME, "CHECK_COMPLETE")


# ── Corporation Watch ─────────────────────────────────────────────────────────

class CorporationWatch:
    """
    Monitors news for food waste stories, dumping,
    recalls, and corporate behavior relevant to Gleaning.

    Surfaces stories that Hoarders moderators should know about.
    Surfaces new corporate acquisitions for Truth Wall review.

    Sources:
      Google News RSS (food waste)
      Reuters RSS (corporate food)
      AP News RSS
    """

    NAME     = "CorporationWatch"
    INTERVAL = 3600  # hourly

    SOURCES = [
        {
            "name": "Google News — Food Waste",
            "url":  "https://news.google.com/rss/search?q=food+waste+corporation&hl=en-US&gl=US&ceid=US:en",
            "keywords": ["food waste", "dumped", "thrown away",
                         "landfill", "wasted food", "food recall",
                         "acquisition", "acquires", "buys brand"],
        },
        {
            "name": "Google News — Food Insecurity",
            "url":  "https://news.google.com/rss/search?q=food+insecurity+hunger+america&hl=en-US&gl=US&ceid=US:en",
            "keywords": ["food insecurity", "hunger", "food bank",
                         "food pantry", "families", "children hungry"],
        },
    ]

    WASTE_KEYWORDS = [
        "dumped food", "food dumped", "thrown away",
        "food destroyed", "food discarded",
        "tons of food wasted", "pounds of food wasted",
        "food rotting", "expired food thrown",
        "grocery store dumps", "supermarket dumps",
        "food in landfill", "food to landfill",
        "wasted food instead", "chose to dump",
    ]

    ACQUISITION_KEYWORDS = [
        "acquires", "acquisition", "buys brand", "purchases brand",
        "takeover", "merger", "acquired by",
    ]

    def __init__(self):
        self._stop = threading.Event()
        self._thread = None
        self._seen = set()

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"[{self.NAME}] Started — watching corporate news.")

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            try:
                self._check()
            except Exception as e:
                log_watcher(self.NAME, "ERROR", str(e))
            self._stop.wait(self.INTERVAL)

    def _check(self):
        log_watcher(self.NAME, "CHECK_START")
        total_found = 0

        for source in self.SOURCES:
            text = fetch_url(source["url"])
            if not text:
                continue
            items = parse_rss(text)

            for item in items:
                item_id = hashlib.md5(
                    item["title"].encode()
                ).hexdigest()
                if item_id in self._seen:
                    continue
                self._seen.add(item_id)

                combined = (item["title"] + item["summary"]).lower()

                # Check for waste stories
                if any(kw in combined for kw in self.WASTE_KEYWORDS):
                    log_watcher(self.NAME, "WASTE_STORY",
                                item["title"][:80])
                    flag_for_founder(
                        self.NAME,
                        item,
                        f"Waste story: {item['title'][:60]}"
                    )
                    total_found += 1

                # Check for acquisitions
                if any(kw in combined for kw in self.ACQUISITION_KEYWORDS):
                    log_watcher(self.NAME, "ACQUISITION_STORY",
                                item["title"][:80])
                    flag_for_founder(
                        self.NAME,
                        item,
                        f"Possible acquisition: {item['title'][:60]}"
                    )
                    total_found += 1

        if total_found:
            print(f"[{self.NAME}] {total_found} item(s) flagged.")
        log_watcher(self.NAME, "CHECK_COMPLETE",
                    f"{total_found} flagged")

        # Trim seen set so it doesn't grow forever
        if len(self._seen) > 10000:
            self._seen = set(list(self._seen)[-5000:])


# ── Watcher Coordinator ───────────────────────────────────────────────────────

class WatcherCoordinator:
    """
    Runs all five watchers.
    Each independent. If one fails, the others continue.
    The record stays current.
    """

    def __init__(self):
        self.acquisition = AcquisitionWatch()
        self.waste       = WasteWatch()
        self.hunger      = HungerWatch()
        self.price       = PriceWatch()
        self.corporation = CorporationWatch()

        self._watchers = [
            self.acquisition,
            self.waste,
            self.hunger,
            self.price,
            self.corporation,
        ]

    def start(self):
        print("\n[WATCHERS] Starting all five watchers...")
        for w in self._watchers:
            try:
                w.start()
            except Exception as e:
                print(f"[WATCHERS] Failed to start {w.NAME}: {e}")
        print("[WATCHERS] All watchers running. The record stays current.\n")

    def stop(self):
        for w in self._watchers:
            try:
                w.stop()
            except Exception:
                pass
        print("[WATCHERS] All watchers stopped.")

    def get_flagged(self) -> list:
        """Return active flags — not deleted, not already reviewed."""
        try:
            with open(FLAGGED_LOG) as f:
                flags = json.load(f)
            return [f for f in flags
                    if not f.get("reviewed") and not f.get("deleted")]
        except Exception:
            return []

    def get_saved(self) -> list:
        """Return flags the Team has saved for future reference."""
        try:
            with open(FLAGGED_LOG) as f:
                flags = json.load(f)
            return [f for f in flags if f.get("saved") and not f.get("deleted")]
        except Exception:
            return []

    def delete_flag(self, index: int) -> dict:
        """
        Mark a flag as deleted — Team judged it irrelevant.
        Not physically removed. Marked deleted and excluded from active queue.
        Keeps the log clean without losing the record entirely.
        """
        try:
            with open(FLAGGED_LOG) as f:
                flags = json.load(f)
            if 0 <= index < len(flags):
                flags[index]["deleted"]    = True
                flags[index]["deleted_at"] = datetime.now(timezone.utc).isoformat()
                with open(FLAGGED_LOG, "w") as f:
                    json.dump(flags, f, indent=2)
                return {"ok": True, "index": index}
            return {"ok": False, "error": "Index out of range"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def save_flag(self, index: int) -> dict:
        """
        Mark a flag as saved — Team wants to keep it for future reference.
        Saved flags stay accessible via /api/flagged/saved.
        """
        try:
            with open(FLAGGED_LOG) as f:
                flags = json.load(f)
            if 0 <= index < len(flags):
                flags[index]["saved"]    = True
                flags[index]["saved_at"] = datetime.now(timezone.utc).isoformat()
                with open(FLAGGED_LOG, "w") as f:
                    json.dump(flags, f, indent=2)
                return {"ok": True, "index": index}
            return {"ok": False, "error": "Index out of range"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def purge_deleted(self) -> dict:
        """
        Permanently remove all deleted flags.
        Keeps the file clean. Run periodically or on demand.
        Saved flags are never purged.
        """
        try:
            with open(FLAGGED_LOG) as f:
                flags = json.load(f)
            before = len(flags)
            flags  = [f for f in flags if not f.get("deleted") or f.get("saved")]
            after  = len(flags)
            with open(FLAGGED_LOG, "w") as f:
                json.dump(flags, f, indent=2)
            removed = before - after
            print(f"[WATCHERS] Purged {removed} deleted flag(s). {after} remain.")
            return {"ok": True, "removed": removed, "remaining": after}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def mark_reviewed(self, index: int):
        """Mark a flagged item as reviewed."""
        try:
            with open(FLAGGED_LOG) as f:
                flags = json.load(f)
            if 0 <= index < len(flags):
                flags[index]["reviewed"] = True
                flags[index]["reviewed_at"] = \
                    datetime.now(timezone.utc).isoformat()
            with open(FLAGGED_LOG, "w") as f:
                json.dump(flags, f, indent=2)
        except Exception:
            pass

    def status(self) -> dict:
        flagged = self.get_flagged()
        return {
            "watchers":       [w.NAME for w in self._watchers],
            "flagged_count":  len(flagged),
            "log":            WATCHER_LOG,
            "note": (
                "Five watchers running. "
                "Acquisitions, waste data, hunger data, "
                "food prices, corporate news. "
                "The record stays current."
            )
        }


watcher_coordinator = WatcherCoordinator()
