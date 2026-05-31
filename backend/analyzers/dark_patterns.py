"""
analyzers/dark_patterns.py — Dark-pattern manipulation detector.

OUR CUSTOM CODE — NO LLM USED.

Identifies 15+ categories of manipulative or user-hostile language
patterns commonly found in privacy policies, using regex-based detection.
Each pattern carries a severity score (1–5).

Pattern categories
------------------
1.  AMBIGUITY — vague language that hides data practices
2.  HIDDEN_SHARING — obscuring who data is shared with
3.  USER_HOSTILE — language designed to override user agency
4.  OBSCURITY — structural factors making comprehension difficult
5.  SCOPE_CREEP — broad, open-ended claims
6.  CONSENT_BYPASS — treating continued use as blanket consent
7.  TEMPORAL_VAGUENESS — undefined timeframes
8.  UNSPECIFIED_RECIPIENTS — unnamed parties receiving data
9.  BURIED_RIGHTS — minimising or obscuring user rights
10. DECEPTIVE_REASSURANCE — false sense of security
11. PASSIVE_RESPONSIBILITY — evading accountability
12. CHILDREN_LOOPHOLE — weak protections for minors
13. UNILATERAL_CHANGE — ability to change terms without notice
14. DATA_MONETISATION — selling or monetising data without clarity
15. FORCED_ARBITRATION — removing right to sue
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List


# ---------------------------------------------------------------------------
# Pattern specification dataclass
# ---------------------------------------------------------------------------

@dataclass
class PatternSpec:
    """Describes a single dark-pattern rule."""
    name: str
    category: str
    regex: str
    severity: int  # 1 (low nuisance) → 5 (serious user harm)
    explanation: str


# ---------------------------------------------------------------------------
# Dark-pattern catalogue
# ---------------------------------------------------------------------------

DARK_PATTERNS: List[PatternSpec] = [

    # 1. AMBIGUITY ─────────────────────────────────────────────────────────
    PatternSpec(
        name="Vague modal verbs",
        category="AMBIGUITY",
        regex=r"\bwe (may|might|could|can) (?:\w+\s){0,4}(collect|use|share|disclose|process|sell)\b",
        severity=3,
        explanation="'May' / 'might' allow any behaviour without commitment.",
    ),
    PatternSpec(
        name="Unspecified quantifiers",
        category="AMBIGUITY",
        regex=r"\b(some|certain|various|several|appropriate|relevant|reasonable)\s+(type|kind|categor|manner|purpose|third|partner)",
        severity=2,
        explanation="Leaves scope undefined so almost anything is permitted.",
    ),
    PatternSpec(
        name="Open-ended enumeration",
        category="AMBIGUITY",
        regex=r"\bincluding but not limited to\b",
        severity=3,
        explanation="Renders any listed items non-exhaustive — anything goes.",
    ),
    PatternSpec(
        name="Vague purpose statement",
        category="AMBIGUITY",
        regex=r"\b(improve|enhance|personalise|optimize|better) (our )?(services|experience|products|platform|content)\b",
        severity=2,
        explanation="'Improving services' is an all-purpose justification for data use.",
    ),

    # 2. HIDDEN SHARING ────────────────────────────────────────────────────
    PatternSpec(
        name="Unnamed third-party sharing",
        category="HIDDEN_SHARING",
        regex=r"\b(partners?|affiliates?|trusted third part(y|ies)|service providers?|vendors?|contractors?)\b(?!.*\bname|\blist\b|\bsuch as\b)",
        severity=4,
        explanation="Data shared with unnamed parties hides who sees your data.",
    ),
    PatternSpec(
        name="Business transaction disclosure",
        category="HIDDEN_SHARING",
        regex=r"\b(merger|acquisition|sale of (?:the )?(?:company|business|assets)|corporate transaction)\b",
        severity=3,
        explanation="Your data can be transferred to unknown new owners.",
    ),

    # 3. USER HOSTILE ──────────────────────────────────────────────────────
    PatternSpec(
        name="Implied consent by use",
        category="CONSENT_BYPASS",
        regex=r"\bby (using|accessing|visiting|continuing to use) (this|our|the) (site|service|platform|app|product|website)\b.{0,80}(agree|consent|accept|bound)\b",
        severity=5,
        explanation="Treating site usage as consent bypasses GDPR/CCPA requirements.",
    ),
    PatternSpec(
        name="Negative opt-out framing",
        category="USER_HOSTILE",
        regex=r"\byou (cannot|can not|may not) opt[- ]?out\b",
        severity=5,
        explanation="Removes user's right to withdraw consent.",
    ),
    PatternSpec(
        name="Unilateral policy changes",
        category="USER_HOSTILE",
        regex=r"\bwe (may|reserve the right to|can) (change|update|modify|revise|amend) (this|our) (policy|terms|agreement)\b(?!.*\bnotify\b|\bnotice\b)",
        severity=4,
        explanation="Policy can change without warning, invalidating prior consent.",
    ),

    # 4. TEMPORAL VAGUENESS ────────────────────────────────────────────────
    PatternSpec(
        name="Indefinite retention language",
        category="TEMPORAL_VAGUENESS",
        regex=r"\b(as long as (necessary|needed|required|we deem|appropriate)|for an (indefinite|unspecified|extended) period|for a period determined by us)\b",
        severity=4,
        explanation="No clear limit on how long your data is stored.",
    ),
    PatternSpec(
        name="Temporal vagueness — from time to time",
        category="TEMPORAL_VAGUENESS",
        regex=r"\bfrom time to time\b",
        severity=2,
        explanation="Changes without defined schedule.",
    ),

    # 5. SCOPE CREEP ───────────────────────────────────────────────────────
    PatternSpec(
        name="Catch-all data collection",
        category="SCOPE_CREEP",
        regex=r"\b(any|all) (information|data|content|material) (you|that you) (provide|submit|upload|share|post)\b",
        severity=3,
        explanation="Claims rights over every piece of submitted content.",
    ),
    PatternSpec(
        name="Inferred data collection",
        category="SCOPE_CREEP",
        regex=r"\b(infer|inferred|derive|derived|deduce|deduced) (from|about|regarding)\b",
        severity=3,
        explanation="Creates new data about you beyond what you submitted.",
    ),

    # 6. DECEPTIVE REASSURANCE ─────────────────────────────────────────────
    PatternSpec(
        name="False security reassurance",
        category="DECEPTIVE_REASSURANCE",
        regex=r"\bwe take (your privacy|security|data protection) (seriously|very seriously)\b",
        severity=1,
        explanation="A claim without substance — often accompanied by weak practices.",
    ),
    PatternSpec(
        name="We never sell — but share",
        category="DECEPTIVE_REASSURANCE",
        regex=r"\bwe (do not|don't|never) sell .{0,40}\bpersonal (data|information)\b",
        severity=2,
        explanation="Often used when data is shared for equivalent value without technically 'selling'.",
    ),

    # 7. PASSIVE RESPONSIBILITY ────────────────────────────────────────────
    PatternSpec(
        name="Responsibility deflection",
        category="PASSIVE_RESPONSIBILITY",
        regex=r"\b(we are not responsible|we cannot|we do not control|we are not liable)\b.{0,80}(third.part|partner|vendor|breach)\b",
        severity=3,
        explanation="Disclaims all responsibility for third-party handling of your data.",
    ),

    # 8. FORCED ARBITRATION ────────────────────────────────────────────────
    PatternSpec(
        name="Mandatory arbitration",
        category="FORCED_ARBITRATION",
        regex=r"\b(mandatory|binding|compulsory) arbitration\b",
        severity=5,
        explanation="Strips your right to sue in court.",
    ),
    PatternSpec(
        name="Class-action waiver",
        category="FORCED_ARBITRATION",
        regex=r"\bclass.action (waiver|prohibited|not permitted|you waive)\b",
        severity=5,
        explanation="Prevents joining with others affected by the same harm.",
    ),

    # 9. DATA MONETISATION ─────────────────────────────────────────────────
    PatternSpec(
        name="Advertising and monetisation",
        category="DATA_MONETISATION",
        regex=r"\b(targeted|interest.based|behavioural) (advertising|ads|marketing)\b",
        severity=3,
        explanation="Your data is used to target you with commercial messages.",
    ),
    PatternSpec(
        name="Data sale language",
        category="DATA_MONETISATION",
        regex=r"\bsell (your|personal|user) (data|information)\b",
        severity=5,
        explanation="Explicit selling of personal data.",
    ),
]


# ---------------------------------------------------------------------------
# Detector class
# ---------------------------------------------------------------------------

class DarkPatternDetector:
    """
    Runs the full catalogue of dark-pattern regexes against a policy text.

    Usage
    -----
    result = DarkPatternDetector.detect(policy_text)
    print(result["severity_level"])   # "High"
    print(result["score"])            # 0-100
    """

    @classmethod
    def _apply_pattern(cls, text: str, spec: PatternSpec) -> List[str]:
        """
        Find all matches of *spec.regex* in *text*.

        Returns
        -------
        List of up to 3 matching snippets (truncated to 150 chars each).
        """
        try:
            matches = re.finditer(spec.regex, text, flags=re.IGNORECASE | re.DOTALL)
            snippets = []
            for m in matches:
                start = max(0, m.start() - 30)
                end = min(len(text), m.end() + 50)
                snippets.append(text[start:end].strip())
            return snippets[:3]
        except re.error:
            return []

    @classmethod
    def detect(cls, text: str, word_count: int = 0, fk_grade: float = 0.0,
               jargon_density: float = 0.0) -> Dict[str, object]:
        """
        Detect dark patterns in *text*.

        Parameters
        ----------
        text          : str   — cleaned policy text
        word_count    : int   — pre-computed word count (for length check)
        fk_grade      : float — Flesch-Kincaid grade (for readability check)
        jargon_density: float — jargon density % (for complexity check)

        Returns
        -------
        dict with keys:
          score           (0–100)
          severity_level  ("Low" | "Medium" | "High" | "Critical")
          patterns_found  list of {pattern, category, severity, examples, explanation}
          category_counts dict { category: count }
        """
        total_weighted = 0
        max_weighted = sum(p.severity for p in DARK_PATTERNS)

        # Structural/obscurity checks based on metrics (no regex needed)
        structural_flags: List[Dict] = []

        if word_count > 5000:
            structural_flags.append({
                "pattern": "Extremely long policy",
                "category": "OBSCURITY",
                "severity": 3,
                "examples": [f"Policy is {word_count} words (>5,000 threshold)"],
                "explanation": "Long policies are harder to read and understand.",
            })
            total_weighted += 3
            max_weighted += 3

        if fk_grade > 15:
            structural_flags.append({
                "pattern": "Very high reading level",
                "category": "OBSCURITY",
                "severity": 3,
                "examples": [f"Flesch-Kincaid grade {fk_grade:.1f} (>15 threshold)"],
                "explanation": "Requires graduate education to comprehend.",
            })
            total_weighted += 3
            max_weighted += 3

        if jargon_density > 20:
            structural_flags.append({
                "pattern": "Dense legal jargon",
                "category": "OBSCURITY",
                "severity": 3,
                "examples": [f"Jargon density {jargon_density:.1f}% (>20% threshold)"],
                "explanation": "Heavy jargon makes policies inaccessible to ordinary users.",
            })
            total_weighted += 3
            max_weighted += 3

        # Regex-based pattern checks
        found: List[Dict] = []
        category_counts: Dict[str, int] = {}

        for spec in DARK_PATTERNS:
            snippets = cls._apply_pattern(text, spec)
            if snippets:
                total_weighted += spec.severity
                category_counts[spec.category] = category_counts.get(spec.category, 0) + 1
                found.append({
                    "pattern": spec.name,
                    "category": spec.category,
                    "severity": spec.severity,
                    "examples": snippets,
                    "explanation": spec.explanation,
                })

        # Aggregate score (0-100)
        score = (total_weighted / max_weighted * 100) if max_weighted else 0.0

        # Severity label
        if score >= 75:
            level = "Critical"
        elif score >= 50:
            level = "High"
        elif score >= 25:
            level = "Medium"
        else:
            level = "Low"

        return {
            "score": round(score, 2),
            "severity_level": level,
            "patterns_found": structural_flags + found,
            "category_counts": category_counts,
        }
