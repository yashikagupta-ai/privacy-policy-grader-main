"""
analyzers/readability.py — Readability formulas implemented from scratch.

OUR CUSTOM CODE — NO LLM USED.

Implements
----------
- Flesch Reading Ease
- Flesch-Kincaid Grade Level
- Coleman-Liau Index
- SMOG Grade
- Automated Readability Index (ARI)

All formulae are derived from the published academic papers and are
computed directly from word / sentence / syllable counts.
"""

import math
import re
from typing import Dict

import nltk
from nltk.tokenize import sent_tokenize, word_tokenize

# Ensure required NLTK data is present.
# safe to call multiple times — NLTK caches after first download.
nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)


class ReadabilityAnalyzer:
    """
    Computes a suite of readability metrics for a block of English text.

    Usage
    -----
    results = ReadabilityAnalyzer.analyze(policy_text)
    print(results["flesch_reading_ease"])   # e.g. 32.5 (difficult)
    print(results["grade_interpretation"])  # e.g. "Graduate Level"
    """

    # ------------------------------------------------------------------
    # Private: Syllable counter
    # ------------------------------------------------------------------

    @staticmethod
    def _count_syllables(word: str) -> int:
        """
        Estimate syllable count for a single English word.

        Algorithm (heuristic — suitable for statistics-level accuracy)
        ---------------------------------------------------------------
        1. Lower-case, strip non-alpha characters.
        2. Count vowel groups (consecutive vowels = 1 syllable).
        3. Subtract silent trailing 'e'.
        4. Ensure minimum of 1.

        Edge cases handled
        ------------------
        - All-vowel words (e.g. "area")
        - Words ending in "-le" after a consonant ("table" → 2)
        - Common silent-e patterns
        """
        word = word.lower()
        word = re.sub(r"[^a-z]", "", word)
        if not word:
            return 0

        # Count vowel groups
        count = len(re.findall(r"[aeiouy]+", word))

        # Silent trailing 'e' — subtract if word ends in a vowel-less suffix
        if word.endswith("e") and not word.endswith("le"):
            count = max(1, count - 1)

        # Words ending in '-ed' with silent e (e.g. "baked" → 1 syllable)
        if word.endswith("ed") and len(word) > 3:
            # consonant before -ed → usually silent
            if word[-3] not in "aeiouy":
                count = max(1, count - 1)

        return max(1, count)

    # ------------------------------------------------------------------
    # Private: Aggregate token counts
    # ------------------------------------------------------------------

    @classmethod
    def _aggregate(cls, text: str) -> Dict[str, int]:
        """
        Tokenise text and compute sentence, word, and syllable counts.

        Returns
        -------
        dict with keys: sentences, words, syllables, characters
        """
        if not text or not text.strip():
            return {"sentences": 1, "words": 1, "syllables": 1, "characters": 1}

        sentences = sent_tokenize(text)
        all_tokens = word_tokenize(text)
        words = [w for w in all_tokens if w.isalpha()]

        num_sentences = max(1, len(sentences))
        num_words = max(1, len(words))
        num_syllables = max(1, sum(cls._count_syllables(w) for w in words))
        num_chars = max(1, sum(len(w) for w in words))

        return {
            "sentences": num_sentences,
            "words": num_words,
            "syllables": num_syllables,
            "characters": num_chars,
        }

    # ------------------------------------------------------------------
    # Formula 1: Flesch Reading Ease
    # ------------------------------------------------------------------

    @classmethod
    def flesch_reading_ease(cls, text: str) -> float:
        """
        Flesch Reading Ease (FRE).

        Formula
        -------
        FRE = 206.835
              − 1.015  × (words / sentences)
              − 84.6   × (syllables / words)

        Interpretation
        --------------
        90–100 : Very Easy (5th grade)
        70–90  : Easy
        60–70  : Standard (8th–9th grade)
        50–60  : Fairly Difficult
        30–50  : Difficult (college)
        0–30   : Very Confusing (professional/legal)
        """
        s = cls._aggregate(text)
        wps = s["words"] / s["sentences"]   # words per sentence
        spw = s["syllables"] / s["words"]   # syllables per word
        score = 206.835 - 1.015 * wps - 84.6 * spw
        return round(score, 2)

    # ------------------------------------------------------------------
    # Formula 2: Flesch-Kincaid Grade Level
    # ------------------------------------------------------------------

    @classmethod
    def flesch_kincaid_grade(cls, text: str) -> float:
        """
        Flesch-Kincaid Grade Level (FKGL).

        Formula
        -------
        FKGL = 0.39 × (words / sentences)
             + 11.8 × (syllables / words)
             − 15.59

        Result corresponds to US school grade level (e.g. 8 → 8th grade).
        """
        s = cls._aggregate(text)
        wps = s["words"] / s["sentences"]
        spw = s["syllables"] / s["words"]
        grade = 0.39 * wps + 11.8 * spw - 15.59
        return round(grade, 2)

    # ------------------------------------------------------------------
    # Formula 3: Coleman-Liau Index
    # ------------------------------------------------------------------

    @classmethod
    def coleman_liau_index(cls, text: str) -> float:
        """
        Coleman-Liau Index.

        Formula (per 100 words)
        -----------------------
        CLI = 0.0588 × L − 0.296 × S − 15.8

        where
          L = (characters / words) × 100
          S = (sentences / words) × 100
        """
        s = cls._aggregate(text)
        L = (s["characters"] / s["words"]) * 100
        S = (s["sentences"] / s["words"]) * 100
        cli = 0.0588 * L - 0.296 * S - 15.8
        return round(cli, 2)

    # ------------------------------------------------------------------
    # Formula 4: SMOG Grade
    # ------------------------------------------------------------------

    @classmethod
    def smog_grade(cls, text: str) -> float:
        """
        SMOG Grade (Simple Measure of Gobbledygook).

        Formula
        -------
        SMOG = 1.0430 × √(polysyllables × (30 / sentences)) + 3.1291

        A polysyllable is a word with ≥ 3 syllables.

        Note: SMOG is most accurate when the text has ≥ 30 sentences.
        """
        sentences = sent_tokenize(text)
        words = [w for w in word_tokenize(text) if w.isalpha()]
        num_sentences = max(1, len(sentences))
        polysyllable_count = sum(
            1 for w in words if cls._count_syllables(w) >= 3
        )
        grade = 1.0430 * math.sqrt(polysyllable_count * (30 / num_sentences)) + 3.1291
        return round(grade, 2)

    # ------------------------------------------------------------------
    # Formula 5: Automated Readability Index
    # ------------------------------------------------------------------

    @classmethod
    def automated_readability_index(cls, text: str) -> float:
        """
        Automated Readability Index (ARI).

        Formula
        -------
        ARI = 4.71 × (characters / words)
            + 0.5  × (words / sentences)
            − 21.43
        """
        s = cls._aggregate(text)
        ari = (
            4.71 * (s["characters"] / s["words"])
            + 0.5 * (s["words"] / s["sentences"])
            - 21.43
        )
        return round(ari, 2)

    # ------------------------------------------------------------------
    # Interpretation helper
    # ------------------------------------------------------------------

    @staticmethod
    def interpret_grade(grade: float) -> str:
        """
        Convert a numeric grade level to a human-readable school level.

        Examples
        --------
        4.2  → "4th Grade (Elementary)"
        8.0  → "8th Grade (Middle School)"
        12.5 → "College Freshman"
        17.0 → "Graduate Level"
        """
        if grade < 1:
            return "Early Reader (Pre-K)"
        if grade <= 5:
            return f"{int(grade)}th Grade (Elementary)"
        if grade <= 8:
            return f"{int(grade)}th Grade (Middle School)"
        if grade <= 12:
            return f"{int(grade)}th Grade (High School)"
        if grade <= 13:
            return "College Freshman"
        if grade <= 14:
            return "College Sophomore"
        if grade <= 16:
            return "College Junior / Senior"
        return "Graduate Level"

    # ------------------------------------------------------------------
    # Public API — run all metrics
    # ------------------------------------------------------------------

    @classmethod
    def analyze(cls, text: str) -> Dict[str, object]:
        """
        Execute every readability metric and return a unified dict.

        Parameters
        ----------
        text : str
            Plain (non-HTML) text.

        Returns
        -------
        dict
            Keys: flesch_reading_ease, flesch_kincaid_grade,
                  coleman_liau_index, smog_grade,
                  automated_readability_index, grade_interpretation,
                  raw_counts
        """
        counts = cls._aggregate(text)
        fkgl = cls.flesch_kincaid_grade(text)

        return {
            "flesch_reading_ease": cls.flesch_reading_ease(text),
            "flesch_kincaid_grade": fkgl,
            "coleman_liau_index": cls.coleman_liau_index(text),
            "smog_grade": cls.smog_grade(text),
            "automated_readability_index": cls.automated_readability_index(text),
            "grade_interpretation": cls.interpret_grade(fkgl),
            "raw_counts": counts,
        }
