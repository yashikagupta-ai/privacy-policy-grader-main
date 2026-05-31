"""
routes/benchmarks.py — GET /api/benchmarks and /api/benchmarks/<industry>.

Returns industry-level benchmark data from the database.
"""

from flask import Blueprint, jsonify

from database.db_manager import DatabaseManager

benchmarks_bp = Blueprint("benchmarks", __name__)


@benchmarks_bp.route("/benchmarks", methods=["GET"])
def get_all_benchmarks():
    """
    GET /api/benchmarks
    Returns all industry benchmarks, grade distribution, and recent analyses.
    """
    benchmarks = DatabaseManager.get_industry_averages()
    grade_distribution = DatabaseManager.get_grade_distribution()
    recent = DatabaseManager.get_recent_analyses(limit=5)

    # Strip policy_text from recent (too large)
    for r in recent:
        r.pop("policy_text", None)
        r.pop("findings", None)

    # Compute top/bottom performers from seed data
    all_analyses = DatabaseManager.get_recent_analyses(limit=50)
    sorted_by_score = sorted(
        [a for a in all_analyses if a.get("overall_score")],
        key=lambda x: x["overall_score"],
        reverse=True,
    )
    top_performers    = sorted_by_score[:3]
    bottom_performers = sorted_by_score[-3:] if len(sorted_by_score) >= 3 else sorted_by_score

    for a in top_performers + bottom_performers:
        a.pop("policy_text", None)
        a.pop("findings", None)

    return jsonify({
        "success": True,
        "data": {
            "benchmarks": benchmarks,
            "grade_distribution": grade_distribution,
            "total_analysed": DatabaseManager.count_analyses(),
            "recent_analyses": recent,
            "top_performers": top_performers,
            "bottom_performers": list(reversed(bottom_performers)),
        },
    })


@benchmarks_bp.route("/benchmarks/<industry>", methods=["GET"])
def get_industry_benchmark(industry: str):
    """
    GET /api/benchmarks/<industry>
    Returns benchmark data for a specific industry.
    """
    bench = DatabaseManager.get_benchmarks(industry)
    if not bench:
        return jsonify({
            "success": False,
            "error": f"No benchmark data found for industry: {industry!r}",
        }), 404

    return jsonify({"success": True, "data": bench})
