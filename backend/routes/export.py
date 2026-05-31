"""
routes/export.py — GET /api/export
Generates polished HTML report (print-to-PDF) or plain text/JSON.
"""

from flask import Blueprint, jsonify, make_response, request
from database.db_manager import DatabaseManager

export_bp = Blueprint("export", __name__)


def _build_html_report(row: dict) -> str:
    grade      = row.get("grade", "?")
    score      = row.get("overall_score", 0)
    trust      = row.get("trust_score", 0)
    dark       = row.get("dark_pattern_score", 0)
    company    = row.get("company_name", "Unknown")
    url        = row.get("url", "")
    dims       = row.get("dimension_scores", {}) or {}
    flags      = row.get("red_flags", []) or []
    findings   = row.get("findings", {}) or {}
    metrics    = row.get("metrics", {}) or {}
    verify     = row.get("verification", {}) or {}
    scraped    = row.get("scraped", {}) or {}
    compliance = findings.get("compliance_indicators", []) or []
    user_rights = findings.get("user_rights", {}) or {}
    data_collected = findings.get("data_collected", []) or []
    data_shared = findings.get("data_shared", []) or []

    grade_colors = {
        "A": "#1E6838", "B": "#1048A0", "C": "#845800",
        "D": "#A84800", "F": "#A82818"
    }
    color = grade_colors.get(grade, "#4A7A58")

    grade_labels = {
        "A": "Excellent Privacy", "B": "Good Privacy",
        "C": "Adequate Privacy", "D": "Poor Privacy", "F": "Very Poor Privacy"
    }
    grade_label = grade_labels.get(grade, "")

    def score_to_grade(s):
        if s >= 90: return "A"
        if s >= 80: return "B"
        if s >= 70: return "C"
        if s >= 60: return "D"
        return "F"

    dim_label_map = {
        "data_collection_transparency": "Data Collection",
        "sharing_disclosure": "Sharing",
        "user_rights": "User Rights",
        "readability": "Readability",
        "compliance": "Compliance",
    }

    dim_rows = "".join(
        f"""<tr>
          <td style="font-weight:600">{dim_label_map.get(k, k.replace('_',' ').title())}</td>
          <td style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{grade_colors.get(score_to_grade(int(v)), '#4A7A58')};font-size:1rem">{int(v)}</td>
          <td style="width:50%">
            <div style="background:#EDE9E2;border-radius:6px;height:12px;overflow:hidden">
              <div style="width:{int(v)}%;height:100%;background:{grade_colors.get(score_to_grade(int(v)), '#4A7A58')};border-radius:6px"></div>
            </div>
          </td>
        </tr>"""
        for k, v in dims.items()
    )

    sev_colors = {"critical": "#A82818", "high": "#A84800", "medium": "#845800", "low": "#1E6838"}
    sev_bgs    = {"critical": "#FDDAD8", "high": "#FFE4C8", "medium": "#FFF0C0", "low": "#D4EDE0"}
    flag_rows = "".join(
        f"""<tr>
          <td><span style="background:{sev_bgs.get(f.get('severity','low'),'#EEE')};color:{sev_colors.get(f.get('severity','low'),'#666')};padding:3px 10px;border-radius:6px;font-size:.75rem;font-weight:700;text-transform:uppercase;white-space:nowrap">{f.get('severity','?')}</span></td>
          <td style="font-weight:600;font-size:.88rem">{f.get('issue') or f.get('pattern') or f.get('category','Unknown')}</td>
          <td style="font-size:.82rem;color:#786F66">{(f.get('explanation') or f.get('description',''))[:120]}</td>
        </tr>"""
        for f in flags
    ) if flags else "<tr><td colspan='3' style='color:#786F66'>No red flags detected.</td></tr>"

    rights_rows = "".join(
        f"""<tr>
          <td style="font-weight:600;font-size:.88rem">{k.replace('_',' ').replace(' ',chr(160),1).title()}</td>
          <td style="font-size:.85rem">{
            f'<span style="color:#1E6838;font-weight:600">✓ ' + str(v)[:100] + '</span>'
            if v else
            '<span style="color:#A82818;font-weight:600">✗ Not mentioned</span>'
          }</td>
        </tr>"""
        for k, v in user_rights.items()
    ) if user_rights else "<tr><td colspan='2' style='color:#786F66'>No rights information found.</td></tr>"

    def data_icon(t):
        return "•"

    collected_html = "".join(
        f"""<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;background:#F6F3EE;border-radius:8px;margin-bottom:8px;border:1px solid #D4CEC4">
          <div><span style="margin-right:8px">{data_icon(d.get('type'))}</span><strong style="font-size:.88rem">{d.get('type','Unknown')}</strong>
          {f'<div style="font-size:.78rem;color:#786F66;margin-top:2px">{d.get("purpose","")}</div>' if d.get('purpose') else ''}</div>
          <span style="font-size:.72rem;font-weight:700;padding:3px 9px;border-radius:5px;background:{'#FDDAD8' if d.get('sensitivity')=='high' else '#FFF0C0' if d.get('sensitivity')=='medium' else '#D4EDE0'};color:{'#A82818' if d.get('sensitivity')=='high' else '#845800' if d.get('sensitivity')=='medium' else '#1E6838'};text-transform:uppercase">{d.get('sensitivity','medium')}</span>
        </div>"""
        for d in data_collected
    ) if data_collected else "<p style='color:#786F66;font-size:.88rem'>No data types identified.</p>"

    shared_html = "".join(
        f"""<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;background:#F6F3EE;border-radius:8px;margin-bottom:8px;border:1px solid #D4CEC4">
          <div><strong style="font-size:.88rem">{d.get('recipient','Unknown')}</strong>
          {f'<div style="font-size:.78rem;color:#786F66;margin-top:2px">{d.get("data_type","")}</div>' if d.get('data_type') else ''}</div>
          <span style="font-size:.72rem;font-weight:700;padding:3px 9px;border-radius:5px;background:{'#D4EDE0' if d.get('opt_out_available') else '#FDDAD8'};color:{'#1E6838' if d.get('opt_out_available') else '#A82818'}">{'✓ Opt-out' if d.get('opt_out_available') else '✗ No opt-out'}</span>
        </div>"""
        for d in data_shared
    ) if data_shared else "<p style='color:#786F66;font-size:.88rem'>No data sharing identified.</p>"

    compliance_html = "".join(
        f"""<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:#EAF6EE;border:1px solid #90C8A0;border-radius:8px;margin-bottom:8px">
          <span style="font-size:.88rem;font-weight:600;color:#1E4828">✓ {c}</span>
        </div>"""
        for c in compliance
    ) if compliance else "<p style='color:#786F66;font-size:.88rem'>No compliance indicators detected.</p>"

    metric_items = [
        ("Word Count",       str((metrics.get("word_count") or 0)),        "words"),
        ("Sentences",        str(metrics.get("sentence_count") or "—"),    ""),
        ("Reading Grade",    f"Grade {metrics.get('flesch_kincaid_grade')}" if metrics.get("flesch_kincaid_grade") else "—", ""),
        ("Flesch Ease",      str(round(metrics.get("flesch_reading_ease") or 0)),  "/ 100"),
        ("Jargon Density",   f"{(metrics.get('jargon_density') or 0):.1f}%", ""),
        ("Passive Voice",    f"{round(metrics.get('passive_voice_percentage') or 0)}%", ""),
        ("Clause Coverage",  f"{round(metrics.get('clause_completeness_score') or 0)}%", ""),
        ("Dark Pattern",     f"{round(dark)} / 100",                        ""),
    ]
    metrics_grid = "".join(
        f"""<div style="background:#F6F3EE;border-radius:10px;padding:14px 16px;border:1px solid #D4CEC4">
          <div style="font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#786F66;margin-bottom:6px">{label}</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:1.35rem;font-weight:600;color:#232018">{val}</div>
          {f'<div style="font-size:.72rem;color:#786F66;margin-top:3px">{sub}</div>' if sub else ''}
        </div>"""
        for label, val, sub in metric_items
    )

    conf = verify.get("overall_confidence", 0)
    conf_pct = round((conf * 100) if conf <= 1 else conf) if conf else 0

    import datetime
    generated = datetime.datetime.now().strftime("%d %B %Y, %H:%M")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Privacy Report — {company}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:'DM Sans',sans-serif;font-size:14px;color:#232018;background:#F6F3EE;line-height:1.65;}}
  .page{{max-width:960px;margin:0 auto;padding:48px 56px;background:#fff;min-height:100vh;}}
  h1{{font-family:'DM Serif Display',serif;font-size:2.6rem;font-weight:400;color:{color};margin-bottom:6px;}}
  h2{{font-family:'DM Serif Display',serif;font-size:1.5rem;font-weight:400;margin:36px 0 16px;padding-bottom:10px;border-bottom:2px solid #EDE9E2;color:#232018;display:flex;align-items:center;gap:8px;}}
  .print-btn{{float:right;padding:9px 20px;background:{color};color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;font-family:'DM Sans',sans-serif;font-size:.88rem;}}
  .print-btn:hover{{opacity:.9;}}
  .hero-row{{display:flex;gap:32px;align-items:flex-start;margin:28px 0 36px;padding:28px;background:#F6F3EE;border-radius:16px;border:1px solid #D4CEC4;}}
  .grade-circle{{width:120px;height:120px;border-radius:50%;background:{color}18;border:3px solid {color};display:flex;flex-direction:column;align-items:center;justify-content:center;flex-shrink:0;}}
  .grade-big{{font-family:'DM Serif Display',serif;font-size:3.4rem;color:{color};line-height:1;}}
  .grade-sub{{font-family:'JetBrains Mono',monospace;font-size:.82rem;color:#786F66;margin-top:2px;}}
  .hero-info{{flex:1;}}
  .hero-info h3{{font-family:'DM Serif Display',serif;font-size:1.6rem;font-weight:400;color:#232018;margin-bottom:8px;}}
  .hero-info p{{font-size:.88rem;color:#786F66;margin-bottom:6px;}}
  .scores-row{{display:flex;gap:14px;margin-top:18px;flex-wrap:wrap;}}
  .score-box{{background:#fff;border:1px solid #D4CEC4;border-radius:10px;padding:14px 18px;min-width:120px;}}
  .score-box-val{{font-family:'JetBrains Mono',monospace;font-size:1.7rem;font-weight:700;color:#232018;}}
  .score-box-label{{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#786F66;margin-top:4px;}}
  table{{width:100%;border-collapse:collapse;margin-bottom:4px;}}
  th{{background:#F6F3EE;text-align:left;padding:10px 14px;font-size:.74rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#786F66;}}
  td{{padding:10px 14px;border-bottom:1px solid #EDE9E2;vertical-align:middle;}}
  .summary-box{{background:#F6F3EE;border-left:4px solid {color};padding:18px 22px;border-radius:6px;font-size:.93rem;line-height:1.75;color:#232018;}}
  .metrics-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;}}
  .verify-row{{display:flex;gap:14px;margin-bottom:14px;flex-wrap:wrap;}}
  .verify-box{{flex:1;min-width:120px;background:#F6F3EE;border:1px solid #D4CEC4;border-radius:10px;padding:16px;text-align:center;}}
  .verify-val{{font-family:'JetBrains Mono',monospace;font-size:1.8rem;font-weight:700;color:#232018;}}
  .verify-label{{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#786F66;margin-top:5px;}}
  .footer{{margin-top:48px;padding-top:20px;border-top:1px solid #EDE9E2;display:flex;justify-content:space-between;align-items:center;font-size:.75rem;color:#B0A898;}}
  @media print{{
    body{{background:#fff;}}
    .page{{max-width:100%;padding:20px 30px;box-shadow:none;}}
    .print-btn{{display:none;}}
    h2{{margin-top:20px;}}
  }}
</style>
</head>
<body>
<div class="page">
  <button class="print-btn" onclick="window.print()">⬇ Print / Save as PDF</button>

  <h1>Privacy Policy Report</h1>
  <p style="color:#786F66;font-size:.88rem;margin-bottom:0">Generated {generated} by PrivacyGrader</p>

  <div class="hero-row">
    <div class="grade-circle">
      <div class="grade-big">{grade}</div>
      <div class="grade-sub">Grade</div>
    </div>
    <div class="hero-info">
      <h3>{company}</h3>
      {f'<p>🔗 <a href="{url}" style="color:{color};word-break:break-all">{url[:80]}{"…" if len(url)>80 else ""}</a></p>' if url else ''}
      <p style="margin-top:4px;color:#786F66;font-size:.85rem">{grade_label}</p>
      <div class="scores-row">
        <div class="score-box">
          <div class="score-box-val">{round(score)}</div>
          <div class="score-box-label">Overall Score</div>
        </div>
        <div class="score-box">
          <div class="score-box-val">{trust:.1f}</div>
          <div class="score-box-label">Trust Score</div>
        </div>
        <div class="score-box">
          <div class="score-box-val">{round(dark)}</div>
          <div class="score-box-label">Dark Pattern</div>
        </div>
        <div class="score-box">
          <div class="score-box-val">{len(flags)}</div>
          <div class="score-box-label">Red Flags</div>
        </div>
      </div>
    </div>
  </div>

  <h2>Dimension Scores</h2>
  <table>
    <tr><th>Dimension</th><th>Score</th><th style="width:55%">Progress</th></tr>
    {dim_rows}
  </table>

  <h2>Summary</h2>
  <div class="summary-box">{findings.get('summary') or 'No summary available.'}</div>

  <h2>Red Flags ({len(flags)} found)</h2>
  <table>
    <tr><th>Severity</th><th>Issue</th><th>Details</th></tr>
    {flag_rows}
  </table>

  <h2>User Rights</h2>
  <table>
    <tr><th>Right</th><th>Status</th></tr>
    {rights_rows}
  </table>

  <h2>Data Collected</h2>
  {collected_html}

  <h2>Data Shared With</h2>
  {shared_html}

  <h2>Compliance Indicators</h2>
  {compliance_html}

  <h2>NLP Metrics</h2>
  <div class="metrics-grid">{metrics_grid}</div>

  {f'''<h2>Claim Verification</h2>
  <div class="verify-row">
    <div class="verify-box"><div class="verify-val">{conf_pct}%</div><div class="verify-label">Confidence</div></div>
    <div class="verify-box"><div class="verify-val">{verify.get("total_claims",0)}</div><div class="verify-label">Claims Verified</div></div>
    <div class="verify-box"><div class="verify-val">{verify.get("hallucination_count",0)}</div><div class="verify-label">Hallucinations</div></div>
  </div>
  {f'<p style="font-size:.88rem;color:#786F66;margin-top:10px;line-height:1.65">{verify.get("summary","")}</p>' if verify.get("summary") else ""}''' if verify.get("total_claims") else ""}

  <div class="footer">
    <span>Privy · Custom NLP + Google Gemini</span>
    <span>{generated}</span>
  </div>
</div>
</body>
</html>"""


def _build_text_report(row: dict) -> str:
    dims   = row.get("dimension_scores", {}) or {}
    flags  = row.get("red_flags", []) or []
    metrics = row.get("metrics", {}) or {}
    findings = row.get("findings", {}) or {}

    lines = [
        "=" * 64,
        "PRIVY — ANALYSIS REPORT",
        "=" * 64,
        f"Company      : {row.get('company_name', 'Unknown')}",
        f"URL          : {row.get('url', '')}",
        f"Grade        : {row.get('grade', '?')}",
        f"Overall Score: {row.get('overall_score', 0):.1f} / 100",
        f"Trust Score  : {row.get('trust_score', 0):.1f} / 100",
        f"Dark Patterns: {row.get('dark_pattern_score', 0):.1f} / 100",
        "",
        "DIMENSION SCORES",
        "-" * 40,
    ]
    for dim, score in dims.items():
        label = dim.replace("_", " ").title()
        bar   = "█" * int(score / 5) + "░" * (20 - int(score / 5))
        lines.append(f"  {label:<36} {bar}  {score:.0f}")

    lines += ["", "NLP METRICS", "-" * 40]
    for key in ["word_count", "flesch_reading_ease", "flesch_kincaid_grade",
                "jargon_density", "passive_voice_percentage", "clause_completeness_score"]:
        val = metrics.get(key, "—")
        lines.append(f"  {key.replace('_', ' ').title():<36}: {val}")

    lines += ["", f"RED FLAGS  ({len(flags)} found)", "-" * 40]
    for i, f in enumerate(flags, 1):
        sev   = f.get("severity", "?").upper()
        issue = f.get("issue") or f.get("pattern", "Unknown")
        lines.append(f"  {i}. [{sev}] {issue}")
        if f.get("quote"):
            lines.append(f'     Quote: "{f["quote"][:120]}"')
        if f.get("explanation"):
            lines.append(f'     Why  : {f["explanation"][:120]}')
        lines.append("")

    lines += ["USER RIGHTS", "-" * 40]
    for right, val in (findings.get("user_rights") or {}).items():
        status = "✓" if val else "✗"
        lines.append(f"  {status} {right.replace('_',' ').title()}: {(str(val) if val else 'Not mentioned')[:80]}")

    lines += ["", "SUMMARY", "-" * 40,
              findings.get("summary") or "No summary available.", "",
              "=" * 64,
              "Generated by Privy · Custom NLP + Google Gemini",
              "=" * 64]
    return "\n".join(lines)


@export_bp.route("/export", methods=["GET"])
def export_by_url():
    url = request.args.get("url", "").strip()
    fmt = request.args.get("format", "html").lower()

    if not url:
        return jsonify({"success": False, "error": "'url' query parameter required"}), 400

    row = DatabaseManager.get_analysis(url)
    if not row:
        return jsonify({"success": False, "error": "No analysis found for this URL. Run /api/analyze first."}), 404

    if fmt == "json":
        row.pop("policy_text", None)
        import json
        resp = make_response(json.dumps(row, indent=2, ensure_ascii=False), 200)
        resp.headers["Content-Type"] = "application/json"
        resp.headers["Content-Disposition"] = f'attachment; filename="privacy_report_{row["company_name"]}.json"'
        return resp

    if fmt == "text":
        content = _build_text_report(row)
        resp = make_response(content, 200)
        resp.headers["Content-Type"] = "text/plain; charset=utf-8"
        resp.headers["Content-Disposition"] = f'attachment; filename="privacy_report_{row["company_name"]}.txt"'
        return resp

    # Default: polished HTML
    content = _build_html_report(row)
    resp = make_response(content, 200)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp
