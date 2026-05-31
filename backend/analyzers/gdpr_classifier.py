"""
analyzers/gdpr_classifier.py — GDPR Lawful Basis Classifier.

OUR CUSTOM CODE — NO LLM USED.
Maps data processing purposes to the 6 GDPR lawful bases using keyword matching.
"""

import re
from typing import Dict, List, Any

class GDPRLawfulBasisClassifier:
    """
    Identifies the 'Lawful Basis for Processing' according to GDPR Article 6.
    
    The 6 bases are:
    1. Consent
    2. Contract
    3. Legal Obligation
    4. Vital Interests
    5. Public Task
    6. Legitimate Interests
    """

    BASES = {
        "consent": {
            "name": "Consent",
            "keywords": [r"consent", r"opt-in", r"permission", r"agree to", r"freely given"],
            "description": "Processing with explicit user permission."
        },
        "contract": {
            "name": "Contractual Necessity",
            "keywords": [r"contract", r"terms of service", r"perform our obligations", r"provide the service", r"fulfillment"],
            "description": "Necessary to fulfill a contract with the user (e.g. shipping an order)."
        },
        "legal_obligation": {
            "name": "Legal Obligation",
            "keywords": [r"compliance", r"legal obligation", r"statutory", r"law enforcement", r"court order", r"regulatory"],
            "description": "Processing required by law (e.g. tax reporting)."
        },
        "vital_interests": {
            "name": "Vital Interests",
            "keywords": [r"vital interest", r"life or death", r"safety", r"emergency", r"health crisis"],
            "description": "Necessary to protect someone's life."
        },
        "public_task": {
            "name": "Public Task",
            "keywords": [r"public interest", r"official authority", r"public task", r"government function"],
            "description": "Processing for a task in the public interest or official authority."
        },
        "legitimate_interests": {
            "name": "Legitimate Interests",
            "keywords": [r"legitimate interest", r"business interest", r"fraud prevention", r"marketing", r"network security"],
            "description": "Processing for necessary business purposes balanced against user rights."
        }
    }

    @classmethod
    def classify(cls, text: str) -> List[Dict[str, Any]]:
        """
        Scan text for lawful basis mentions.
        Capped at first 10,000 characters for performance.
        """
        # Performance cap
        sample = text[:10000].lower()
        results = []

        for key, info in cls.BASES.items():
            matches = []
            for pattern in info["keywords"]:
                found = re.finditer(pattern, sample)
                for m in found:
                    # Extract a small context window
                    start = max(0, m.start() - 40)
                    end = min(len(sample), m.end() + 40)
                    context = text[start:end].strip().replace("\n", " ")
                    matches.append(context)
            
            if matches:
                results.append({
                    "basis": info["name"],
                    "description": info["description"],
                    "found_in_text": list(set(matches))[:2], # Unique excerpts, limit to 2
                    "count": len(matches)
                })
        
        return results
