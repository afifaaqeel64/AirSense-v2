"""AirSense Pakistan - Automated Daily Telemetry Email Dispatcher.

Delivers daily 3-tier telemetry snapshot CSV and ZIP packages with
rich responsive HTML summaries and plain-text fallbacks via standard SMTP (zero cost).
"""

import os
import smtplib
import logging
from pathlib import Path
from email.message import EmailMessage
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger("airsense.email_dispatcher")


def mask_email_secret(val: str, prefix_len: int = 3, suffix_len: int = 3) -> str:
    """Safely masks sensitive credentials for logging."""
    if not val:
        return "<empty>"
    s = str(val).strip()
    if len(s) <= prefix_len + suffix_len:
        return "****"
    return f"{s[:prefix_len]}...{s[-suffix_len:]}"


def parse_email_recipients(raw_recipients: Optional[Union[str, List[str]]]) -> List[str]:
    """Normalizes single string, comma/semicolon-separated string, or list into cleaned email list."""
    if not raw_recipients:
        return []
    if isinstance(raw_recipients, list):
        items = raw_recipients
    else:
        # Split by comma or semicolon
        items = str(raw_recipients).replace(";", ",").split(",")

    cleaned = []
    for item in items:
        e = item.strip().strip('"').strip("'").strip()
        if e and "@" in e and "." in e:
            parts = e.split("@", 1)
            if len(parts) == 2 and parts[0].strip() and "." in parts[1] and len(parts[1].split(".")[-1]) >= 2:
                cleaned.append(e)
    return cleaned


def render_backup_email_text(summary_data: Dict[str, Any], target_date: str) -> str:
    """Renders plain text version of the daily telemetry snapshot email."""
    pm25 = summary_data.get("avg_pm25", 0.0)
    min_pm25 = summary_data.get("min_pm25", 0.0)
    max_pm25 = summary_data.get("max_pm25", 0.0)
    temp = summary_data.get("avg_temp", 0.0)
    hum = summary_data.get("avg_hum", 0.0)
    tot = summary_data.get("total_records", 0)

    tier_counts = summary_data.get("tier_counts", {})
    t1_cnt = tier_counts.get("tier1", tot)
    t2_cnt = tier_counts.get("tier2", 24)
    t3_cnt = tier_counts.get("tier3", tot)
    t3_valid = tier_counts.get("valid_tier3", t3_cnt)

    text = f"""AIRSENSE PAKISTAN - DAILY 3-TIER TELEMETRY SNAPSHOT
Target Date (PKT UTC+5): {target_date}

SUMMARY OBSERVATIONS:
- Total Hardware Readings: {tot:,} records
- PM2.5 Air Quality: Avg {pm25:.1f} ug/m3 (Min: {min_pm25:.1f}, Max: {max_pm25:.1f})
- Ambient Temperature: Avg {temp:.1f} °C
- Relative Humidity: Avg {hum:.0f} %

3-TIER DATASET CLASSIFICATION:
- Tier 1 (Hardware Sensor + Verified Chemicals): {t1_cnt:,} rows
- Tier 2 (Pure Open-Source Meteorological & Chemical Grid): {t2_cnt} hourly records
- Tier 3 (ML Cumulative Validated Defining Dataset): {t3_cnt:,} rows (Validated: {t3_valid:,})

ATTACHMENTS INCLUDED:
1. tier3_ml_cumulative_validated_{target_date.replace('-', '_')}.csv
   Defining ML dataset with cross-sensor validation, QC flags, and SHA-256 provenance hashes.
2. airsense_tiered_daily_{target_date.replace('-', '_')}.zip
   Complete archive containing all 3 tiers + legacy daily telemetry CSV.

Live Environmental Dashboard: https://airsense-team.vercel.app
AirSense Pakistan Autonomous Monitoring System
"""
    return text


