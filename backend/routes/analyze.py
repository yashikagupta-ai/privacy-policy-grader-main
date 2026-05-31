"""
routes/analyze.py — Analysis endpoints.

OUR CUSTOM CODE — NO LLM USED IN THIS FILE.

Endpoints
---------
POST /api/analyze          — full pipeline from URL (scrape → NLP → LLM → grade → verify)
POST /api/analyze/text     — full pipeline from pasted text (skips scraper entirely)
GET  /api/history/<domain> — version history for a domain (grade changes over time)

The analyse_text endpoint is particularly useful for:
  - Paywalled or login-protected policy pages
  - Offline demo using samples/ text files
  - PDF policies pasted as plain text
  - Testing with known inputs
"""

import time
from typing import Any, Dict
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request

from services.scraper import PrivacyPolicyScraper
from services.preprocessor import PolicyPreprocessor
from services.llm_service import PrivacyAnalyzer
from services.grading_engine import GradingEngine
from services.verifier import ClaimVerifier
from database.db_manager import DatabaseManager
from utils.url_validator import URLValidator

analyze_bp = Blueprint("analyze", __name__)

# Module-level service instances (shared across requests — instantiated once)
_scraper   = PrivacyPolicyScraper()
_analyzer  = PrivacyAnalyzer()
_grader    = GradingEngine()
_verifier  = ClaimVerifier()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _error(message: str, code: int = 400) -> Any:
    return jsonify({"success": False, "error": message}), code


def _run_pipeline(
    policy_text: str,
    policy_url: str,
    company_name: str,
    sections: list,
    last_updated,
    t0: float,
) -> Dict[str, Any]:
    """
    OUR CUSTOM CODE — the shared analysis pipeline.

    Runs preprocessor → LLM → grader → verifier on already-retrieved text.
    Called by both /api/analyze (URL) and /api/analyze/text (paste).
    """
    # ── Step 1: Preprocess — OUR CUSTOM NLP ───────────────────────────────
    metrics = PolicyPreprocessor.process(
        policy_text,
        sections=sections,
        last_updated=last_updated,
    )

    # ── Step 2: LLM analysis (ONLY LLM CALL IN PROJECT) ───────────────────
    llm_findings = _analyzer.analyze_with_gemini(policy_text, metrics)

    # ── Step 3: Grade — OUR CUSTOM WEIGHTED SCORING ───────────────────────
    grading_result = _grader.calculate_grade(llm_findings, metrics)

    # ── Step 4: Claim verification — OUR CUSTOM FUZZY MATCH ───────────────
    verification = _verifier.verify_claims(llm_findings, policy_text)

    # ── Step 5: Cross-signal fusion — OUR CUSTOM MULTI-SOURCE ENGINE ──────
    # Fuses LLM + dark-pattern + GDPR-basis signals into CONFIRMED CRITICAL
    try:
        from analyzers.gdpr_classifier import GDPRLawfulBasisClassifier
        gdpr_basis = metrics.get("gdpr_basis", GDPRLawfulBasisClassifier.classify(policy_text))
    except Exception:
        gdpr_basis = []
    confirmed_critical = _verifier.cross_signal_escalation(llm_findings, metrics, gdpr_basis)
    if confirmed_critical:
        llm_findings.setdefault("confirmed_critical", confirmed_critical)

    # Inject verification confidence so trust_score is accurate

    grading_result["trust_score"] = _grader.calculate_trust_score(
        overall_score=grading_result["overall_score"],
        dark_pattern_score=metrics.get("dark_pattern_score", 0),
        verification_confidence=verification.get("overall_confidence", 0.5),
        red_flag_count=len(llm_findings.get("red_flags", [])),
    )

    processing_time = round(time.time() - t0, 2)

    result: Dict[str, Any] = {
        "url": policy_url,
        "company_name": company_name,
        "grade": grading_result["grade"],
        "overall_score": grading_result["overall_score"],
        "trust_score": grading_result["trust_score"],
        "dimension_scores": grading_result["dimension_scores"],
        "dimension_details": grading_result["dimension_details"],
        "reasoning": grading_result["reasoning"],
        "findings": llm_findings,
        "metrics": metrics,
        "red_flags": llm_findings.get("red_flags", []),
        "dark_pattern_score": metrics.get("dark_pattern_score", 0.0),
        "verification": verification,
        "scraped": {
            "title": company_name,
            "last_updated": last_updated,
            "word_count": metrics.get("word_count"),
            "section_count": len(sections),
        },
        "processing_time_seconds": processing_time,
        "cached": False,
    }

    # ── Save to database — OUR CUSTOM ORM ─────────────────────────────────
    try:
        DatabaseManager.save_analysis({
            "url": policy_url,
            "company_name": company_name,
            "policy_text": policy_text[:50_000],
            "grade": grading_result["grade"],
            "overall_score": grading_result["overall_score"],
            "trust_score": grading_result["trust_score"],
            "dimension_scores": grading_result["dimension_scores"],
            "findings": llm_findings,
            "metrics": {k: v for k, v in metrics.items() if k != "dark_patterns_found"},
            "red_flags": llm_findings.get("red_flags", []),
            "dark_pattern_score": metrics.get("dark_pattern_score", 0.0),
        })
    except Exception as exc:
        print(f"[analyze] DB save warning: {exc}")

    return result


