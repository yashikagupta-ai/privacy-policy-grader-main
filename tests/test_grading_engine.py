"""tests/test_grading_engine.py — Tests for GradingEngine."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from services.grading_engine import GradingEngine

PERFECT_LLM = {
    "data_collected": [
        {"type": t, "purpose": "stated", "sensitivity": "low"}
        for t in ["email","name","ip","device","location","cookies","phone","age"]
    ],
    "data_shared": [
        {"recipient": "Stripe (payment)", "data_type": "payment info", "opt_out_available": True},
        {"recipient": "Google Analytics", "data_type": "usage data", "opt_out_available": True},
    ],
    "user_rights": {"access": "yes", "deletion": "yes", "portability": "yes", "correction": "yes"},
    "red_flags": [],
    "compliance_indicators": ["GDPR compliant", "CCPA compliant", "COPPA section present"],
    "summary": "Excellent policy.",
}

PERFECT_METRICS = {
    "word_count": 2000, "sentence_count": 150, "avg_sentence_length": 13,
    "flesch_reading_ease": 70, "flesch_kincaid_grade": 8,
    "jargon_density": 5, "section_count": 12,
    "opt_out_presence": True, "structure_score": 80,
    "clause_completeness_score": 90,
    "data_types_found": ["email","name","ip","device"],
    "third_party_mentions": 5, "user_rights_mentions": 8,
    "gdpr_mentions": {"mentioned": True, "count": 3},
    "ccpa_mentions": {"mentioned": True, "count": 2},
    "children_privacy": {"mentioned": True, "coppa_referenced": True},
    "data_sale": {"sells_data": False},
}

EMPTY_LLM = {"data_collected": [], "data_shared": [], "user_rights": {}, "red_flags": [], "compliance_indicators": [], "summary": ""}
EMPTY_METRICS = {k: 0 for k in PERFECT_METRICS}

class TestCalculateGrade:
    def test_perfect_inputs_high_score(self):
        result = GradingEngine.calculate_grade(PERFECT_LLM, PERFECT_METRICS)
        assert result["overall_score"] >= 80, (
            f"Perfect inputs should score ≥80/100. Got {result['overall_score']:.1f}. "
            "If this fails, re-check the grading dimension weights or sub-score formulas."
        )

    def test_returns_required_keys(self):
        result = GradingEngine.calculate_grade(PERFECT_LLM, PERFECT_METRICS)
        for key in ["grade", "overall_score", "dimension_scores", "reasoning"]:
            assert key in result, f"Missing: {key}"

    def test_grade_is_valid_letter(self):
        result = GradingEngine.calculate_grade(PERFECT_LLM, PERFECT_METRICS)
        assert result["grade"] in ("A", "B", "C", "D", "F")

    def test_score_range(self):
        result = GradingEngine.calculate_grade(PERFECT_LLM, PERFECT_METRICS)
        assert 0 <= result["overall_score"] <= 100

    def test_five_dimensions_returned(self):
        result = GradingEngine.calculate_grade(PERFECT_LLM, PERFECT_METRICS)
        dims = result["dimension_scores"]
        expected_dims = ["data_collection_transparency","sharing_disclosure","user_rights","readability","compliance"]
        for d in expected_dims:
            assert d in dims

    def test_all_dimension_scores_in_range(self):
        result = GradingEngine.calculate_grade(PERFECT_LLM, PERFECT_METRICS)
        for val in result["dimension_scores"].values():
            assert 0 <= val <= 100

    def test_empty_inputs_no_crash(self):
        result = GradingEngine.calculate_grade(EMPTY_LLM, EMPTY_METRICS)
        assert "grade" in result
        assert result["grade"] in ("A","B","C","D","F")

    def test_grade_boundaries(self):
        from config import Config
        assert Config.grade_letter(95) == "A"
        assert Config.grade_letter(85) == "B"
        assert Config.grade_letter(75) == "C"
        assert Config.grade_letter(65) == "D"
        assert Config.grade_letter(50) == "F"

    def test_reasoning_has_five_keys(self):
        result = GradingEngine.calculate_grade(PERFECT_LLM, PERFECT_METRICS)
        assert len(result["reasoning"]) == 5
