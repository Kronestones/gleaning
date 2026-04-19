"""
hoarders_email.py — Gleaning Email Notifications

Three triggers:
  on_submit  — reporter receives confirmation
  on_approve — reporter notified their report is live
  on_deny    — reporter notified their report was not approved

Email is discarded after send. Never stored. Never logged.
Resend API. FROM_ADDRESS must match verified Resend domain.

— Krone the Architect · 2026
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone


RESEND_API_URL = "https://api.resend.com/emails"
FROM_ADDRESS   = os.environ.get("FROM_ADDRESS", "Gleaning <noreply@gleaning.onrender.com>")


def _send(to: str, subject: str, html: str) -> bool:
    """
    Send an email via Resend API.
    Returns True on success, False on failure.
    Email address is used once and discarded — never stored.
    """
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        print("[EMAIL] RESEND_API_KEY not set — email not sent.")
        return False

    payload = json.dumps({
        "from":    FROM_ADDRESS,
        "to":      [to],
        "subject": subject,
        "html":    html,
    }).encode("utf-8")

    req = urllib.request.Request(
        RESEND_API_URL,
        data    = payload,
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        },
        method = "POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            print(f"[EMAIL] Sent to {to[:4]}**** — status {status}")
            return status in (200, 201)
    except urllib.error.HTTPError as e:
        print(f"[EMAIL] HTTP error: {e.code} {e.reason}")
        return False
    except Exception as e:
        print(f"[EMAIL] Failed: {e}")
        return False


def on_submit(to: str, report_id: int, lbs: float) -> bool:
    """
    Sent when a report is submitted.
    Confirms receipt and sets expectations.
    """
    subject = "Your report has been received — Gleaning"
    html = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                max-width:520px;margin:0 auto;background:#0a0a0a;color:#e8e8e8;
                padding:32px 24px;border-radius:10px;">
      <div style="font-size:24px;font-weight:800;color:#7cb87c;margin-bottom:8px;">
        🌾 Gleaning
      </div>
      <div style="font-size:13px;color:#666;margin-bottom:28px;font-style:italic;">
        The harvest was never only theirs.
      </div>
      <h2 style="font-size:20px;font-weight:700;color:#fff;margin-bottom:16px;">
        Your report has been received.
      </h2>
      <p style="font-size:15px;color:#aaa;line-height:1.7;margin-bottom:16px;">
        Thank you for documenting this. Your report of approximately
        <strong style="color:#7cb87c">{int(lbs):,} lbs</strong> of food waste
        has been submitted and is under review by the Team.
      </p>
      <p style="font-size:15px;color:#aaa;line-height:1.7;margin-bottom:16px;">
        You will receive one more email when the Team has reviewed your report.
        After that, this email address is discarded. It is never stored, never shared,
        never used again.
      </p>
      <div style="background:#111;border:1px solid #2a2a2a;border-radius:8px;
                  padding:16px;margin-bottom:24px;font-size:13px;color:#666;">
        Report ID: #{report_id} &nbsp;·&nbsp;
        Submitted: {datetime.now(timezone.utc).strftime('%b %d, %Y')}
      </div>
      <p style="font-size:13px;color:#444;line-height:1.6;">
        Gleaning · No advertising · No data selling · Power to the People
      </p>
    </div>
    """
    return _send(to, subject, html)