def render_backup_email_html(summary_data: Dict[str, Any], target_date: str) -> str:
    """Renders modern, responsive HTML email report with metric cards and tier breakdown."""
    pm25 = summary_data.get("avg_pm25", 0.0)
    min_pm25 = summary_data.get("min_pm25", 0.0)
    max_pm25 = summary_data.get("max_pm25", 0.0)
    temp = summary_data.get("avg_temp", 0.0)
    hum = summary_data.get("avg_hum", 0.0)
    tot = summary_data.get("total_records", 0)

    tier_counts = summary_data.get("tier_counts", {})
    t1_cnt = tier_counts.get("tier1", tot)
    t2_cnt = tier_counts.get("tier2", 24)
    t3_cnt = tier_counts.get("tier3", tot)
    t3_valid = tier_counts.get("valid_tier3", t3_cnt)

    # Health status color determination based on PM2.5
    if pm25 <= 15.0:
        aqi_badge_color = "#10b981"
        aqi_label = "Optimal (WHO Guideline Compliant)"
    elif pm25 <= 35.4:
        aqi_badge_color = "#f59e0b"
        aqi_label = "Moderate (Acceptable)"
    elif pm25 <= 55.4:
        aqi_badge_color = "#f97316"
        aqi_label = "Unhealthy for Sensitive Groups"
    else:
        aqi_badge_color = "#ef4444"
        aqi_label = "Elevated Alert"

    date_under = target_date.replace("-", "_")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AirSense Daily 3-Tier Telemetry Report</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0b1120; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f1f5f9;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0b1120; padding: 24px 12px;">
    <tr>
      <td align="center">
        <!-- Master Container -->
        <table role="presentation" width="100%" style="max-width: 640px; background-color: #131d33; border: 1px solid #1e293b; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.5);">
          
          <!-- Header Banner -->
          <tr>
            <td style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 28px 32px; border-bottom: 1px solid #334155;">
              <table width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td>
                    <div style="display: inline-block; background-color: #10b981; color: #0f172a; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; padding: 4px 10px; border-radius: 20px; margin-bottom: 8px;">
                      Autonomous 24/7 Pipeline
                    </div>
                    <h1 style="margin: 0; font-size: 22px; font-weight: 700; color: #ffffff; letter-spacing: -0.5px;">
                      AirSense Pakistan Telemetry Snapshot
                    </h1>
                    <p style="margin: 6px 0 0 0; font-size: 14px; color: #94a3b8;">
                      Calendar Day: <strong style="color: #38bdf8;">{target_date} (PKT / UTC+5)</strong>
                    </p>
                  </td>
                  <td align="right" valign="top">
                    <div style="width: 44px; height: 44px; border-radius: 12px; background-color: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); text-align: center; line-height: 44px; font-size: 20px;">
                      🌬️
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Primary Metric Cards -->
          <tr>
            <td style="padding: 24px 32px 12px 32px;">
              <h2 style="margin: 0 0 16px 0; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: #94a3b8;">
                Key Environmental Observations
              </h2>
              <table width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <!-- Card 1: PM2.5 -->
                  <td width="48%" style="background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; vertical-align: top;">
                    <div style="font-size: 12px; font-weight: 600; color: #94a3b8; text-transform: uppercase;">Average PM2.5</div>
                    <div style="font-size: 28px; font-weight: 800; color: #ffffff; margin: 4px 0;">
                      {pm25:.1f} <span style="font-size: 14px; font-weight: 500; color: #94a3b8;">μg/m³</span>
                    </div>
                    <div style="display: inline-block; font-size: 11px; font-weight: 700; color: {aqi_badge_color}; background-color: rgba(255,255,255,0.05); padding: 3px 8px; border-radius: 6px;">
                      {aqi_label}
                    </div>
                    <div style="font-size: 11px; color: #64748b; margin-top: 6px;">
                      Range: {min_pm25:.1f} – {max_pm25:.1f} μg/m³
                    </div>
                  </td>
                  <td width="4%"></td>
                  <!-- Card 2: Temperature & Humidity -->
                  <td width="48%" style="background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; vertical-align: top;">
                    <div style="font-size: 12px; font-weight: 600; color: #94a3b8; text-transform: uppercase;">Microclimate</div>
                    <div style="font-size: 28px; font-weight: 800; color: #ffffff; margin: 4px 0;">
                      {temp:.1f}°C <span style="font-size: 18px; font-weight: 500; color: #38bdf8;">/ {hum:.0f}%</span>
                    </div>
                    <div style="font-size: 12px; color: #cbd5e1; margin-top: 4px;">
                      Bosch BME280 Ground Truth
                    </div>
                    <div style="font-size: 11px; color: #64748b; margin-top: 6px;">
                      Total Cycles: <strong style="color: #f1f5f9;">{tot:,}</strong> records
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- 3-Tier Classification Table -->
          <tr>
            <td style="padding: 12px 32px 24px 32px;">
              <h2 style="margin: 0 0 12px 0; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: #94a3b8;">
                3-Tier Dataset Breakdown
              </h2>
              <table width="100%" cellspacing="0" cellpadding="0" style="border: 1px solid #334155; border-radius: 10px; overflow: hidden; background-color: #1a243b;">
                <tr style="background-color: #0f172a; border-bottom: 1px solid #334155;">
                  <th align="left" style="padding: 10px 14px; font-size: 12px; color: #94a3b8; font-weight: 600;">Dataset Tier</th>
                  <th align="left" style="padding: 10px 14px; font-size: 12px; color: #94a3b8; font-weight: 600;">Contents & Variables</th>
                  <th align="right" style="padding: 10px 14px; font-size: 12px; color: #94a3b8; font-weight: 600;">Records</th>
                </tr>
                <tr style="border-bottom: 1px solid #283548;">
                  <td style="padding: 10px 14px; font-size: 12px; font-weight: 700; color: #38bdf8;">Tier 1</td>
                  <td style="padding: 10px 14px; font-size: 12px; color: #cbd5e1;">Hardware Sensors + Verified Atmospheric Chemistry</td>
                  <td align="right" style="padding: 10px 14px; font-size: 12px; font-weight: 600; color: #f1f5f9;">{t1_cnt:,}</td>
                </tr>
                <tr style="border-bottom: 1px solid #283548;">
                  <td style="padding: 10px 14px; font-size: 12px; font-weight: 700; color: #a78bfa;">Tier 2</td>
                  <td style="padding: 10px 14px; font-size: 12px; color: #cbd5e1;">Pure Open-Source Meteorological & Chemical Grid</td>
                  <td align="right" style="padding: 10px 14px; font-size: 12px; font-weight: 600; color: #f1f5f9;">{t2_cnt}</td>
                </tr>
                <tr>
                  <td style="padding: 10px 14px; font-size: 12px; font-weight: 700; color: #10b981;">Tier 3 ★</td>
                  <td style="padding: 10px 14px; font-size: 12px; color: #cbd5e1;">ML Cumulative Validated Dataset (Cross-Validated)</td>
                  <td align="right" style="padding: 10px 14px; font-size: 12px; font-weight: 700; color: #10b981;">{t3_cnt:,}</td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Attachments Box -->
          <tr>
            <td style="padding: 0 32px 24px 32px;">
              <div style="background-color: rgba(56, 189, 248, 0.08); border: 1px dashed rgba(56, 189, 248, 0.3); border-radius: 12px; padding: 16px;">
                <div style="font-size: 13px; font-weight: 700; color: #38bdf8; margin-bottom: 8px;">
                  📎 Attached Datasets (Included with this Email):
                </div>
                <div style="font-size: 12px; color: #cbd5e1; margin-bottom: 4px;">
                  • <strong style="color: #f8fafc;">tier3_ml_cumulative_validated_{date_under}.csv</strong>: Defining ML dataset containing all 35 validated sensor and chemical variables.
                </div>
                <div style="font-size: 12px; color: #cbd5e1;">
                  • <strong style="color: #f8fafc;">airsense_tiered_daily_{date_under}.zip</strong>: Complete package containing Tier 1, Tier 2, Tier 3, and legacy telemetry CSV.
                </div>
              </div>
            </td>
          </tr>

          <!-- Action Button -->
          <tr>
            <td align="center" style="padding: 0 32px 32px 32px;">
              <a href="https://airsense-team.vercel.app" style="display: inline-block; background-color: #10b981; color: #064e3b; font-size: 14px; font-weight: 700; text-decoration: none; padding: 12px 28px; border-radius: 8px; box-shadow: 0 4px 12px rgba(16,185,129,0.3);">
                Open Live Environmental Dashboard →
              </a>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color: #0d1527; padding: 20px 32px; border-top: 1px solid #1e293b; text-align: center;">
              <p style="margin: 0; font-size: 11px; color: #64748b;">
                AirSense Pakistan Autonomous Monitoring System • BIC Rooftop, Karachi
              </p>
              <p style="margin: 4px 0 0 0; font-size: 10px; color: #475569;">
                Automated 24/7 telemetry snapshot dispatched concurrently with Telegram Bot channel.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
    return html


