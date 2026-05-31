"""
database/seed_data.py — Pre-populate the database with benchmark data.

Run once:
    cd backend
    python -c "from database.seed_data import seed_all; seed_all()"

Contains synthetic (but realistic) data for 12 major companies,
grouped into 4 industries.  Averages are computed automatically.
"""

from typing import Dict, List
from database.db_manager import DatabaseManager

# ---------------------------------------------------------------------------
# Synthetic company data
# ---------------------------------------------------------------------------

COMPANY_DATA: List[Dict] = [
    # ── TECHNOLOGY ──────────────────────────────────────────────────────────
    {
        "company": "Google",
        "industry": "Technology",
        "url": "https://policies.google.com/privacy",
        "grade": "B",
        "overall_score": 82.0,
        "dimension_scores": {
            "data_collection_transparency": 85,
            "sharing_disclosure": 80,
            "user_rights": 88,
            "readability": 65,
            "compliance": 92,
        },
        "red_flags": [
            {"issue": "Extensive data collection across all Google services",
             "severity": "medium",
             "explanation": "Google collects data across Search, Maps, Gmail, YouTube and more."},
            {"issue": "Vague 'improve our services' justification",
             "severity": "low",
             "explanation": "'Improving services' is used as a catch-all purpose."},
        ],
    },
    {
        "company": "Facebook / Meta",
        "industry": "Technology",
        "url": "https://www.facebook.com/policy.php",
        "grade": "C",
        "overall_score": 68.5,
        "dimension_scores": {
            "data_collection_transparency": 72,
            "sharing_disclosure": 60,
            "user_rights": 70,
            "readability": 55,
            "compliance": 75,
        },
        "red_flags": [
            {"issue": "Data shared with undisclosed 'partners'",
             "severity": "high",
             "explanation": "The policy does not enumerate all third parties receiving data."},
            {"issue": "Implied consent via platform use",
             "severity": "high",
             "explanation": "Continued platform use is treated as consent to data processing."},
            {"issue": "Cross-app tracking without explicit consent",
             "severity": "high",
             "explanation": "Meta tracks users across Instagram, WhatsApp, and Facebook."},
        ],
    },
    {
        "company": "Apple",
        "industry": "Technology",
        "url": "https://www.apple.com/legal/privacy/",
        "grade": "A",
        "overall_score": 91.0,
        "dimension_scores": {
            "data_collection_transparency": 93,
            "sharing_disclosure": 90,
            "user_rights": 95,
            "readability": 85,
            "compliance": 92,
        },
        "red_flags": [
            {"issue": "iCloud data subject to US law",
             "severity": "low",
             "explanation": "Cloud data stored in the US may be subject to US government requests."},
        ],
    },
    {
        "company": "Microsoft",
        "industry": "Technology",
        "url": "https://privacy.microsoft.com/en-us/privacystatement",
        "grade": "B",
        "overall_score": 84.0,
        "dimension_scores": {
            "data_collection_transparency": 86,
            "sharing_disclosure": 83,
            "user_rights": 88,
            "readability": 72,
            "compliance": 91,
        },
        "red_flags": [
            {"issue": "Very long policy (15,000+ words)",
             "severity": "medium",
             "explanation": "Length makes comprehension difficult for average users."},
        ],
    },

    # ── E-COMMERCE ──────────────────────────────────────────────────────────
    {
        "company": "Amazon",
        "industry": "E-Commerce",
        "url": "https://www.amazon.com/gp/help/customer/display.html?nodeId=468496",
        "grade": "C",
        "overall_score": 71.0,
        "dimension_scores": {
            "data_collection_transparency": 75,
            "sharing_disclosure": 65,
            "user_rights": 70,
            "readability": 60,
            "compliance": 85,
        },
        "red_flags": [
            {"issue": "Alexa voice data retention",
             "severity": "high",
             "explanation": "Voice recordings may be retained indefinitely by default."},
            {"issue": "Third-party seller data access",
             "severity": "medium",
             "explanation": "Sellers on Amazon's marketplace receive customer data."},
        ],
    },

    # ── SOCIAL MEDIA ────────────────────────────────────────────────────────
    {
        "company": "Twitter / X",
        "industry": "Social Media",
        "url": "https://twitter.com/en/privacy",
        "grade": "C",
        "overall_score": 65.0,
        "dimension_scores": {
            "data_collection_transparency": 68,
            "sharing_disclosure": 58,
            "user_rights": 68,
            "readability": 60,
            "compliance": 71,
        },
        "red_flags": [
            {"issue": "Policy updated frequently without clear notification",
             "severity": "medium",
             "explanation": "Unilateral updates may invalidate previous consent."},
            {"issue": "Inferred data collection",
             "severity": "medium",
             "explanation": "Twitter infers interests and demographics from behaviour."},
        ],
    },
    {
        "company": "LinkedIn",
        "industry": "Social Media",
        "url": "https://www.linkedin.com/legal/privacy-policy",
        "grade": "B",
        "overall_score": 76.0,
        "dimension_scores": {
            "data_collection_transparency": 80,
            "sharing_disclosure": 72,
            "user_rights": 78,
            "readability": 68,
            "compliance": 82,
        },
        "red_flags": [
            {"issue": "Profile data used for ad targeting",
             "severity": "medium",
             "explanation": "Professional data is used for commercial advertising."},
        ],
    },
    {
        "company": "Reddit",
        "industry": "Social Media",
        "url": "https://www.reddit.com/policies/privacy-policy",
        "grade": "C",
        "overall_score": 67.0,
        "dimension_scores": {
            "data_collection_transparency": 70,
            "sharing_disclosure": 60,
            "user_rights": 68,
            "readability": 65,
            "compliance": 72,
        },
        "red_flags": [
            {"issue": "Posts are public and indexed by search engines",
             "severity": "medium",
             "explanation": "User content may appear in Google results indefinitely."},
        ],
    },
    {
        "company": "TikTok",
        "industry": "Social Media",
        "url": "https://www.tiktok.com/legal/page/us/privacy-policy/en",
        "grade": "D",
        "overall_score": 55.0,
        "dimension_scores": {
            "data_collection_transparency": 58,
            "sharing_disclosure": 48,
            "user_rights": 55,
            "readability": 50,
            "compliance": 64,
        },
        "red_flags": [
            {"issue": "Data shared with ByteDance (Chinese parent company)",
             "severity": "critical",
             "explanation": "Cross-border data transfer to China raises regulatory concerns."},
            {"issue": "Biometric data collection (face and voice)",
             "severity": "critical",
             "explanation": "TikTok collects biometric identifiers in some jurisdictions."},
            {"issue": "Children's data protections insufficient",
             "severity": "high",
             "explanation": "App is popular with minors; COPPA compliance has been questioned."},
        ],
    },

    # ── ENTERTAINMENT ───────────────────────────────────────────────────────
    {
        "company": "Netflix",
        "industry": "Entertainment",
        "url": "https://help.netflix.com/legal/privacy",
        "grade": "B",
        "overall_score": 78.0,
        "dimension_scores": {
            "data_collection_transparency": 82,
            "sharing_disclosure": 75,
            "user_rights": 78,
            "readability": 72,
            "compliance": 83,
        },
        "red_flags": [
            {"issue": "Viewing history used for ad targeting (ad tier)",
             "severity": "medium",
             "explanation": "Ad-supported tier shares viewing behaviour with advertisers."},
        ],
    },
    {
        "company": "Spotify",
        "industry": "Entertainment",
        "url": "https://www.spotify.com/us/legal/privacy-policy/",
        "grade": "C",
        "overall_score": 70.0,
        "dimension_scores": {
            "data_collection_transparency": 75,
            "sharing_disclosure": 65,
            "user_rights": 72,
            "readability": 62,
            "compliance": 76,
        },
        "red_flags": [
            {"issue": "Microphone and sensor access",
             "severity": "high",
             "explanation": "Spotify may access microphone data with device permission."},
        ],
    },

    # ── PRODUCTIVITY ────────────────────────────────────────────────────────
    {
        "company": "Zoom",
        "industry": "Productivity",
        "url": "https://zoom.us/privacy",
        "grade": "C",
        "overall_score": 66.0,
        "dimension_scores": {
            "data_collection_transparency": 70,
            "sharing_disclosure": 60,
            "user_rights": 65,
            "readability": 58,
            "compliance": 77,
        },
        "red_flags": [
            {"issue": "Meeting content used for AI training (previously)",
             "severity": "critical",
             "explanation": "Zoom updated policy after controversy over AI model training."},
            {"issue": "Attention tracking feature",
             "severity": "high",
             "explanation": "Host can see if participant's attention is on Zoom window."},
        ],
    },
]


