"""
routes/compare.py — POST /api/compare endpoint.

Analyses two privacy policies side-by-side and returns a comparison.
"""

from flask import Blueprint, jsonify, request

from services.scraper import PrivacyPolicyScraper
from services.preprocessor import PolicyPreprocessor
from services.llm_service import PrivacyAnalyzer
from services.grading_engine import GradingEngine
from services.verifier import ClaimVerifier
from database.db_manager import DatabaseManager
from utils.url_validator import URLValidator

compare_bp = Blueprint("compare", __name__)

_scraper  = PrivacyPolicyScraper()
_analyzer = PrivacyAnalyzer()
_grader   = GradingEngine()
_verifier = ClaimVerifier()


def _analyse_single(url: str) -> dict:
    """Run the full pipeline for one URL. Returns result dict."""
    try:
        # Try cache first
        cached = DatabaseManager.get_analysis(url)
        if cached:
            return cached

        scraped = _scraper.extract_policy(url)
        if not scraped:
            return {"error": f"Could not scrape {url}"}

        metrics     = PolicyPreprocessor.process(scraped["policy_text"], scraped.get("sections", []), scraped.get("last_updated"))
        llm         = _analyzer.analyze_with_gemini(scraped["policy_text"], metrics)
        grading     = _grader.calculate_grade(llm, metrics)
        verification= _verifier.verify_claims(llm, scraped["policy_text"])
        
        # Calculate trust score
        trust_score = _grader.calculate_trust_score(
            overall_score=grading["overall_score"],
            dark_pattern_score=metrics.get("dark_pattern_score", 0),
            verification_confidence=verification.get("overall_confidence", 0.5),
            red_flag_count=len(llm.get("red_flags", [])),
        )
        company     = URLValidator.extract_domain(url).replace("www.", "").split(".")[0].capitalize()

        result = {
            "url": url,
            "company_name": company,
            "grade": grading["grade"],
            "overall_score": grading["overall_score"],
            "trust_score": trust_score,
            "dimension_scores": grading["dimension_scores"],
            "findings": llm,
            "metrics": metrics,
            "red_flags": llm.get("red_flags", []),
            "dark_pattern_score": metrics.get("dark_pattern_score", 0.0),
            "verification": verification,
        }

        # ── Save to database ──
        try:
            DatabaseManager.save_analysis({
                "url": url,
                "company_name": company,
                "policy_text": scraped["policy_text"][:50_000],
                "grade": grading["grade"],
                "overall_score": grading["overall_score"],
                "trust_score": trust_score,
                "dimension_scores": grading["dimension_scores"],
                "findings": llm,
                "metrics": metrics,
                "red_flags": llm.get("red_flags", []),
                "dark_pattern_score": metrics.get("dark_pattern_score", 0.0),
            })
        except Exception as exc:
            print(f"[compare] DB save warning: {exc}")

        return result
    except Exception as exc:
        print(f"[compare] Error analysing {url}: {exc}")
        return {"error": str(exc)}


def _key_differences(a: dict, b: dict) -> list:
    """Highlight significant differences in dimension scores."""
    diffs = []
    a_dims = a.get("dimension_scores", {})
    b_dims = b.get("dimension_scores", {})
    for dim in a_dims:
        score_a = a_dims.get(dim, 0)
        score_b = b_dims.get(dim, 0)
        delta = score_b - score_a
        if abs(delta) >= 10:
            winner = b.get("company_name") if delta > 0 else a.get("company_name")
            diffs.append({
                "dimension": dim.replace("_", " ").title(),
                "score_a": score_a,
                "score_b": score_b,
                "delta": round(delta, 1),
                "better": winner,
            })
    return sorted(diffs, key=lambda x: abs(x["delta"]), reverse=True)


@compare_bp.route("/compare", methods=["POST"])
def compare():
    """
    POST /api/compare
    Body: { "urls": ["https://a.com/privacy", "https://b.com/privacy"] }
    """
    body = request.get_json(silent=True) or {}
    urls = body.get("urls", [])

    if not isinstance(urls, list) or len(urls) != 2:
        return jsonify({"success": False, "error": "'urls' must be a list of exactly 2 URLs."}), 400

    url_a, url_b = urls[0].strip(), urls[1].strip()

    for u in (url_a, url_b):
        if not URLValidator.is_valid_url(u):
            return jsonify({"success": False, "error": f"Invalid URL: {u!r}"}), 400

    result_a = _analyse_single(url_a)
    result_b = _analyse_single(url_b)

    if "error" in result_a:
        return jsonify({"success": False, "error": result_a["error"]}), 422
    if "error" in result_b:
        return jsonify({"success": False, "error": result_b["error"]}), 422

    # Benchmarks for context
    benchmarks = DatabaseManager.compare_to_benchmarks(result_a.get("dimension_scores", {}))

    comparison = {
        "policy_a": {
            "url": result_a["url"],
            "company": result_a["company_name"],
            "grade": result_a["grade"],
            "overall_score": result_a["overall_score"],
            "dimension_scores": result_a["dimension_scores"],
            "red_flag_count": len(result_a.get("red_flags", [])),
            "dark_pattern_score": result_a.get("dark_pattern_score", 0),
            "trust_score": result_a.get("trust_score", 0),
        },
        "policy_b": {
            "url": result_b["url"],
            "company": result_b["company_name"],
            "grade": result_b["grade"],
            "overall_score": result_b["overall_score"],
            "dimension_scores": result_b["dimension_scores"],
            "red_flag_count": len(result_b.get("red_flags", [])),
            "dark_pattern_score": result_b.get("dark_pattern_score", 0),
            "trust_score": result_b.get("trust_score", 0),
        },
        "winner": (result_a["company_name"] if result_a["overall_score"] >= result_b["overall_score"]
                   else result_b["company_name"]),
        "score_delta": round(result_a["overall_score"] - result_b["overall_score"], 2),
        "key_differences": _key_differences(result_a, result_b),
        "benchmark_comparison": benchmarks,
    }

    return jsonify({"success": True, "data": comparison})
