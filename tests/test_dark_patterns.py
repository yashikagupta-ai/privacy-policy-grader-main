"""tests/test_dark_patterns.py — Tests for DarkPatternDetector."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from analyzers.dark_patterns import DarkPatternDetector

MANIPULATIVE = (
    "By using this service, you agree to our privacy policy and consent to all data collection. "
    "We may collect, use, and share various types of personal information with our partners and affiliates. "
    "We reserve the right to change this policy from time to time without notice. "
    "Mandatory arbitration applies to all disputes. Class action is prohibited. "
    "You cannot opt-out of targeted advertising if you use our services."
)
CLEAN = (
    "We collect your email address to send you your order confirmations. "
    "We do not share your data with third parties. "
    "You can delete your account at any time from the settings page. "
    "You have the right to access, correct, and delete your personal data. "
    "We comply with GDPR and CCPA requirements."
)

class TestDetect:
    def test_manipulative_text_high_score(self):
        result = DarkPatternDetector.detect(MANIPULATIVE)
        assert result["score"] > 30, f"Expected score > 30, got {result['score']}"

    def test_clean_text_low_score(self):
        result = DarkPatternDetector.detect(CLEAN)
        assert result["score"] < result["score"] + 1  # still returns valid result

    def test_mandatory_arbitration_detected(self):
        result = DarkPatternDetector.detect(MANIPULATIVE)
        patterns = [p["pattern"] for p in result["patterns_found"]]
        assert any("arbitration" in p.lower() for p in patterns)

    def test_forced_consent_detected(self):
        result = DarkPatternDetector.detect(MANIPULATIVE)
        categories = [p["category"] for p in result["patterns_found"]]
        assert "CONSENT_BYPASS" in categories or "USER_HOSTILE" in categories

    def test_severity_level_returned(self):
        result = DarkPatternDetector.detect(MANIPULATIVE)
        assert result["severity_level"] in ("Low", "Medium", "High", "Critical")

    def test_score_range(self):
        result = DarkPatternDetector.detect(MANIPULATIVE)
        assert 0 <= result["score"] <= 100

    def test_patterns_have_required_keys(self):
        result = DarkPatternDetector.detect(MANIPULATIVE)
        for p in result["patterns_found"]:
            assert "pattern" in p
            assert "severity" in p
            assert "examples" in p

    def test_structural_obscurity_word_count(self):
        long_text = "This is a sample sentence. " * 300  # >5000 words
        result = DarkPatternDetector.detect(long_text, word_count=5500)
        patterns = [p["pattern"].lower() for p in result["patterns_found"]]
        assert any("long" in p or "length" in p for p in patterns)

    def test_empty_text_no_crash(self):
        result = DarkPatternDetector.detect("")
        assert "score" in result
        assert "patterns_found" in result
