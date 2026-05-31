"""
services/llm_service.py — ONLY file that calls Google Gemini API.

This is the single point of LLM interaction for the entire project.
All other analysis is performed by our custom Python code.

Responsibilities
----------------
- Truncate policy text to fit within Gemini's context window.
- Build a structured JSON-mode prompt with pre-computed metrics.
- Call Gemini API and parse the response.
- Return a validated, typed findings dict.
- Fall back gracefully (demo mode) when no API key is available.
"""

import json
import re
from typing import Any, Dict, List, Optional

# Severity ordering for red flag sorting (lower = more severe)
_SEVERITY_ORDER: Dict[str, int] = {"critical": 0, "high": 1, "medium": 2, "low": 3}

from config import Config

# ---------------------------------------------------------------------------
# Demo-mode mock response (used when GEMINI_API_KEY is absent)
# ---------------------------------------------------------------------------

_DEMO_RESPONSE: Dict[str, Any] = {
    "data_collected": [
        {"type": "Email address", "purpose": "Account creation and communications", "sensitivity": "medium"},
        {"type": "IP address", "purpose": "Security and fraud prevention", "sensitivity": "low"},
        {"type": "Browsing behaviour", "purpose": "Personalisation and analytics", "sensitivity": "medium"},
        {"type": "Location data", "purpose": "Tailoring content to your region", "sensitivity": "high"},
        {"type": "Device identifiers", "purpose": "Cross-device tracking", "sensitivity": "medium"},
        {"type": "Payment information", "purpose": "Processing transactions", "sensitivity": "high"},
    ],
    "data_shared": [
        {"recipient": "Analytics providers (e.g. Google Analytics)", "data_type": "Browsing behaviour", "opt_out_available": True},
        {"recipient": "Advertising networks", "data_type": "Device identifiers + interests", "opt_out_available": True},
        {"recipient": "Payment processors", "data_type": "Payment information", "opt_out_available": False},
        {"recipient": "Law enforcement (upon legal request)", "data_type": "Account data", "opt_out_available": False},
    ],
    "user_rights": {
        "access": "Users may request a copy of their personal data via the account settings or by emailing privacy@example.com.",
        "deletion": "Users may request deletion of their account and associated data; some data may be retained for legal obligations.",
        "portability": "Data can be exported in JSON format from the account dashboard.",
        "correction": "Inaccurate data can be corrected through account settings.",
    },
    "red_flags": [
        {
            "issue": "Vague 'improve our services' justification",
            "severity": "medium",
            "quote": "We may use your data to improve our services and develop new features.",
            "explanation": "This catch-all purpose allows virtually unlimited data processing without specific justification.",
        },
        {
            "issue": "Implied consent by platform use",
            "severity": "high",
            "quote": "By continuing to use our platform, you agree to this privacy policy.",
            "explanation": "Continued use cannot substitute for freely given, informed, and specific consent under GDPR.",
        },
        {
            "issue": "Unnamed advertising partners",
            "severity": "high",
            "quote": "We share data with our trusted advertising partners.",
            "explanation": "Partners are not named, preventing users from making informed decisions.",
        },
    ],
    "compliance_indicators": [
        "GDPR Article 13/14 notice present",
        "CCPA 'Do Not Sell' link mentioned",
        "Data retention periods stated for most categories",
    ],
    "summary": (
        "This privacy policy demonstrates moderate transparency. "
        "It discloses the main categories of collected data and identifies several user rights. "
        "However, it uses vague language in several key areas, particularly around third-party "
        "sharing and the legal basis for processing. The 'implied consent by use' clause is a "
        "significant red flag under GDPR. Overall, the policy requires improvement in clarity "
        "and specificity to fully meet modern privacy standards."
    ),
}


# ---------------------------------------------------------------------------
# Red-flag post-processing helper
# ---------------------------------------------------------------------------