def send_daily_backup_email(
    target_date: str,
    summary_data: Dict[str, Any],
    attachments: Optional[List[Union[Path, str]]] = None,
    to_emails: Optional[Union[str, List[str]]] = None,
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None,
    smtp_user: Optional[str] = None,
    smtp_password: Optional[str] = None,
    subject_prefix: str = "AirSense Pakistan",
    use_tls: bool = True,
    timeout: float = 30.0
) -> bool:
    """Dispatches daily 3-tier telemetry snapshot and attachments to designated email recipients.

    Returns:
        True if email successfully transmitted, False otherwise.
    """
    # 1. Resolve credentials & configuration from args or environment
    host = smtp_host or os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(smtp_port or os.environ.get("SMTP_PORT", 587))
    user = smtp_user or os.environ.get("SMTP_USER") or os.environ.get("EMAIL_USER") or ""
    password = smtp_password or os.environ.get("SMTP_PASSWORD") or os.environ.get("EMAIL_PASSWORD") or ""
    recipients_raw = to_emails or os.environ.get("EMAIL_TO") or os.environ.get("ALERT_EMAIL_RECIPIENTS") or ""

    recipients = parse_email_recipients(recipients_raw)

    if not user or not password:
        logger.info(
            f"[EMAIL NOTICE] Email dispatch skipped: SMTP credentials not configured "
            f"(user_present={bool(user)}, password_present={bool(password)})."
        )
        return False

    if not recipients:
        logger.warning("[EMAIL WARNING] Email dispatch skipped: No valid recipients found in EMAIL_TO.")
        return False

    masked_user = mask_email_secret(user)
    masked_recipients = [mask_email_secret(r) for r in recipients]
    logger.info(
        f"[EMAIL] Preparing daily backup email via {host}:{port} "
        f"from {masked_user} to {len(recipients)} recipient(s): {', '.join(masked_recipients)}..."
    )

    # 2. Build MIME EmailMessage
    msg = EmailMessage()
    msg["Subject"] = f"[{subject_prefix}] 3-Tier Daily Telemetry Snapshot - {target_date} (PKT)"
    msg["From"] = f"AirSense Pakistan <{user}>"
    msg["To"] = ", ".join(recipients)

    # Render body contents
    text_content = render_backup_email_text(summary_data, target_date)
    html_content = render_backup_email_html(summary_data, target_date)

    msg.set_content(text_content)
    msg.add_alternative(html_content, subtype="html")

    # 3. Add attachments
    att_list = attachments or []
    attached_count = 0

    for item in att_list:
        p = Path(item)
        if not p.exists() or p.stat().st_size == 0:
            logger.warning(f"[EMAIL WARNING] Attachment {p.name} does not exist or is empty; skipping.")
            continue

        file_size_kb = round(p.stat().st_size / 1024, 1)

        if p.suffix.lower() == ".csv":
            maintype, subtype = "text", "csv"
        elif p.suffix.lower() == ".zip":
            maintype, subtype = "application", "zip"
        else:
            maintype, subtype = "application", "octet-stream"

        try:
            with open(p, "rb") as f:
                file_bytes = f.read()
            msg.add_attachment(
                file_bytes,
                maintype=maintype,
                subtype=subtype,
                filename=p.name
            )
            attached_count += 1
            logger.info(f"[EMAIL] Attached {p.name} ({file_size_kb} KB) [{maintype}/{subtype}].")
        except Exception as e:
            logger.error(f"[EMAIL ERROR] Failed to attach {p.name}: {e}")

    # 4. Transmit via SMTP
    try:
        if port == 465:
            # Direct SSL
            server = smtplib.SMTP_SSL(host, port, timeout=timeout)
        else:
            # Standard port 587 with STARTTLS
            server = smtplib.SMTP(host, port, timeout=timeout)
            if use_tls:
                server.starttls()

        server.login(user, password)
        server.send_message(msg)
        server.quit()

        logger.info(
            f"[EMAIL SUCCESS] Successfully sent daily backup email with {attached_count} attachment(s) "
            f"to {len(recipients)} recipient(s) for date {target_date}."
        )
        return True

    except smtplib.SMTPAuthenticationError as e:
        logger.error(
            f"[EMAIL AUTH ERROR] SMTP Authentication failed ({e.smtp_code}: {e.smtp_error}). "
            f"If using Gmail, verify you are using a 16-character Google App Password (not your account password) "
            f"and 2FA is enabled."
        )
        return False
    except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError, OSError) as e:
        logger.error(f"[EMAIL CONNECTION ERROR] Could not connect to SMTP server {host}:{port}: {e}")
        return False
    except Exception as e:
        logger.error(f"[EMAIL UNEXPECTED ERROR] An error occurred during email transmission: {e}")
        return False
