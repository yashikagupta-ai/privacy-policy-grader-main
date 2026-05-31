"""
services/preprocessor.py — NLP metrics pipeline.
OUR CUSTOM CODE — NO LLM USED.
Computes 18+ metrics from raw policy text.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Any

import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
import textstat

from analyzers.jargon_detector import LegalJargonDetector
from analyzers.dark_patterns import DarkPatternDetector
from analyzers.text_metrics import TextMetricsAnalyzer
from analyzers.gdpr_classifier import GDPRLawfulBasisClassifier

nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)


class PolicyPreprocessor:
    """Converts raw policy text into a rich metrics dictionary."""

    _DATA_TYPES = [
        "email","name","address","location","phone","ip address","device",
        "cookies","browsing history","purchase history","biometric","genetic",
        "health","financial","credit card","social security","photo","video",
        "audio","voice","age","gender","race","religion","political",
        "sexual orientation",
    ]
    _THIRD_PARTY_PATTERNS = [
        r"\bthird.part(y|ies)\b",r"\bservice provider\b",r"\bpartner\b",
        r"\baffiliate\b",r"\bvendor\b",r"\bsubprocessor\b",r"\banalytic\b",
    ]
    _USER_RIGHTS_PATTERNS = [
        r"\bright to access\b",r"\bright to delete\b",r"\bright to erasure\b",
        r"\bright to portabilit\b",r"\bright to correct\b",r"\bright to object\b",
        r"\bopt.out\b",r"\bopt.in\b",r"\bwithdraw consent\b",
    ]
    _OPT_OUT_PATTERNS = [
        r"\bopt[- ]?out\b",r"\bunsubscribe\b",r"\bwithdraw consent\b",
        r"\bmanage preferences\b",r"\bdo not sell\b",r"\bdo not track\b",
    ]

    @staticmethod
    def word_count(text: str) -> int:
        return len([w for w in word_tokenize(text) if w.isalpha()])

    @staticmethod
    def sentence_count(text: str) -> int:
        return max(1, len(sent_tokenize(text)))

    @staticmethod
    def avg_sentence_length(text: str) -> float:
        sentences = sent_tokenize(text)
        if not sentences:
            return 0.0
        lengths = [len([w for w in word_tokenize(s) if w.isalpha()]) for s in sentences]
        return round(sum(lengths) / len(lengths), 2)

    @staticmethod
    def flesch_reading_ease(text: str) -> float:
        return round(textstat.flesch_reading_ease(text), 2)

    @staticmethod
    def flesch_kincaid_grade(text: str) -> float:
        return round(textstat.flesch_kincaid_grade(text), 2)

    @classmethod
    def jargon_density(cls, text: str) -> float:
        return LegalJargonDetector.detect(text)["density_percent"]

    @staticmethod
    def passive_voice_percentage(text: str) -> float:
        return TextMetricsAnalyzer.passive_voice_percentage(text)

    @staticmethod
    def active_voice_percentage(text: str) -> float:
        return round(100.0 - TextMetricsAnalyzer.passive_voice_percentage(text), 2)

    @staticmethod
    def section_count(sections: List[Dict]) -> int:
        return len(sections)

    @classmethod
    def data_type_mentions(cls, text: str) -> Dict[str, int]:
        norm = text.lower()
        return {d: len(re.findall(r"\b"+re.escape(d)+r"\b", norm))
                for d in cls._DATA_TYPES
                if re.search(r"\b"+re.escape(d)+r"\b", norm)}

    @classmethod
    def third_party_mentions(cls, text: str) -> int:
        norm = text.lower()
        return sum(len(re.findall(p, norm, re.IGNORECASE)) for p in cls._THIRD_PARTY_PATTERNS)

    @classmethod
    def user_rights_mentions(cls, text: str) -> int:
        norm = text.lower()
        return sum(len(re.findall(p, norm, re.IGNORECASE)) for p in cls._USER_RIGHTS_PATTERNS)

    @staticmethod
    def policy_age_days(last_updated: Optional[str]) -> Optional[int]:
        if not last_updated:
            return None
        for fmt in ["%B %d, %Y","%B %d %Y","%b %d, %Y","%Y-%m-%d","%m/%d/%Y"]:
            try:
                dt = datetime.strptime(last_updated.strip()[:20], fmt)
                return (datetime.utcnow() - dt).days
            except ValueError:
                continue
        return None

    @classmethod
    def opt_out_presence(cls, text: str) -> bool:
        norm = text.lower()
        return any(re.search(p, norm) for p in cls._OPT_OUT_PATTERNS)

    @staticmethod
    def data_sale_mentions(text: str) -> Dict[str, Any]:
        norm = text.lower()
        sells = bool(re.search(r"\bsell (your|personal|user) (data|information)\b", norm))
        count = len(re.findall(r"\bsale? (of|your) (personal|data|information)\b", norm))
        return {"found": count > 0 or sells, "sells_data": sells, "count": count}

    @staticmethod
    def children_privacy_mentions(text: str) -> Dict[str, Any]:
        norm = text.lower()
        count = sum(len(re.findall(p, norm)) for p in [
            r"\bchildren\b",r"\bminor\b",r"\bunder (13|16|18)\b",r"\bcoppa\b"])
        return {"mentioned": count > 0, "count": count,
                "coppa_referenced": bool(re.search(r"\bcoppa\b", norm))}

    @staticmethod
    def gdpr_mentions(text: str) -> Dict[str, Any]:
        norm = text.lower()
        count = len(re.findall(r"\bgdpr\b|\bgeneral data protection regulation\b", norm))
        return {"mentioned": count > 0, "count": count}

    @staticmethod
    def ccpa_mentions(text: str) -> Dict[str, Any]:
        norm = text.lower()
        count = len(re.findall(r"\bccpa\b|\bcalifornia consumer privacy act\b|\bcpra\b", norm))
        return {"mentioned": count > 0, "count": count}

    @classmethod
    def process(cls, policy_text: str, sections: Optional[List[Dict]] = None,
                last_updated: Optional[str] = None) -> Dict[str, Any]:
        """Run all metrics on policy_text and return a unified dict."""
        sections = sections or []
        text = policy_text

        wc  = cls.word_count(text)
        sc  = cls.sentence_count(text)
        avg_sl = cls.avg_sentence_length(text)
        fre = cls.flesch_reading_ease(text)
        fkg = cls.flesch_kincaid_grade(text)

        jargon_info = LegalJargonDetector.detect(text)
        jd = jargon_info["density_percent"]

        pv = cls.passive_voice_percentage(text)
        av = cls.active_voice_percentage(text)

        dark_result = DarkPatternDetector.detect(text, word_count=wc, fk_grade=fkg, jargon_density=jd)
        text_metrics = TextMetricsAnalyzer.analyze(text)

        return {
            "word_count": wc,
            "sentence_count": sc,
            "avg_sentence_length": avg_sl,
            "section_count": cls.section_count(sections),
            "flesch_reading_ease": fre,
            "flesch_kincaid_grade": fkg,
            "jargon_density": jd,
            "jargon_top_terms": jargon_info.get("top_terms", []),
            "jargon_by_category": jargon_info.get("terms_by_category", {}),
            "passive_voice_percentage": pv,
            "active_voice_percentage": av,
            "data_type_mentions": cls.data_type_mentions(text),
            "data_types_found": list(cls.data_type_mentions(text).keys()),
            "third_party_mentions": cls.third_party_mentions(text),
            "user_rights_mentions": cls.user_rights_mentions(text),
            "policy_age_days": cls.policy_age_days(last_updated),
            "last_updated": last_updated,
            "opt_out_presence": cls.opt_out_presence(text),
            "data_sale": cls.data_sale_mentions(text),
            "children_privacy": cls.children_privacy_mentions(text),
            "gdpr_mentions": cls.gdpr_mentions(text),
            "ccpa_mentions": cls.ccpa_mentions(text),
            "dark_pattern_score": dark_result["score"],
            "dark_pattern_severity": dark_result["severity_level"],
            "dark_patterns_found": dark_result["patterns_found"],
            "type_token_ratio": text_metrics["type_token_ratio"],
            "sentiment": text_metrics["sentiment"],
            "required_clauses": text_metrics["required_clauses"],
            "clause_completeness_score": text_metrics["clause_completeness_score"],
            "structure_score": text_metrics["structure_score"],
            "sentence_complexity": text_metrics["sentence_complexity"],
            "paragraph_count": text_metrics["paragraph_structure"]["paragraph_count"],
            "gdpr_basis": GDPRLawfulBasisClassifier.classify(text),
        }
