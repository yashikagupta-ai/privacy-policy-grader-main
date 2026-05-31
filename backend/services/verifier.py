"""
services/verifier.py — Claim verifier using fuzzy string matching.
OUR CUSTOM CODE — NO LLM USED.

For every claim in the LLM output, searches the original policy text for
supporting evidence using difflib SequenceMatcher (Levenshtein-like).
Flags claims with no textual support as potential hallucinations.
"""

import re
import difflib
from typing import Any, Dict, List, Optional, Tuple


class ClaimVerifier:
    """
    Cross-references LLM findings against the original policy text.

    Usage
    -----
    verifier = ClaimVerifier()
    verified = verifier.verify_claims(llm_findings, original_text)
    """

    # Minimum similarity ratio to accept a match (0-1)
    SIMILARITY_THRESHOLD: float = 0.55
    # Context characters to extract around a match
    CONTEXT_WINDOW: int = 120
    # Maximum length of text window for fuzzy matching per claim
    FUZZY_WINDOW: int = 200

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(text: str) -> str:
        """Lower-case, collapse whitespace."""
        return re.sub(r"\s+", " ", text.lower()).strip()

    @classmethod
    def _exact_search(cls, query: str, corpus: str) -> Optional[str]:
        """
        Return a context snippet if query appears verbatim in corpus.
        Case-insensitive.
        """
        norm_query = cls._normalize(query)
        norm_corpus = cls._normalize(corpus)
        idx = norm_corpus.find(norm_query)
        if idx == -1:
            return None
        start = max(0, idx - 40)
        end = min(len(corpus), idx + len(query) + 80)
        return corpus[start:end].strip()

    @classmethod
    def _fuzzy_search(cls, query: str, corpus: str) -> Tuple[float, Optional[str]]:
        """
        Slide a window over corpus and compute SequenceMatcher ratio.

        Returns (best_ratio, best_snippet).
        """
        norm_query = cls._normalize(query)
        norm_corpus = cls._normalize(corpus)
        window = cls.FUZZY_WINDOW
        best_ratio = 0.0
        best_snippet: Optional[str] = None

        for i in range(0, max(1, len(norm_corpus) - window), window // 2):
            window_text = norm_corpus[i: i + window]
            ratio = difflib.SequenceMatcher(None, norm_query, window_text).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                # Extract a centred context snippet from the original (non-normalised) corpus
                start = max(0, i - 20)
                end = min(len(corpus), i + window + 20)
                best_snippet = corpus[start:end].strip()

        return best_ratio, best_snippet

    @classmethod
    def _confidence_score(cls, ratio: float, exact_found: bool) -> float:
        """
        Convert similarity ratio + exact-match flag to a 0-1 confidence score.
        """
        if exact_found:
            return 1.0
        # Scale fuzzy ratio to confidence
        return round(min(ratio * 1.2, 1.0), 3)  # slight boost

    # ------------------------------------------------------------------
    # Claim-type specific verifiers
    # ------------------------------------------------------------------

    @classmethod
    def _verify_single_claim(cls, claim_text: str, corpus: str) -> Dict[str, Any]:
        """
        Verify one claim string against the policy corpus.

        Returns
        -------
        {
          claim        : str,
          supported    : bool,
          confidence   : float (0-1),
          quote        : str | None,
          hallucination_risk: "low" | "medium" | "high"
        }
        """
        if not claim_text or not claim_text.strip():
            return {
                "claim": claim_text,
                "supported": False,
                "confidence": 0.0,
                "quote": None,
                "hallucination_risk": "high",
            }

        # Step 1 — exact search
        exact = cls._exact_search(claim_text, corpus)
        if exact:
            return {
                "claim": claim_text,
                "supported": True,
                "confidence": 1.0,
                "quote": exact,
                "hallucination_risk": "low",
            }

        # Step 2 — fuzzy search
        ratio, snippet = cls._fuzzy_search(claim_text, corpus)
        confidence = cls._confidence_score(ratio, False)
        supported = confidence >= cls.SIMILARITY_THRESHOLD

        if confidence >= 0.75:
            risk = "low"
        elif confidence >= cls.SIMILARITY_THRESHOLD:
            risk = "medium"
        else:
            risk = "high"

        return {
            "claim": claim_text,
            "supported": supported,
            "confidence": confidence,
            "quote": snippet if supported else None,
            "hallucination_risk": risk,
        }

    # ------------------------------------------------------------------
    # Section verifiers
    # ------------------------------------------------------------------

    @classmethod
    def _verify_data_collected(cls, items: List[Dict], corpus: str) -> List[Dict]:
        """Verify each collected-data claim."""
        results = []
        for item in items:
            claim = item.get("type", "") or item.get("name", "")
            v = cls._verify_single_claim(claim, corpus)
            v["original"] = item
            results.append(v)
        return results

    @classmethod
    def _verify_data_shared(cls, items: List[Dict], corpus: str) -> List[Dict]:
        """Verify each data-sharing claim."""
        results = []
        for item in items:
            claim = (item.get("recipient", "") + " " + item.get("data_type", "")).strip()
            v = cls._verify_single_claim(claim, corpus)
            v["original"] = item
            results.append(v)
        return results

    @classmethod
    def _verify_user_rights(cls, rights_dict: Dict, corpus: str) -> Dict[str, Any]:
        """Verify each user-rights assertion."""
        results = {}
        for right_name, right_value in rights_dict.items():
            claim = f"right to {right_name}" if right_value else ""
            if claim:
                results[right_name] = cls._verify_single_claim(claim, corpus)
            else:
                results[right_name] = {
                    "claim": claim,
                    "supported": False,
                    "confidence": 0.0,
                    "quote": None,
                    "hallucination_risk": "high",
                }
        return results

    @classmethod
    def _verify_red_flags(cls, flags: List[Dict], corpus: str) -> List[Dict]:
        """Verify each red-flag claim using its quoted text."""
        results = []
        for flag in flags:
            quote = flag.get("quote", "") or flag.get("issue", "")
            v = cls._verify_single_claim(quote, corpus)
            v["original"] = flag
            results.append(v)
        return results

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    @classmethod
    def verify_claims(cls, llm_findings: Dict, original_text: str) -> Dict[str, Any]:
        """
        Cross-reference all LLM claims against *original_text*.

        Parameters
        ----------
        llm_findings  : dict — structured output from PrivacyAnalyzer
        original_text : str  — full cleaned policy text

        Returns
        -------
        dict with keys:
          data_collected_verified : list of verified claim dicts
          data_shared_verified    : list of verified claim dicts
          user_rights_verified    : dict of verified right dicts
          red_flags_verified      : list of verified flag dicts
          overall_confidence      : float 0-1 (mean confidence across all claims)
          hallucination_count     : int (claims with risk="high")
          summary                 : str
        """
        findings = llm_findings or {}
        corpus = original_text or ""

        data_collected_v = cls._verify_data_collected(
            findings.get("data_collected", []), corpus
        )
        data_shared_v = cls._verify_data_shared(
            findings.get("data_shared", []), corpus
        )
        user_rights_v = cls._verify_user_rights(
            findings.get("user_rights", {}), corpus
        )
        red_flags_v = cls._verify_red_flags(
            findings.get("red_flags", []), corpus
        )

        # Aggregate confidence scores
        all_confidences: List[float] = []
        hallucination_count = 0

        for item in data_collected_v + data_shared_v + red_flags_v:
            conf = item.get("confidence", 0.0)
            all_confidences.append(conf)
            if item.get("hallucination_risk") == "high":
                hallucination_count += 1

        for right_result in user_rights_v.values():
            conf = right_result.get("confidence", 0.0)
            all_confidences.append(conf)
            if right_result.get("hallucination_risk") == "high":
                hallucination_count += 1

        overall_confidence = (
            round(sum(all_confidences) / len(all_confidences), 3)
            if all_confidences else 0.0
        )

        total_claims = len(all_confidences)
        summary = (
            f"Verified {total_claims} claims. "
            f"Overall confidence: {overall_confidence:.0%}. "
            f"Potential hallucinations: {hallucination_count} "
            f"({hallucination_count/total_claims:.0%} of claims)."
            if total_claims else "No claims to verify."
        )

        return {
            "data_collected_verified": data_collected_v,
            "data_shared_verified": data_shared_v,
            "user_rights_verified": user_rights_v,
            "red_flags_verified": red_flags_v,
            "overall_confidence": overall_confidence,
            "hallucination_count": hallucination_count,
            "total_claims": total_claims,
            "summary": summary,
        }

    # ------------------------------------------------------------------
    # Cross-signal fusion (Issue #12)
    # ------------------------------------------------------------------

    @classmethod
    def cross_signal_escalation(
        cls,
        llm_findings: Dict,
        metrics: Dict,
        gdpr_basis: list,
    ) -> List[Dict[str, Any]]:
        """
        OUR CUSTOM CODE — fuses three independent signal sources:

        1. LLM red flags  (semantic, from Gemini)
        2. Dark-pattern detector score  (rule-based, our code)
        3. GDPR lawful-basis classifier  (keyword NLP, our code)

        When multiple signals converge on the same concern, escalate to
        CONFIRMED CRITICAL — a finding no single signal could produce alone.

        Parameters
        ----------
        llm_findings : dict  — validated Gemini output
        metrics      : dict  — preprocessor output (includes dark_pattern_score)
        gdpr_basis   : list  — output of GDPRLawfulBasisClassifier.classify()

        Returns
        -------
        List of confirmed-critical dicts: {issue, severity, signals, explanation}
        """
        confirmed: List[Dict[str, Any]] = []
        dark_score: float = float(metrics.get("dark_pattern_score", 0))
        red_flags: List[Dict] = llm_findings.get("red_flags", [])
        data_collected: List[Dict] = llm_findings.get("data_collected", [])
        has_gdpr_basis = bool(gdpr_basis)

        # ── Signal 1 × 2: LLM high/critical flag + dark-pattern score > 50 ──
        if dark_score > 50:
            high_flags = [
                f for f in red_flags
                if f.get("severity") in ("high", "critical")
            ]
            for flag in high_flags:
                confirmed.append({
                    "issue": flag.get("issue", "Unspecified issue"),
                    "severity": "critical",
                    "signals": ["llm_red_flag", "dark_pattern_detector"],
                    "explanation": (
                        f"LLM flagged: \"{flag.get('issue')}\". "
                        f"Corroborated by dark-pattern detector score {dark_score:.0f}/100. "
                        "Multi-signal convergence elevates this to CONFIRMED CRITICAL."
                    ),
                    "original_quote": flag.get("quote", ""),
                })

        # ── Signal 2 × 3: High-sensitivity data collected + no GDPR lawful basis ──
        if not has_gdpr_basis:
            high_sens = [
                d for d in data_collected
                if d.get("sensitivity") == "high"
            ]
            if high_sens:
                types_str = ", ".join(d.get("type", "Unknown") for d in high_sens[:3])
                confirmed.append({
                    "issue": f"High-sensitivity data collected without documented lawful basis",
                    "severity": "critical",
                    "signals": ["llm_data_extraction", "gdpr_classifier"],
                    "explanation": (
                        f"Gemini identified high-sensitivity data types: {types_str}. "
                        "Our GDPR classifier found no lawful basis (Art. 6) documented "
                        "in the policy text. Processing high-sensitivity data without a "
                        "lawful basis is a GDPR violation."
                    ),
                    "original_quote": "",
                })

        # ── Signal 1 × 3: LLM compliance gap + GDPR basis missing ──
        compliance = llm_findings.get("compliance_indicators", [])
        has_gdpr_indicator = any("gdpr" in c.lower() for c in compliance)
        if has_gdpr_indicator and not has_gdpr_basis:
            confirmed.append({
                "issue": "GDPR referenced but no lawful basis documented",
                "severity": "critical",
                "signals": ["llm_compliance", "gdpr_classifier"],
                "explanation": (
                    "The policy mentions GDPR compliance, but our keyword-based "
                    "GDPR classifier (Art. 6) found no documented lawful basis for "
                    "processing. Claiming GDPR compliance without stating a basis "
                    "is misleading."
                ),
                "original_quote": "",
            })

        # Deduplicate by issue text
        seen: set = set()
        unique: List[Dict] = []
        for c in confirmed:
            key = c["issue"].lower()[:60]
            if key not in seen:
                seen.add(key)
                unique.append(c)

        return unique