# ---------------------------------------------------------------------------
# Route 1: POST /api/analyze  (URL-based)
# ---------------------------------------------------------------------------

@analyze_bp.route("/analyze", methods=["POST"])
def analyze():
    """
    POST /api/analyze
    Body: { "url": "https://example.com/privacy", "force_refresh": false }
    """
    body = request.get_json(silent=True) or {}
    url: str = (body.get("url") or "").strip()
    force_refresh: bool = bool(body.get("force_refresh", False))

    if not url:
        return _error("'url' field is required.")
    if not URLValidator.is_valid_url(url):
        return _error(f"Invalid URL: {url!r}")

    if not force_refresh:
        cached = DatabaseManager.get_analysis(url)
        if cached:
            cached["cached"] = True
            return jsonify({"success": True, "data": cached})

    t0 = time.time()
    try:
        scraped = _scraper.extract_policy(url)
        if not scraped:
            return _error(
                f"Could not retrieve a privacy policy from {url!r}. "
                "Please check the URL or try pasting the policy text directly using the 'Paste Text' tab.",
                422,
            )

        policy_text = scraped["policy_text"]
        sections = scraped.get("sections", [])
        last_updated = scraped.get("last_updated")
        policy_url = scraped["url"]
        company_name = (
            URLValidator.extract_domain(policy_url)
            .replace("www.", "").split(".")[0].capitalize()
        )

        result = _run_pipeline(policy_text, policy_url, company_name, sections, last_updated, t0)
        return jsonify({"success": True, "data": result})
    except Exception as exc:
        print(f"[analyze] Pipeline error for {url}: {exc}")
        import traceback
        traceback.print_exc()
        return _error(f"Analysis failed: {str(exc)}", 500)


# ---------------------------------------------------------------------------
# Route 2: POST /api/analyze/text  (paste-text mode — NEW S-TIER FEATURE)
# ---------------------------------------------------------------------------

@analyze_bp.route("/analyze/text", methods=["POST"])
def analyze_text():
    """
    POST /api/analyze/text
    Body: {
        "text":         "Full privacy policy text here...",
        "company_name": "Acme Corp",           (optional)
        "source_url":   "https://acme.com"     (optional, for attribution)
    }

    OUR CUSTOM CODE — Skips the scraper entirely. The full NLP + grading +
    verification pipeline runs identically to the URL path.

    Use cases:
    - Paywalled / login-required policy pages
    - PDF policies copied as plain text
    - Offline demo using samples/ text files
    - Testing with samples/google_privacy.txt, samples/facebook_privacy.txt etc.
    """
    body = request.get_json(silent=True) or {}
    policy_text: str = (body.get("text") or "").strip()
    company_name: str = (body.get("company_name") or "Pasted Policy").strip()
    source_url: str = (body.get("source_url") or "").strip()

    if not policy_text:
        return _error("'text' field is required and must not be empty.")

    word_count = len(policy_text.split())
    if word_count < 50:
        return _error(
            f"Text is too short ({word_count} words). "
            "Please paste the complete privacy policy text (minimum 50 words)."
        )
    if len(policy_text) > 500_000:
        return _error("Text exceeds 500,000 characters. Please paste a shorter excerpt.")

    # Synthetic URL for DB keying — deterministic hash of first 500 chars
    if source_url and URLValidator.is_valid_url(source_url):
        domain = URLValidator.extract_domain(source_url)
        policy_url = f"paste://{domain}/{hash(policy_text[:500]) & 0xFFFFFF:06x}"
        if not company_name or company_name == "Pasted Policy":
            company_name = domain.replace("www.", "").split(".")[0].capitalize()
    else:
        policy_url = f"paste://direct/{hash(policy_text[:500]) & 0xFFFFFF:06x}"

    t0 = time.time()
    try:
        result = _run_pipeline(policy_text, policy_url, company_name, [], None, t0)
        result["input_mode"] = "text"
        result["word_count_input"] = word_count
        return jsonify({"success": True, "data": result})
    except Exception as exc:
        print(f"[analyze_text] Pipeline error: {exc}")
        import traceback
        traceback.print_exc()
        return _error(f"Analysis failed: {str(exc)}", 500)


