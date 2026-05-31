"""
analyzers/text_metrics.py — Advanced text statistics.

OUR CUSTOM CODE — NO LLM USED.

Provides
--------
- Type-token ratio (vocabulary diversity)
- Sentence complexity distribution
- Paragraph structure analysis
- Privacy keyword density
- Sentiment scores (NLTK VADER)
- Required clause presence detection
- Policy structure score
"""

import re
from collections import Counter
from typing import Dict, List

import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import sent_tokenize, word_tokenize

# Ensure NLTK corpora are present
nltk.download("vader_lexicon", quiet=True)
nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)


class TextMetricsAnalyzer:
    """
    Computes a wide set of structural and linguistic text statistics.

    All methods are class-methods — no state is stored.
    Call ``analyze()`` to get the full report.
    """

    # Privacy-relevant keywords to track
    PRIVACY_KEYWORDS: List[str] = [
        "cookies", "tracking", "data", "share", "third-party",
        "consent", "opt-out", "opt-in", "gdpr", "ccpa", "coppa",
        "collect", "personal", "location", "email", "biometric",
        "advertising", "delete", "access", "rights", "security",
        "encrypt", "breach", "children", "minor",
    ]

    # Required clauses: name → list of regex patterns (any match → present)
    REQUIRED_CLAUSES: Dict[str, List[str]] = {
        "data_retention_policy": [
            r"\bdata (is |will be )?(retained|stored|kept) for\b",
            r"\bretention period\b",
        ],
        "right_to_access": [
            r"\bright to (access|request a copy|obtain a copy)\b",
            r"\byou (may|can) (request|access) (your|a copy of your)\b",
        ],
        "right_to_deletion": [
            r"\bright to (delete|erasure|be forgotten)\b",
            r"\byou (may|can) (request|ask us to) (delete|remove|erase)\b",
        ],
        "right_to_portability": [
            r"\bright to (data portability|port(ability)?)\b",
            r"\breceive (your data|a copy) in a (machine.readable|portable|structured)\b",
        ],
        "right_to_correction": [
            r"\bright to (rectif|correct|amend|update) (your )?(personal )?(data|information)\b",
        ],
        "opt_out_mechanism": [
            r"\bopt[- ]out\b",
            r"\byou (may|can|have the right to) (unsubscribe|withdraw consent|object)\b",
        ],
        "gdpr_reference": [
            r"\bgdpr\b",
            r"\bgeneral data protection regulation\b",
        ],
        "ccpa_reference": [
            r"\bccpa\b",
            r"\bcalifornia consumer privacy act\b",
        ],
        "coppa_reference": [
            r"\bcoppa\b",
            r"\bchildren'?s online privacy protection\b",
        ],
        "security_measures": [
            r"\b(encrypt|secure|protect) (your |all )?(data|information|transmissions?)\b",
            r"\bsecurity (measures|controls|safeguards|practices)\b",
        ],
        "contact_information": [
            r"\bcontact (us|our (privacy|data protection))\b",
            r"\bemail (us|our privacy team)\b",
        ],
        "third_party_disclosure": [
            r"\b(share|disclose) .{0,40}(with|to) (third part|partner|service provider)\b",
        ],
    }

    # ------------------------------------------------------------------
    # 1. Type-token ratio
    # ------------------------------------------------------------------

    @staticmethod
    def type_token_ratio(text: str) -> float:
        """
        Vocabulary diversity = unique tokens / total tokens.

        A higher ratio indicates richer, more varied language.
        Typical range for legal text: 0.05 – 0.20.
        """
        tokens = re.findall(r"\b[a-zA-Z]+\b", text.lower())
        if not tokens:
            return 0.0
        return round(len(set(tokens)) / len(tokens), 4)

    # ------------------------------------------------------------------
    # 2. Sentence complexity distribution
    # ------------------------------------------------------------------

    @staticmethod
    def sentence_complexity_distribution(text: str) -> Dict[str, object]:
        """
        Classify sentences by length (in words):
          short  : < 10 words
          medium : 10–25 words
          long   : 26–40 words
          very_long : > 40 words  (red flag for readability)
        """
        sentences = sent_tokenize(text)
        distribution = {"short": 0, "medium": 0, "long": 0, "very_long": 0}
        lengths = []

        for s in sentences:
            n = len(re.findall(r"\b\w+\b", s))
            lengths.append(n)
            if n < 10:
                distribution["short"] += 1
            elif n <= 25:
                distribution["medium"] += 1
            elif n <= 40:
                distribution["long"] += 1
            else:
                distribution["very_long"] += 1

        avg = sum(lengths) / len(lengths) if lengths else 0

        return {
            "distribution": distribution,
            "average_words_per_sentence": round(avg, 1),
            "max_sentence_length": max(lengths) if lengths else 0,
        }

    # ------------------------------------------------------------------
    # 3. Paragraph structure
    # ------------------------------------------------------------------

    @staticmethod
    def paragraph_structure(text: str) -> Dict[str, int]:
        """
        Estimate paragraph count and average paragraph length.

        Paragraphs are separated by one or more blank lines.
        """
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        total_para = len(paragraphs)
        words_per_para = [len(re.findall(r"\b\w+\b", p)) for p in paragraphs]
        avg_words = (sum(words_per_para) / total_para) if total_para else 0

        return {
            "paragraph_count": total_para,
            "average_words_per_paragraph": round(avg_words, 1),
        }

    # ------------------------------------------------------------------
    # 4. Privacy keyword density
    # ------------------------------------------------------------------

    @classmethod
    def keyword_density(cls, text: str) -> Dict[str, float]:
        """
        Calculate the occurrence density (per 1,000 words) of each
        privacy-relevant keyword.
        """
        total_words = len(re.findall(r"\b\w+\b", text.lower()))
        if total_words == 0:
            return {kw: 0.0 for kw in cls.PRIVACY_KEYWORDS}

        norm = text.lower()
        densities: Dict[str, float] = {}
        for kw in cls.PRIVACY_KEYWORDS:
            count = len(re.findall(r"\b" + re.escape(kw) + r"\b", norm))
            # Express as occurrences per 1,000 words
            densities[kw] = round((count / total_words) * 1000, 2)
        return densities

    # ------------------------------------------------------------------
    # 5. Sentiment scores (VADER)
    # ------------------------------------------------------------------

    @staticmethod
    def sentiment_scores(text: str) -> Dict[str, float]:
        """
        VADER sentiment on the full text.

        Returns compound (–1 to +1), pos, neu, neg proportions.
        Note: privacy policies tend to score near 0 (neutral-legal).
        """
        sia = SentimentIntensityAnalyzer()
        scores = sia.polarity_scores(text[:10_000])  # limit for speed
        return {k: round(v, 4) for k, v in scores.items()}

    # ------------------------------------------------------------------
    # 6. Required-clause presence
    # ------------------------------------------------------------------

    @classmethod
    def required_clause_check(cls, text: str) -> Dict[str, bool]:
        """
        Return True for each required clause if it appears in the text.
        """
        norm = text.lower()
        results: Dict[str, bool] = {}
        for clause_name, patterns in cls.REQUIRED_CLAUSES.items():
            results[clause_name] = any(
                bool(re.search(p, norm, re.IGNORECASE)) for p in patterns
            )
        return results

    @classmethod
    def clause_completeness_score(cls, text: str) -> float:
        """
        Score (0-100) based on how many required clauses are present.
        """
        clauses = cls.required_clause_check(text)
        present = sum(1 for v in clauses.values() if v)
        return round((present / len(clauses)) * 100, 2) if clauses else 0.0

    # ------------------------------------------------------------------
    # 7. Policy structure score
    # ------------------------------------------------------------------

    @staticmethod
    def policy_structure_score(text: str) -> float:
        """
        Heuristic quality score (0–100) based on:
        - Presence of section headings
        - Paragraph count (more granular → better)
        - Average sentence length (shorter → better)

        Returns a normalised 0–100 score.
        """
        # Count lines that look like headings (ALL CAPS or Title Case, short)
        headings = re.findall(
            r"^[A-Z][A-Za-z0-9 \-&:]{2,60}$",
            text,
            re.MULTILINE,
        )
        heading_score = min(30, len(headings) * 3)  # up to 30 pts for headings

        # Paragraph count
        paragraphs = re.split(r"\n{2,}", text)
        para_score = min(40, len(paragraphs) * 2)  # up to 40 pts

        # Sentence length penalty
        sentences = sent_tokenize(text)
        if sentences:
            avg_len = sum(
                len(re.findall(r"\b\w+\b", s)) for s in sentences
            ) / len(sentences)
            # Ideal ≈ 15 words; penalty grows with distance
            length_score = max(0, 30 - abs(avg_len - 15))
        else:
            length_score = 0

        return round(heading_score + para_score + length_score, 2)

    # ------------------------------------------------------------------
    # 8. Passive-voice detection
    # ------------------------------------------------------------------

    @staticmethod
    def passive_voice_percentage(text: str) -> float:
        """
        Estimate percentage of sentences using passive voice.

        Heuristic: passive voice patterns like
        "is collected", "are processed", "will be shared", "was used".
        """
        sentences = sent_tokenize(text)
        if not sentences:
            return 0.0
        passive_pattern = re.compile(
            r"\b(am|is|are|was|were|be|been|being)\s+\w+ed\b",
            re.IGNORECASE,
        )
        passive_count = sum(
            1 for s in sentences if passive_pattern.search(s)
        )
        return round((passive_count / len(sentences)) * 100, 2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def analyze(cls, text: str) -> Dict[str, object]:
        """
        Execute all metrics and return a unified dictionary.

        Parameters
        ----------
        text : str
            Clean plain text of the privacy policy.
        """
        return {
            "type_token_ratio": cls.type_token_ratio(text),
            "sentence_complexity": cls.sentence_complexity_distribution(text),
            "paragraph_structure": cls.paragraph_structure(text),
            "keyword_density": cls.keyword_density(text),
            "sentiment": cls.sentiment_scores(text),
            "required_clauses": cls.required_clause_check(text),
            "clause_completeness_score": cls.clause_completeness_score(text),
            "structure_score": cls.policy_structure_score(text),
            "passive_voice_percent": cls.passive_voice_percentage(text),
        }
