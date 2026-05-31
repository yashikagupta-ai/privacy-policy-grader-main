"""tests/test_readability.py — Test suite for ReadabilityAnalyzer."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from analyzers.readability import ReadabilityAnalyzer

SIMPLE_TEXT = "The cat sat on the mat. It was a fat cat. The cat liked hats."
LEGAL_TEXT  = (
    "The indemnification of the aforementioned parties pursuant to the "
    "jurisdictional framework established by the arbitration clause constitutes "
    "a binding contractual obligation with respect to personally identifiable "
    "information and associated data protection regulations as defined herein."
)

class TestFleschReadingEase:
    def test_simple_text_high_score(self):
        score = ReadabilityAnalyzer.flesch_reading_ease(SIMPLE_TEXT)
        assert score > 60, f"Simple text should score >60, got {score}"

    def test_legal_text_low_score(self):
        score = ReadabilityAnalyzer.flesch_reading_ease(LEGAL_TEXT)
        assert score < 40, f"Legal text should score <40, got {score}"

    def test_returns_float(self):
        assert isinstance(ReadabilityAnalyzer.flesch_reading_ease(SIMPLE_TEXT), float)

    def test_range_is_reasonable(self):
        score = ReadabilityAnalyzer.flesch_reading_ease(SIMPLE_TEXT)
        assert -50 <= score <= 130

class TestFleschKincaidGrade:
    def test_simple_text_low_grade(self):
        grade = ReadabilityAnalyzer.flesch_kincaid_grade(SIMPLE_TEXT)
        assert grade < 8, f"Simple text grade should be <8, got {grade}"

    def test_legal_text_high_grade(self):
        grade = ReadabilityAnalyzer.flesch_kincaid_grade(LEGAL_TEXT)
        assert grade > 12, f"Legal text grade should be >12, got {grade}"

class TestSyllableCount:
    @pytest.mark.parametrize("word,expected", [
        ("cat", 1), ("table", 2), ("beautiful", 4), ("education", 4),
        ("a", 1), ("the", 1), ("indemnification", 5),
    ])
    def test_syllable_count(self, word, expected):
        count = ReadabilityAnalyzer._count_syllables(word)
        assert abs(count - expected) <= 1, f"'{word}': expected ~{expected}, got {count}"

class TestEdgeCases:
    def test_empty_string(self):
        score = ReadabilityAnalyzer.flesch_reading_ease("")
        assert isinstance(score, float)

    def test_single_word(self):
        score = ReadabilityAnalyzer.flesch_kincaid_grade("hello")
        assert isinstance(score, float)

    def test_interpret_grade(self):
        assert "Elementary" in ReadabilityAnalyzer.interpret_grade(4)
        assert "College" in ReadabilityAnalyzer.interpret_grade(13)
        assert "Graduate" in ReadabilityAnalyzer.interpret_grade(20)

class TestAnalyzeMethod:
    def test_returns_all_keys(self):
        result = ReadabilityAnalyzer.analyze(SIMPLE_TEXT)
        expected = ["flesch_reading_ease","flesch_kincaid_grade","coleman_liau_index",
                    "smog_grade","automated_readability_index","grade_interpretation","raw_counts"]
        for key in expected:
            assert key in result, f"Missing key: {key}"

    def test_raw_counts_positive(self):
        r = ReadabilityAnalyzer.analyze(SIMPLE_TEXT)
        assert r["raw_counts"]["words"] > 0
        assert r["raw_counts"]["sentences"] > 0
        assert r["raw_counts"]["syllables"] > 0