def on_approve(to: str, report_id: int, lbs: float) -> bool:
    """
    Sent when a report is approved and goes live on the map.
    """
    families = int(lbs / 38)
    subject = "Your report is live — Gleaning"
    html = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                max-width:520px;margin:0 auto;background:#0a0a0a;color:#e8e8e8;
                padding:32px 24px;border-radius:10px;">
      <div style="font-size:24px;font-weight:800;color:#7cb87c;margin-bottom:8px;">
        🌾 Gleaning
      </div>
      <div style="font-size:13px;color:#666;margin-bottom:28px;font-style:italic;">
        The harvest was never only theirs.
      </div>
      <h2 style="font-size:20px;font-weight:700;color:#fff;margin-bottom:16px;">
        Your report is live.
      </h2>
      <p style="font-size:15px;color:#aaa;line-height:1.7;margin-bottom:16px;">
        The Team has reviewed and approved your report.
        It is now visible on the <a href="https://gleaning.onrender.com/hoarders"
        style="color:#7cb87c;">Project Gleaning map</a> as a redistribution opportunity.
      </p>
      <div style="background:#0d1f14;border:1px solid rgba(74,158,107,0.25);
                  border-radius:8px;padding:20px;margin-bottom:24px;text-align:center;">
        <div style="font-size:36px;font-weight:800;color:#7cb87c;line-height:1;">
          ~{families:,}
        </div>
        <div style="font-size:13px;color:#aaa;margin-top:6px;">
          families could have been fed for a week
        </div>
        <div style="font-size:11px;color:#666;margin-top:4px;">
          Based on USDA data · 38 lbs/week · Family of 4 · Always rounded down
        </div>
      </div>
      <p style="font-size:15px;color:#aaa;line-height:1.7;margin-bottom:16px;">
        This is the last email you will receive from Gleaning about this report.
        Your email address has now been discarded.
      </p>
      <p style="font-size:13px;color:#444;line-height:1.6;">
        Gleaning · No advertising · No data selling · Power to the People
      </p>
    </div>
    """
    return _send(to, subject, html)


def on_deny(to: str, report_id: int) -> bool:
    """
    Sent when a report is denied.
    Brief, respectful, no reason required.
    """
    subject = "Your report was not approved — Gleaning"
    html = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                max-width:520px;margin:0 auto;background:#0a0a0a;color:#e8e8e8;
                padding:32px 24px;border-radius:10px;">
      <div style="font-size:24px;font-weight:800;color:#7cb87c;margin-bottom:8px;">
        🌾 Gleaning
      </div>
      <div style="font-size:13px;color:#666;margin-bottom:28px;font-style:italic;">
        The harvest was never only theirs.
      </div>
      <h2 style="font-size:20px;font-weight:700;color:#fff;margin-bottom:16px;">
        Your report was not approved.
      </h2>
      <p style="font-size:15px;color:#aaa;line-height:1.7;margin-bottom:16px;">
        After review, the Team was not able to approve your report for publication
        on Project Gleaning. This may be because the report did not meet our documentation
        standards, or the location could not be verified.
      </p>
      <p style="font-size:15px;color:#aaa;line-height:1.7;margin-bottom:16px;">
        If you witnessed food waste, we encourage you to submit a new report
        with a clear photo and a precise location pin.
      </p>
      <p style="font-size:15px;color:#aaa;line-height:1.7;margin-bottom:24px;">
        This is the last email you will receive from Gleaning about this report.
        Your email address has now been discarded.
      </p>
      <p style="font-size:13px;color:#444;line-height:1.6;">
        Gleaning · No advertising · No data selling · Power to the People
      </p>
    </div>
    """
    return _send(to, subject, html)


def on_problem_report(description: str, contact: str = "") -> bool:
    """
    Alert the founder and team that a problem has been reported on the submit page.
    """
    founder_email = os.environ.get("FOUNDER_EMAIL", "")
    if not founder_email:
        print("[EMAIL] FOUNDER_EMAIL not set — problem report not sent.")
        return False

    subject = "[Gleaning] Problem Report — Submit Page"
    contact_line = f"<p><strong>Contact:</strong> {contact}</p>" if contact else "<p><strong>Contact:</strong> Not provided</p>"
    html = f"""
    <div style="background:#0a0a0a;color:#e8e8e8;font-family:sans-serif;padding:32px;max-width:600px;margin:0 auto">
      <h2 style="color:#e74c3c;margin-bottom:8px">⚠ Problem Report</h2>
      <p style="color:#999;margin-bottom:24px">A user reported a problem on the Project Gleaning submit page.</p>
      <div style="background:#1a1a1a;border:1px solid #2a2a2a;border-radius:8px;padding:20px;margin-bottom:20px">
        <p><strong>Description:</strong></p>
        <p style="color:#ccc;margin-top:8px">{description}</p>
      </div>
      {contact_line}
      <p style="color:#666;font-size:12px;margin-top:24px">Gleaning · The Team has been notified · Review at /hoarders/moderate</p>
    </div>
    """
    return _send(founder_email, subject, html)