# ---------------------------------------------------------------------------
# Industry aggregation helper
# ---------------------------------------------------------------------------

_GRADE_TO_NUM = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}
_NUM_TO_GRADE = {v: k for k, v in _GRADE_TO_NUM.items()}
_DIMENSIONS = [
    "data_collection_transparency",
    "sharing_disclosure",
    "user_rights",
    "readability",
    "compliance",
]


def _aggregate_industry(industry: str) -> Dict:
    filtered = [c for c in COMPANY_DATA if c["industry"] == industry]
    if not filtered:
        return {}

    avg_numeric = sum(_GRADE_TO_NUM.get(c["grade"], 3) for c in filtered) / len(filtered)
    avg_grade = _NUM_TO_GRADE[round(avg_numeric)]

    avg_scores = {
        dim: round(sum(c["dimension_scores"].get(dim, 0) for c in filtered) / len(filtered), 1)
        for dim in _DIMENSIONS
    }

    return {
        "avg_grade": avg_grade,
        "avg_scores": avg_scores,
        "sample_size": len(filtered),
    }


# ---------------------------------------------------------------------------
# Public seed function
# ---------------------------------------------------------------------------

def seed_all() -> None:
    """
    Seed both the analyses table (historical data) and benchmarks table.

    Safe to call multiple times — rows are upserted.
    """
    DatabaseManager.init_db()

    # Seed analyses
    for company in COMPANY_DATA:
        try:
            DatabaseManager.save_analysis({
                "url": company["url"],
                "company_name": company["company"],
                "policy_text": f"[Seed data for {company['company']}]",
                "grade": company["grade"],
                "overall_score": company["overall_score"],
                "dimension_scores": company["dimension_scores"],
                "findings": {},
                "metrics": {},
                "red_flags": company.get("red_flags", []),
                "dark_pattern_score": 0.0,
            })
        except Exception as exc:
            print(f"[seed] Warning seeding {company['company']}: {exc}")

    # Seed benchmarks
    industries = set(c["industry"] for c in COMPANY_DATA)
    for ind in industries:
        agg = _aggregate_industry(ind)
        if agg:
            try:
                DatabaseManager.update_or_create_benchmark(
                    industry=ind,
                    avg_grade=agg["avg_grade"],
                    avg_scores=agg["avg_scores"],
                    sample_size=agg["sample_size"],
                )
            except Exception as exc:
                print(f"[seed] Warning seeding benchmark {ind}: {exc}")

    print("✅ Seed data loaded successfully.")
    print(f"   Analyses : {len(COMPANY_DATA)}")
    print(f"   Industries: {len(industries)}")


if __name__ == "__main__":
    seed_all()
