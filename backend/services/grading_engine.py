"""
services/grading_engine.py — Weighted multi-dimensional scoring engine.
OUR CUSTOM CODE — NO LLM USED.

Computes scores across 5 dimensions and produces an overall letter grade.

Dimension weights (sum = 1.0):
  data_collection_transparency  25%
  sharing_disclosure            25%
  user_rights                   20%
  readability                   15%
  compliance                    15%
"""

import math
from typing import Any, Dict, List

from config import Config


class GradingEngine:
    """
    Computes multi-dimensional privacy-policy grades.

    Usage
    -----
    engine = GradingEngine()
    result = engine.calculate_grade(llm_findings, preprocessor_metrics)
    """

    # ------------------------------------------------------------------
    # Scoring helpers — each returns 0.0 to 10.0
    # ------------------------------------------------------------------

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 10.0) -> float:
        return max(lo, min(hi, value))

    @classmethod
    def _score_data_types_enumerated(cls, llm_findings: Dict) -> float:
        """
        Were all data types collected explicitly listed?
        More types listed → higher score, up to 10.
        """
        collected = llm_findings.get("data_collected", [])
        if not isinstance(collected, list):
            return 0.0
        count = len(collected)
        return cls._clamp(count * 1.25)  # 8 types → 10

    @classmethod
    def _score_purpose_specified(cls, llm_findings: Dict) -> float:
        """Each data type should have a purpose specified."""
        collected = llm_findings.get("data_collected", [])
        if not collected:
            return 0.0
        with_purpose = sum(1 for item in collected
                           if item.get("purpose") and item["purpose"] != "unspecified")
        return cls._clamp((with_purpose / len(collected)) * 10)

    @classmethod
    def _score_clear_categorisation(cls, metrics: Dict) -> float:
        """Reward clear data-type categorisation (many distinct types, structured)."""
        types_found = metrics.get("data_types_found", [])
        count = len(types_found)
        return cls._clamp(min(count * 1.0, 10.0))

    # SHARING DISCLOSURE ─────────────────────────────────────────────────────

    @classmethod
    def _score_third_parties_named(cls, llm_findings: Dict) -> float:
        """Reward naming specific recipients rather than vague 'partners'."""
        shared = llm_findings.get("data_shared", [])
        if not shared:
            return 2.0  # small baseline for transparency about not sharing
        named = sum(1 for item in shared
                    if item.get("recipient") and item["recipient"].lower()
                    not in ("third parties", "partners", "affiliates", "service providers"))
        return cls._clamp((named / len(shared)) * 10)

    @classmethod
    def _score_purpose_per_recipient(cls, llm_findings: Dict) -> float:
        """Each sharing relationship should have a purpose."""
        shared = llm_findings.get("data_shared", [])
        if not shared:
            return 5.0
        with_purpose = sum(1 for item in shared if item.get("data_type"))
        return cls._clamp((with_purpose / len(shared)) * 10)

    @classmethod
    def _score_opt_out_availability(cls, llm_findings: Dict, metrics: Dict) -> float:
        """Reward opt-out mechanisms and CCPA compliance."""
        opt_out = metrics.get("opt_out_presence", False)
        ccpa = metrics.get("ccpa_mentions", {}).get("mentioned", False)
        score = 0.0
        if opt_out:
            score += 5.0
        if ccpa:
            score += 3.0
        # Check LLM findings for per-recipient opt-out
        shared = llm_findings.get("data_shared", [])
        if shared:
            opt_out_count = sum(1 for i in shared if i.get("opt_out_available"))
            score += (opt_out_count / len(shared)) * 2.0
        return cls._clamp(score)

    # USER RIGHTS ────────────────────────────────────────────────────────────

    @classmethod
    def _score_access_mechanism(cls, llm_findings: Dict) -> float:
        rights = llm_findings.get("user_rights", {})
        return 10.0 if rights.get("access") else 0.0

    @classmethod
    def _score_deletion_process(cls, llm_findings: Dict) -> float:
        rights = llm_findings.get("user_rights", {})
        return 10.0 if rights.get("deletion") else 0.0

    @classmethod
    def _score_data_portability(cls, llm_findings: Dict) -> float:
        rights = llm_findings.get("user_rights", {})
        return 10.0 if rights.get("portability") else 0.0

    # READABILITY ────────────────────────────────────────────────────────────

    @classmethod
    def _score_readability_from_metrics(cls, metrics: Dict) -> float:
        """
        Convert Flesch Reading Ease (0-100) to a 0-10 score.
        Higher FRE = more readable = higher score.
        """
        fre = metrics.get("flesch_reading_ease", 30.0)
        # FRE 0  → score 0;  FRE 100 → score 10
        return cls._clamp(fre / 10.0)

    @classmethod
    def _score_section_organisation(cls, metrics: Dict) -> float:
        """More sections and better structure → higher score."""
        section_count = metrics.get("section_count", 0)
        structure = metrics.get("structure_score", 0.0)
        # Normalise structure score (0-100) to (0-5) and add section bonus (0-5)
        s_score = cls._clamp(structure / 20.0, 0.0, 5.0)
        sec_score = cls._clamp(min(section_count * 0.5, 5.0), 0.0, 5.0)
        return cls._clamp(s_score + sec_score)

    @classmethod
    def _score_jargon_explanation(cls, metrics: Dict) -> float:
        """Lower jargon density → higher score."""
        jargon_density = metrics.get("jargon_density", 0.0)
        # 0% jargon → 10; 20%+ jargon → 0
        return cls._clamp(10.0 - (jargon_density / 2.0))

    # COMPLIANCE ─────────────────────────────────────────────────────────────

    @classmethod
    def _score_gdpr_alignment(cls, llm_findings: Dict, metrics: Dict) -> float:
        compliance = llm_findings.get("compliance_indicators", [])
        gdpr_in_llm = any("gdpr" in str(c).lower() for c in compliance)
        gdpr_in_metrics = metrics.get("gdpr_mentions", {}).get("mentioned", False)
        rights = llm_findings.get("user_rights", {})
        # GDPR requires access, deletion, portability, correction
        rights_score = sum([
            bool(rights.get("access")),
            bool(rights.get("deletion")),
            bool(rights.get("portability")),
            bool(rights.get("correction")),
        ]) * 2.0  # 0-8 points
        mention_bonus = 1.0 if (gdpr_in_llm or gdpr_in_metrics) else 0.0
        return cls._clamp(rights_score + mention_bonus)

    @classmethod
    def _score_ccpa_alignment(cls, metrics: Dict) -> float:
        ccpa = metrics.get("ccpa_mentions", {}).get("mentioned", False)
        opt_out = metrics.get("opt_out_presence", False)
        no_sell = metrics.get("data_sale", {}).get("sells_data", True)  # True = bad
        score = 0.0
        if ccpa:
            score += 4.0
        if opt_out:
            score += 3.0
        if not no_sell:
            score += 3.0  # bonus for NOT selling data
        return cls._clamp(score)

    @classmethod
    def _score_coppa_consideration(cls, metrics: Dict) -> float:
        children = metrics.get("children_privacy", {})
        if children.get("mentioned", False):
            score = 5.0
            if children.get("coppa_referenced", False):
                score += 5.0
            return cls._clamp(score)
        return 5.0  # neutral if children not in scope

    # ------------------------------------------------------------------
    # Dimension aggregators
    # ------------------------------------------------------------------

    @classmethod
    def _dimension_data_collection(cls, llm: Dict, metrics: Dict) -> Dict:
        scores = {
            "data_types_enumerated": cls._score_data_types_enumerated(llm),
            "purpose_specified": cls._score_purpose_specified(llm),
            "clear_categorisation": cls._score_clear_categorisation(metrics),
        }
        avg = sum(scores.values()) / len(scores)
        return {"subscores": scores, "score": round(avg * 10, 2)}  # 0-100

    @classmethod
    def _dimension_sharing_disclosure(cls, llm: Dict, metrics: Dict) -> Dict:
        scores = {
            "third_parties_named": cls._score_third_parties_named(llm),
            "purpose_per_recipient": cls._score_purpose_per_recipient(llm),
            "opt_out_availability": cls._score_opt_out_availability(llm, metrics),
        }
        avg = sum(scores.values()) / len(scores)
        return {"subscores": scores, "score": round(avg * 10, 2)}

    @classmethod
    def _dimension_user_rights(cls, llm: Dict, metrics: Dict) -> Dict:
        scores = {
            "access_mechanism": cls._score_access_mechanism(llm),
            "deletion_process": cls._score_deletion_process(llm),
            "data_portability": cls._score_data_portability(llm),
        }
        avg = sum(scores.values()) / len(scores)
        return {"subscores": scores, "score": round(avg * 10, 2)}

    @classmethod
    def _dimension_readability(cls, llm: Dict, metrics: Dict) -> Dict:
        scores = {
            "readability_score": cls._score_readability_from_metrics(metrics),
            "section_organisation": cls._score_section_organisation(metrics),
            "jargon_explanation": cls._score_jargon_explanation(metrics),
        }
        avg = sum(scores.values()) / len(scores)
        return {"subscores": scores, "score": round(avg * 10, 2)}

    @classmethod
    def _dimension_compliance(cls, llm: Dict, metrics: Dict) -> Dict:
        scores = {
            "gdpr_alignment": cls._score_gdpr_alignment(llm, metrics),
            "ccpa_alignment": cls._score_ccpa_alignment(metrics),
            "coppa_consideration": cls._score_coppa_consideration(metrics),
        }
        avg = sum(scores.values()) / len(scores)
        return {"subscores": scores, "score": round(avg * 10, 2)}

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    @classmethod
    def calculate_grade(cls, llm_findings: Dict, preprocessor_metrics: Dict) -> Dict:
        """
        Compute weighted overall grade and per-dimension breakdown.

        Returns
        -------
        {
          grade            : "A" | "B" | "C" | "D" | "F"
          overall_score    : float 0-100
          dimension_scores : { dimension: { score, subscores } }
          reasoning        : dict of per-dimension reasoning strings
        }
        """
        llm = llm_findings or {}
        metrics = preprocessor_metrics or {}

        # Compute all dimensions
        dims = {
            "data_collection_transparency": cls._dimension_data_collection(llm, metrics),
            "sharing_disclosure":           cls._dimension_sharing_disclosure(llm, metrics),
            "user_rights":                  cls._dimension_user_rights(llm, metrics),
            "readability":                  cls._dimension_readability(llm, metrics),
            "compliance":                   cls._dimension_compliance(llm, metrics),
        }

        weights = Config.GRADING_WEIGHTS

        # Weighted overall score
        overall = sum(
            dims[dim]["score"] * weight
            for dim, weight in weights.items()
        )
        overall = round(overall, 2)

        # Letter grade
        grade = Config.grade_letter(overall)

        # Human-readable reasoning per dimension
        reasoning = {
            "data_collection_transparency": (
                f"Score {dims['data_collection_transparency']['score']:.0f}/100. "
                f"Policy lists {len(llm.get('data_collected', []))} data types with purposes."
            ),
            "sharing_disclosure": (
                f"Score {dims['sharing_disclosure']['score']:.0f}/100. "
                f"Sharing with {len(llm.get('data_shared', []))} recipient types."
            ),
            "user_rights": (
                f"Score {dims['user_rights']['score']:.0f}/100. "
                f"Rights found: access={bool(llm.get('user_rights',{}).get('access'))}, "
                f"deletion={bool(llm.get('user_rights',{}).get('deletion'))}, "
                f"portability={bool(llm.get('user_rights',{}).get('portability'))}."
            ),
            "readability": (
                f"Score {dims['readability']['score']:.0f}/100. "
                f"Flesch Reading Ease={metrics.get('flesch_reading_ease', 'N/A')}, "
                f"Grade Level={metrics.get('flesch_kincaid_grade', 'N/A')}."
            ),
            "compliance": (
                f"Score {dims['compliance']['score']:.0f}/100. "
                f"GDPR={metrics.get('gdpr_mentions',{}).get('mentioned', False)}, "
                f"CCPA={metrics.get('ccpa_mentions',{}).get('mentioned', False)}, "
                f"COPPA={metrics.get('children_privacy',{}).get('coppa_referenced', False)}."
            ),
        }

        # Flat dimension score dict for easy frontend consumption
        flat_scores = {dim: info["score"] for dim, info in dims.items()}

        # Trust Score — a memorable single composite metric
        trust_score = cls.calculate_trust_score(
            overall_score=overall,
            dark_pattern_score=metrics.get("dark_pattern_score", 0.0),
            verification_confidence=metrics.get("_verification_confidence", 0.75),
            red_flag_count=len(llm.get("red_flags", [])),
        )

        return {
            "grade": grade,
            "overall_score": overall,
            "trust_score": trust_score,
            "dimension_scores": flat_scores,
            "dimension_details": {dim: info for dim, info in dims.items()},
            "reasoning": reasoning,
        }

    @classmethod
    def calculate_trust_score(
        cls,
        overall_score: float,
        dark_pattern_score: float = 0.0,
        verification_confidence: float = 0.75,
        red_flag_count: int = 0,
    ) -> float:
        """
        Composite Trust Score (0–100) — OUR CUSTOM CODE.

        Formula
        -------
        trust = overall_score
                − dark_pattern_penalty   (0–25 pts; heavy dark patterns reduce trust)
                + verification_bonus     (0–10 pts; high AI-claim confidence = more trustworthy)
                − red_flag_penalty       (2 pts per flag, capped at 20)

        Interpretation
        --------------
        80–100 : Highly Trustworthy policy
        60–79  : Moderately Trustworthy
        40–59  : Questionable
        0–39   : Untrustworthy
        """
        # 1. Dark pattern penalty (score 0 = no patterns = 0 penalty; 100 = max patterns = 25 penalty)
        dark_penalty = (dark_pattern_score / 100.0) * 25.0

        # 2. Verification bonus (AI confidence 0→1 maps to 0→10 bonus points)
        verify_bonus = verification_confidence * 10.0

        # 3. Red flag penalty (each flag costs 2 pts, capped at 20)
        flag_penalty = min(red_flag_count * 2.0, 20.0)

        trust = overall_score - dark_penalty + verify_bonus - flag_penalty
        return round(max(0.0, min(100.0, trust)), 1)
