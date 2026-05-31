"""tests/test_verifier.py — Tests for ClaimVerifier."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from services.verifier import ClaimVerifier

CORPUS = (
    "We collect your email address for account registration. "
    "We share anonymised analytics data with Google Analytics. "
    "You have the right to access your personal data at any time by emailing privacy@example.com. "
    "You may request deletion of your account within 30 days. "
    "Data portability is available via the dashboard export feature."
)

LLM_FINDINGS = {
    "data_collected": [
        {"type": "email address", "purpose": "account registration", "sensitivity": "medium"},
        {"type": "purchase history", "purpose": "recommendations", "sensitivity": "medium"},  # not in corpus
    ],
    "data_shared": [
        {"recipient": "Google Analytics", "data_type": "analytics data", "opt_out_available": True},
        {"recipient": "TikTok Ads", "data_type": "behavioral data", "opt_out_available": False},  # hallucination
    ],
    "user_rights": {
        "access": "email privacy@example.com",
        "deletion": "request within 30 days",
        "portability": "dashboard export",
        "correction": "no correction mechanism",  # not in corpus
    },
    "red_flags": [
        {"issue": "Unclear data retention", "quote": "data retained for an indefinite period", "severity": "high"},  # not in corpus
        {"issue": "Google Analytics data sharing", "quote": "share anonymised analytics data with Google Analytics", "severity": "low"},
    ],
}

class TestVerifyClaims:
    def test_returns_required_keys(self):
        result = ClaimVerifier.verify_claims(LLM_FINDINGS, CORPUS)
        for k in ["data_collected_verified","data_shared_verified","user_rights_verified",
                  "red_flags_verified","overall_confidence","hallucination_count","summary"]:
            assert k in result, f"Missing: {k}"

    def test_email_claim_supported(self):
        result = ClaimVerifier.verify_claims(LLM_FINDINGS, CORPUS)
        email_claim = next((c for c in result["data_collected_verified"]
                            if "email" in c.get("claim","").lower()), None)
        assert email_claim is not None
        assert email_claim["supported"] is True

    def test_hallucination_flagged(self):
        result = ClaimVerifier.verify_claims(LLM_FINDINGS, CORPUS)
        assert result["hallucination_count"] >= 1

    def test_confidence_range(self):
        result = ClaimVerifier.verify_claims(LLM_FINDINGS, CORPUS)
        assert 0.0 <= result["overall_confidence"] <= 1.0

    def test_google_analytics_exact_match(self):
        result = ClaimVerifier.verify_claims(LLM_FINDINGS, CORPUS)
        ga_flag = next((f for f in result["red_flags_verified"]
                        if "analytics" in f.get("claim","").lower()), None)
        if ga_flag:
            assert ga_flag["confidence"] > 0.5

    def test_empty_findings_no_crash(self):
        result = ClaimVerifier.verify_claims({}, CORPUS)
        assert result["total_claims"] == 0
        assert result["summary"] == "No claims to verify."

    def test_empty_corpus_all_flagged(self):
        result = ClaimVerifier.verify_claims(LLM_FINDINGS, "")
        assert result["hallucination_count"] > 0

    def test_verified_items_have_keys(self):
        result = ClaimVerifier.verify_claims(LLM_FINDINGS, CORPUS)
        for item in result["data_collected_verified"]:
            for k in ["claim","supported","confidence","hallucination_risk"]:
                assert k in item, f"Missing key {k} in verified item"

    def test_user_rights_dict_structure(self):
        result = ClaimVerifier.verify_claims(LLM_FINDINGS, CORPUS)
        rights = result["user_rights_verified"]
        assert isinstance(rights, dict)
        for right, val in rights.items():
            assert "confidence" in val
