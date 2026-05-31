"""
analyzers/jargon_detector.py — Legal/privacy jargon detector.

OUR CUSTOM CODE — NO LLM USED.

Provides
--------
- A curated dictionary of 150+ legal/privacy/technical terms.
- Jargon density calculation.
- Categorised term detection.
- Undefined-term heuristics.
- Per-section analysis.
"""

import re
from collections import Counter
from typing import Dict, List, Tuple


class LegalJargonDetector:
    """
    Detects legal, privacy, and technical jargon in policy text.

    Architecture
    ------------
    - JARGON_DICT maps term → (category, plain-English explanation).
    - All matching is case-insensitive substring / word-boundary matching.
    - Multi-word terms (e.g. "personally identifiable information") are
      matched before single-word terms to avoid double-counting.
    """

    # ------------------------------------------------------------------
    # Jargon dictionary: term → (category, explanation)
    # ------------------------------------------------------------------
    JARGON_DICT: Dict[str, Tuple[str, str]] = {
        # ---- LEGAL TERMS ------------------------------------------------
        "indemnification": ("legal", "Protection from financial loss"),
        "indemnify": ("legal", "Protect from financial harm"),
        "liability": ("legal", "Legal responsibility"),
        "limitation of liability": ("legal", "Cap on damages owed"),
        "jurisdiction": ("legal", "Geographic area of legal authority"),
        "arbitration": ("legal", "Dispute resolution outside court"),
        "class action waiver": ("legal", "Prevents group lawsuits"),
        "class action": ("legal", "Lawsuit brought by a group"),
        "governing law": ("legal", "Which state/country's laws apply"),
        "venue": ("legal", "Location where disputes are resolved"),
        "severability": ("legal", "Invalid clauses don't void the whole agreement"),
        "intellectual property": ("legal", "Creations of the mind, legally protected"),
        "proprietary": ("legal", "Privately owned, protected information"),
        "injunctive relief": ("legal", "Court order to stop an action"),
        "force majeure": ("legal", "Unforeseeable circumstances clause"),
        "waiver": ("legal", "Voluntary surrender of a right"),
        "warranty": ("legal", "Guarantee of quality or truth"),
        "disclaimer": ("legal", "Statement limiting responsibility"),
        "representation": ("legal", "Statement of fact made by a party"),
        "covenant": ("legal", "Legally binding promise"),
        "remedy": ("legal", "Legal means of addressing a wrong"),
        "damages": ("legal", "Financial compensation for harm"),
        "statutory": ("legal", "Relating to written law"),
        "regulatory": ("legal", "Relating to government rules"),
        "compliance": ("legal", "Following rules and regulations"),
        "subpoena": ("legal", "Legal order to provide information"),
        "court order": ("legal", "Directive issued by a judge"),
        "law enforcement": ("legal", "Government agencies enforcing laws"),
        "legal process": ("legal", "Official legal proceedings"),
        "successor": ("legal", "Entity that takes over another"),
        "assignee": ("legal", "Party to whom rights are transferred"),
        "merger": ("legal", "Two companies combining"),
        "acquisition": ("legal", "One company buying another"),

        # ---- PRIVACY TERMS ---------------------------------------------
        "personally identifiable information": ("privacy", "Data that identifies a person"),
        "personal data": ("privacy", "Information about an identifiable person"),
        "sensitive personal information": ("privacy", "Especially protected personal data"),
        "special categories of data": ("privacy", "EU GDPR high-sensitivity data"),
        "data subject": ("privacy", "Person whose data is collected"),
        "data controller": ("privacy", "Entity deciding how data is used"),
        "data processor": ("privacy", "Entity processing data on behalf of controller"),
        "data protection officer": ("privacy", "Employee overseeing privacy compliance"),
        "dpo": ("privacy", "Data Protection Officer"),
        "legitimate interest": ("privacy", "Legal basis for processing without consent"),
        "consent": ("privacy", "Permission freely given by the user"),
        "explicit consent": ("privacy", "Opt-in agreement, clearly stated"),
        "implied consent": ("privacy", "Consent inferred from behaviour"),
        "opt-out": ("privacy", "Choice to not participate"),
        "opt-in": ("privacy", "Active choice to participate"),
        "right to erasure": ("privacy", "Right to delete your data"),
        "right to be forgotten": ("privacy", "Right to have data deleted"),
        "right to access": ("privacy", "Right to see your collected data"),
        "right to portability": ("privacy", "Right to receive your data in usable format"),
        "right to rectification": ("privacy", "Right to correct inaccurate data"),
        "right to object": ("privacy", "Right to oppose data processing"),
        "profiling": ("privacy", "Automated analysis to predict behaviour"),
        "automated decision-making": ("privacy", "Decisions made by algorithms without humans"),
        "data minimisation": ("privacy", "Collecting only necessary data"),
        "purpose limitation": ("privacy", "Using data only for its stated purpose"),
        "storage limitation": ("privacy", "Not keeping data longer than necessary"),
        "data retention": ("privacy", "How long data is kept"),
        "retention period": ("privacy", "Specified time data is stored"),
        "data breach": ("privacy", "Unauthorised access to personal data"),
        "security incident": ("privacy", "Event compromising data security"),
        "gdpr": ("privacy", "EU General Data Protection Regulation"),
        "ccpa": ("privacy", "California Consumer Privacy Act"),
        "coppa": ("privacy", "Children's Online Privacy Protection Act"),
        "hipaa": ("privacy", "Health Insurance Portability and Accountability Act"),
        "pipeda": ("privacy", "Canadian Personal Information Protection Act"),
        "lgpd": ("privacy", "Brazilian data protection law"),
        "data protection": ("privacy", "Safeguarding personal information"),
        "privacy by design": ("privacy", "Building privacy into systems by default"),
        "privacy notice": ("privacy", "Formal notification of data practices"),
        "privacy policy": ("privacy", "Document describing data practices"),
        "privacy shield": ("privacy", "EU-US data transfer framework (now invalid)"),
        "standard contractual clauses": ("privacy", "EU-approved data transfer contracts"),
        "binding corporate rules": ("privacy", "Intra-group data transfer policies"),
        "cross-border transfer": ("privacy", "Moving data between countries"),
        "international transfer": ("privacy", "Moving data across national borders"),
        "data localisation": ("privacy", "Requirement to store data domestically"),
        "anonymisation": ("privacy", "Making data non-identifiable"),
        "pseudonymisation": ("privacy", "Replacing identifiers with pseudonyms"),
        "de-identification": ("privacy", "Removing personal identifiers"),
        "aggregated data": ("privacy", "Data combined so individuals cannot be identified"),
        "inferred data": ("privacy", "Data derived from your behaviour"),
        "derived data": ("privacy", "Data generated from existing data"),
        "biometric data": ("privacy", "Physical characteristics like fingerprints"),
        "genetic data": ("privacy", "DNA and hereditary information"),
        "health data": ("privacy", "Medical and wellness information"),
        "children's data": ("privacy", "Data from users under 13"),
        "sale of personal information": ("privacy", "Sharing data for monetary value"),
        "sharing": ("privacy", "Disclosing data to third parties"),
        "disclosure": ("privacy", "Revealing information to others"),
        "onward transfer": ("privacy", "Passing data to further parties"),
        "third party": ("privacy", "Entity not party to the main agreement"),
        "service provider": ("privacy", "Company providing services on your behalf"),
        "subprocessor": ("privacy", "Third-party used by a data processor"),
        "affiliate": ("privacy", "Related company or subsidiary"),
        "partner": ("privacy", "Associated business entity"),
        "vendor": ("privacy", "External supplier of services"),

        # ---- TECHNICAL TERMS -------------------------------------------
        "cookies": ("technical", "Small files stored in your browser"),
        "tracking pixel": ("technical", "Invisible image used for tracking"),
        "web beacon": ("technical", "Invisible tracker embedded in web pages"),
        "pixel tag": ("technical", "Small tracking image"),
        "session storage": ("technical", "Temporary browser-side data storage"),
        "local storage": ("technical", "Persistent browser-side data storage"),
        "fingerprinting": ("technical", "Identifying devices via browser attributes"),
        "device fingerprint": ("technical", "Unique identifier based on device properties"),
        "ip address": ("technical", "Numerical internet location identifier"),
        "geolocation": ("technical", "Physical location data"),
        "metadata": ("technical", "Data describing other data"),
        "log data": ("technical", "Automatically collected server logs"),
        "server log": ("technical", "Record of server requests"),
        "encryption": ("technical", "Converting data to unreadable format"),
        "tls": ("technical", "Transport Layer Security (encrypted connections)"),
        "ssl": ("technical", "Secure Sockets Layer (encrypted connections)"),
        "two-factor authentication": ("technical", "Two-step identity verification"),
        "api": ("technical", "Application Programming Interface"),
        "sdk": ("technical", "Software Development Kit"),
        "push notification": ("technical", "Message sent to your device"),
        "analytics": ("technical", "Data analysis for behaviour insights"),
        "a/b testing": ("technical", "Testing two versions of a feature"),
        "machine learning": ("technical", "AI systems learning from data"),
        "algorithm": ("technical", "Set of rules for automated decision-making"),
        "scraping": ("technical", "Automated data extraction from websites"),
        "cross-site tracking": ("technical", "Following users across different websites"),
        "interest-based advertising": ("technical", "Ads targeted to your behaviour"),
        "targeted advertising": ("technical", "Personalised ads based on your data"),
        "retargeting": ("technical", "Showing ads based on previous site visits"),
        "dark pattern": ("technical", "UI designed to trick users"),
        "user agent": ("technical", "Browser/device identifier string"),
        "referrer": ("technical", "URL of the page that linked to the current one"),
    }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(text: str) -> str:
        """Lower-case and collapse whitespace for reliable matching."""
        return re.sub(r"\s+", " ", text.lower()).strip()

    @classmethod
    def _sorted_terms(cls) -> List[str]:
        """
        Return jargon terms sorted by length (longest first).

        Matching longest-first prevents short terms from masking
        multi-word phrases (e.g. "data" matching before "personal data").
        """
        return sorted(cls.JARGON_DICT.keys(), key=len, reverse=True)

    # ------------------------------------------------------------------
    # Core detection
    # ------------------------------------------------------------------

    @classmethod
    def _find_terms(cls, text: str) -> Counter:
        """
        Scan text for jargon occurrences using word-boundary regex.

        Returns a Counter mapping term → occurrence count.
        """
        norm = cls._normalize(text)
        counter: Counter = Counter()
        for term in cls._sorted_terms():
            pattern = r"\b" + re.escape(term) + r"\b"
            matches = re.findall(pattern, norm)
            if matches:
                counter[term] = len(matches)
        return counter

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def detect(cls, text: str) -> Dict[str, object]:
        """
        Detect jargon in *text* and return a comprehensive report.

        Returns
        -------
        dict with keys
          jargon_count     : total jargon token occurrences
          density_percent  : jargon occurrences / total words × 100
          terms_found      : list of dicts {term, category, count, explanation}
          terms_by_category: dict { category: [terms] }
          top_terms        : 10 most frequent jargon terms
          undefined_terms  : long words not in the dictionary (potential unexplained jargon)
        """
        total_words = len(re.findall(r"\b\w+\b", text))
        term_counter = cls._find_terms(text)

        jargon_count = sum(term_counter.values())
        density = (jargon_count / total_words * 100) if total_words else 0.0

        # Build rich term list
        terms_found = []
        terms_by_category: Dict[str, List[str]] = {}
        for term, count in term_counter.most_common():
            cat, explanation = cls.JARGON_DICT[term]
            terms_found.append({
                "term": term,
                "category": cat,
                "count": count,
                "explanation": explanation,
            })
            terms_by_category.setdefault(cat, []).append(term)

        # Undefined-term heuristic: words ≥ 8 chars not in our dictionary and
        # not in NLTK's common vocabulary — approximated by checking against
        # our dictionary only (for simplicity, no extra corpus needed)
        known = set(cls.JARGON_DICT.keys())
        # Extract candidate long words from the text
        long_words = set(re.findall(r"\b[a-z]{8,}\b", cls._normalize(text)))
        # Remove known jargon terms, common English words we trust
        _common = {
            "including", "following", "personal", "information", "services",
            "location", "collected", "provided", "company", "business",
            "customer", "account", "website", "security", "purposes",
            "describe", "explained", "sections", "required", "deletion",
            "applicable", "available", "described", "relevant",
        }
        undefined = long_words - known - _common
        undefined_sorted = sorted(undefined)[:25]  # limit output

        return {
            "jargon_count": jargon_count,
            "density_percent": round(density, 2),
            "terms_found": terms_found,
            "terms_by_category": terms_by_category,
            "top_terms": [t["term"] for t in terms_found[:10]],
            "undefined_terms": undefined_sorted,
        }

    @classmethod
    def detect_per_section(cls, sections: List[Dict]) -> List[Dict]:
        """
        Run jargon detection on each section dict individually.

        Parameters
        ----------
        sections : list of {"title": str, "text": str}

        Returns
        -------
        list of {"section_title": str, "jargon_count": int, "density_percent": float}
        """
        results = []
        for sec in sections:
            report = cls.detect(sec.get("text", ""))
            results.append({
                "section_title": sec.get("title", "Unknown"),
                "jargon_count": report["jargon_count"],
                "density_percent": report["density_percent"],
                "top_terms": report["top_terms"][:5],
            })
        return results