# ---------------------------------------------------------------------------
# Route 3: GET /api/history/<domain>  (policy version diff tracker — NEW)
# ---------------------------------------------------------------------------

@analyze_bp.route("/history/<path:domain>", methods=["GET"])
def policy_history(domain: str):
    """
    GET /api/history/<domain>
    Example: GET /api/history/google.com

    Returns all stored analyses for a domain ordered by date.
    OUR CUSTOM CODE: computes grade & score deltas between versions — no LLM.

    This endpoint makes the database layer meaningful: you can see how a
    company's privacy practices changed over time.
    """
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
    analyses = DatabaseManager.get_analyses_by_domain(domain)

    if not analyses:
        return jsonify({
            "success": True,
            "data": {
                "domain": domain,
                "count": 0,
                "versions": [],
                "message": f"No analyses found for '{domain}'. Analyse a policy first.",
            },
        })

    versions = []
    for i, row in enumerate(analyses):
        version: Dict[str, Any] = {
            "version": i + 1,
            "date": row.get("created_at"),
            "url": row.get("url"),
            "grade": row.get("grade"),
            "overall_score": row.get("overall_score"),
            "trust_score": row.get("trust_score"),
            "dimension_scores": row.get("dimension_scores", {}),
            "red_flag_count": len(row.get("red_flags", [])),
            "dark_pattern_score": row.get("dark_pattern_score", 0),
            "delta": None,
        }

        if i > 0:
            prev = analyses[i - 1]
            score_delta = round(
                (row.get("overall_score") or 0) - (prev.get("overall_score") or 0), 2
            )
            grade_changed = row.get("grade") != prev.get("grade")

            # Per-dimension deltas — OUR CUSTOM DIFF LOGIC
            dim_deltas = {}
            for dim, curr_score in (row.get("dimension_scores") or {}).items():
                prev_score = (prev.get("dimension_scores") or {}).get(dim, curr_score)
                diff = round((curr_score or 0) - (prev_score or 0), 2)
                if abs(diff) >= 2.0:
                    dim_deltas[dim] = {
                        "delta": diff,
                        "direction": "improved" if diff > 0 else "declined",
                    }

            flag_delta = len(row.get("red_flags", [])) - len(prev.get("red_flags", []))

            version["delta"] = {
                "score_delta": score_delta,
                "grade_changed": grade_changed,
                "previous_grade": prev.get("grade"),
                "direction": (
                    "improved" if score_delta > 0
                    else "declined" if score_delta < 0
                    else "unchanged"
                ),
                "dimension_deltas": dim_deltas,
                "red_flag_delta": flag_delta,
                "summary": _diff_summary(prev, row, score_delta, grade_changed, flag_delta),
            }

        versions.append(version)

    return jsonify({
        "success": True,
        "data": {
            "domain": domain,
            "count": len(versions),
            "latest_grade": versions[-1]["grade"] if versions else None,
            "versions": versions,
        },
    })


def _diff_summary(prev: dict, curr: dict, score_delta: float, grade_changed: bool, flag_delta: int) -> str:
    """
    OUR CUSTOM CODE — generate a plain-English changelog sentence.
    Example: "Grade declined from B to C (-8.3 pts). 2 new red flags detected."
    """
    parts = []
    if grade_changed:
        parts.append(
            f"Grade {'improved' if score_delta > 0 else 'declined'} "
            f"from {prev.get('grade')} to {curr.get('grade')} "
            f"({'+' if score_delta > 0 else ''}{score_delta:.1f} pts)"
        )
    elif abs(score_delta) >= 1.0:
        parts.append(
            f"Score {'increased' if score_delta > 0 else 'decreased'} "
            f"by {abs(score_delta):.1f} points"
        )
    else:
        parts.append("Score unchanged")

    if flag_delta > 0:
        parts.append(f"{flag_delta} new red flag{'s' if flag_delta != 1 else ''} detected")
    elif flag_delta < 0:
        parts.append(f"{abs(flag_delta)} fewer red flag{'s' if flag_delta != -1 else ''}")

    return ". ".join(parts) + "."
