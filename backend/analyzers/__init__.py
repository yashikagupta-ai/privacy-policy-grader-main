# analyzers/__init__.py
from .readability import ReadabilityAnalyzer
from .jargon_detector import LegalJargonDetector
from .dark_patterns import DarkPatternDetector
from .text_metrics import TextMetricsAnalyzer

__all__ = [
    "ReadabilityAnalyzer",
    "LegalJargonDetector",
    "DarkPatternDetector",
    "TextMetricsAnalyzer",
]
