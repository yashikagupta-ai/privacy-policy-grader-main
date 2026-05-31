"""tests/test_jargon_detector.py — Tests for LegalJargonDetector."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from analyzers.jargon_detector import LegalJargonDetector

LEGAL_TEXT = (
    "This policy describes how we use cookies and personal data. "
    "We act as a data controller and may share data with service providers under "
    "legitimate interest. You have the right to erasure under GDPR. "
    "Jurisdiction for any arbitration shall be determined by the governing law."
)
PLAIN_TEXT = "We collect your name and email to send you a newsletter. You can unsubscribe any time."

class TestDetect:
    def test_legal_text_has_jargon(self):
        result = LegalJargonDetector.detect(LEGAL_TEXT)
        assert result["jargon_count"] > 0

    def test_plain_text_low_density(self):
        result = LegalJargonDetector.detect(PLAIN_TEXT)
        assert result["density_percent"] < 10

    def test_gdpr_detected(self):
        result = LegalJargonDetector.detect(LEGAL_TEXT)
        found_terms = [t["term"] for t in result["terms_found"]]
        assert "gdpr" in found_terms

    def test_categories_present(self):
        result = LegalJargonDetector.detect(LEGAL_TEXT)
        cats = result["terms_by_category"]
        assert any(cat in cats for cat in ["legal", "privacy", "technical"])

    def test_density_percent_range(self):
        result = LegalJargonDetector.detect(LEGAL_TEXT)
        assert 0 <= result["density_percent"] <= 100

    def test_terms_found_structure(self):
        result = LegalJargonDetector.detect(LEGAL_TEXT)
        for term in result["terms_found"]:
            assert "term" in term
            assert "category" in term
            assert "count" in term
            assert "explanation" in term

    def test_empty_text(self):
        result = LegalJargonDetector.detect("")
        assert result["jargon_count"] == 0

    def test_returns_top_terms(self):
        result = LegalJargonDetector.detect(LEGAL_TEXT)
        assert isinstance(result["top_terms"], list)
        assert len(result["top_terms"]) <= 10

class TestPerSection:
    def test_per_section_structure(self):
        sections = [
            {"title": "Collection", "text": LEGAL_TEXT},
            {"title": "Plain", "text": PLAIN_TEXT},
        ]
        results = LegalJargonDetector.detect_per_section(sections)
        assert len(results) == 2
        for r in results:
            assert "section_title" in r
            assert "jargon_count" in r
            assert "density_percent" in r