def _dedup_and_sort_flags(red_flags: List[Dict]) -> List[Dict]:
    """
    1. Deduplicate flags with identical issue text (case-insensitive, first 80 chars).
    2. Sort critical → high → medium → low.
    3. Cap at 15 flags.
    """
    seen: set = set()
    unique: List[Dict] = []
    for flag in red_flags:
        key = (flag.get("issue") or "").lower().strip()[:80]
        if key and key not in seen:
            seen.add(key)
            unique.append(flag)
    unique.sort(key=lambda f: _SEVERITY_ORDER.get(f.get("severity", "medium"), 2))
    return unique[:15]


# ---------------------------------------------------------------------------
# PrivacyAnalyzer class
# ---------------------------------------------------------------------------


class PrivacyAnalyzer:
    """
    Wraps the Gemini API for structured privacy-policy analysis.

    THIS IS THE ONLY CLASS IN THE PROJECT THAT CALLS GEMINI.

    All other analysis (readability, jargon, dark patterns, grading,
    verification) is performed by our own Python code.
    """

    def __init__(self) -> None:
        self._client = None  # lazy initialisation
        self._demo = Config.DEMO_MODE

        if not self._demo:
            try:
                import google.generativeai as genai
                genai.configure(api_key=Config.GEMINI_API_KEY)
                self._client = genai.GenerativeModel(
                    model_name=Config.GEMINI_MODEL,
                    generation_config={
                        "temperature": Config.GEMINI_TEMPERATURE,
                        "max_output_tokens": Config.GEMINI_MAX_TOKENS,
                        "response_mime_type": "application/json",
                    },
                )
            except Exception as exc:
                print(f"[llm_service] Gemini init failed: {exc}. Falling back to demo mode.")
                self._demo = True

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(policy_text: str, metrics: Dict) -> str:
        """
        Construct a structured JSON-mode prompt for Gemini.

        The prompt includes:
        - Pre-computed NLP metrics (so Gemini doesn't re-derive them)
        - The policy text (truncated)
        - Exact output schema
        - Chain-of-thought instruction
        """
        truncated = policy_text[:Config.LLM_MAX_CHARS]

        # Format key metrics for context
        metrics_summary = (
            f"- Word count: {metrics.get('word_count', 'unknown')}\n"
            f"- Flesch Reading Ease: {metrics.get('flesch_reading_ease', 'unknown')} "
            f"(higher = easier; 0-100 scale)\n"
            f"- Flesch-Kincaid Grade Level: {metrics.get('flesch_kincaid_grade', 'unknown')}\n"
            f"- Jargon density: {metrics.get('jargon_density', 0):.1f}%\n"
            f"- Third-party mentions: {metrics.get('third_party_mentions', 0)}\n"
            f"- User-rights mentions: {metrics.get('user_rights_mentions', 0)}\n"
            f"- Opt-out present: {metrics.get('opt_out_presence', False)}\n"
            f"- GDPR mentioned: {metrics.get('gdpr_mentions', {}).get('mentioned', False)}\n"
            f"- CCPA mentioned: {metrics.get('ccpa_mentions', {}).get('mentioned', False)}\n"
            f"- COPPA mentioned: {metrics.get('children_privacy', {}).get('mentioned', False)}\n"
            f"- Dark pattern score: {metrics.get('dark_pattern_score', 0):.1f}/100\n"
            f"- Section count: {metrics.get('section_count', 0)}\n"
        )

        prompt = f"""You are an expert privacy-policy analyst. Analyse the privacy policy below.

PRE-COMPUTED METRICS (use these as context, do not recalculate):
{metrics_summary}

PRIVACY POLICY TEXT:
---
{truncated}
---

TASK:
Extract and analyse the privacy policy's practices. Think step-by-step:
1. Identify every category of personal data collected.
2. Identify who data is shared with and for what purpose.
3. Identify what user rights are explicitly granted.
4. Identify red flags — vague, manipulative, or user-hostile language.
5. Note compliance indicators (GDPR/CCPA/COPPA references).
6. Write a concise, plain-English summary.

OUTPUT FORMAT — return ONLY valid JSON matching this schema exactly:
{{
  "data_collected": [
    {{"type": "string", "purpose": "string", "sensitivity": "low|medium|high"}}
  ],
  "data_shared": [
    {{"recipient": "string", "data_type": "string", "opt_out_available": true|false}}
  ],
  "user_rights": {{
    "access": "string describing access mechanism, or null",
    "deletion": "string describing deletion process, or null",
    "portability": "string describing portability, or null",
    "correction": "string describing correction process, or null"
  }},
  "red_flags": [
    {{"issue": "string", "severity": "low|medium|high|critical",
      "quote": "exact quote from policy", "explanation": "string"}}
  ],
  "compliance_indicators": ["string", ...],
  "summary": "Plain-English paragraph summarising overall privacy posture."
}}"""
        return prompt

    # ------------------------------------------------------------------
    # Response validation / normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_response(raw: Dict) -> Dict:
        """
        Ensure the response matches our schema.
        Fill in missing keys with safe defaults.
        """
        def ensure_list(key: str) -> list:
            val = raw.get(key, [])
            return val if isinstance(val, list) else []

        def ensure_dict(key: str) -> dict:
            val = raw.get(key, {})
            return val if isinstance(val, dict) else {}

        data_collected = ensure_list("data_collected")
        for item in data_collected:
            if not isinstance(item, dict):
                continue
            item.setdefault("type", "Unknown")
            item.setdefault("purpose", "unspecified")
            item.setdefault("sensitivity", "medium")

        data_shared = ensure_list("data_shared")
        for item in data_shared:
            if not isinstance(item, dict):
                continue
            item.setdefault("recipient", "Unknown")
            item.setdefault("data_type", "Unknown")
            item.setdefault("opt_out_available", False)

        user_rights = ensure_dict("user_rights")
        for right in ("access", "deletion", "portability", "correction"):
            user_rights.setdefault(right, None)

        red_flags = ensure_list("red_flags")
        for flag in red_flags:
            if not isinstance(flag, dict):
                continue
            flag.setdefault("issue", "Unknown issue")
            flag.setdefault("severity", "medium")
            flag.setdefault("quote", "")
            flag.setdefault("explanation", "")

        red_flags = _dedup_and_sort_flags(red_flags)

        return {
            "data_collected": data_collected,
            "data_shared": data_shared,
            "user_rights": user_rights,
            "red_flags": red_flags,
            "compliance_indicators": ensure_list("compliance_indicators"),
            "summary": raw.get("summary", "No summary available."),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_with_gemini(
        self,
        policy_text: str,
        preprocessor_metrics: Dict,
    ) -> Dict[str, Any]:
        """
        Analyse a privacy policy using Gemini.

        Parameters
        ----------
        policy_text          : str  — clean policy text
        preprocessor_metrics : dict — output of PolicyPreprocessor.process()

        Returns
        -------
        Validated findings dict (matches schema above).
        If DEMO_MODE or API failure → returns realistic mock response.
        """
        # Demo mode — return mock without calling API
        if self._demo or self._client is None:
            print("[llm_service] Running in DEMO MODE — returning mock response.")
            return dict(_DEMO_RESPONSE)  # return a copy

        prompt = self._build_prompt(policy_text, preprocessor_metrics)

        try:
            response = self._client.generate_content(prompt)
            raw_text = response.text.strip()

            # Strip markdown code fences if present
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text)

            raw_dict = json.loads(raw_text)
            return self._validate_response(raw_dict)

        except json.JSONDecodeError as exc:
            print(f"[llm_service] JSON parse error: {exc}. Returning demo response.")
            return dict(_DEMO_RESPONSE)

        except Exception as exc:
            print(f"[llm_service] Gemini API error: {exc}. Returning demo response.")
            return dict(_DEMO_RESPONSE)
