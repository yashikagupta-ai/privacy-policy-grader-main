"""
utils/text_cleaner.py — HTML → clean plain text pipeline.

OUR CUSTOM CODE — NO LLM USED.

All transformations are deterministic string/regex operations.
Used by the scraper before passing text to the preprocessor.
"""

import re
import unicodedata
from typing import Optional

from bs4 import BeautifulSoup


class TextCleaner:
    """
    Converts raw HTML (or already-decoded text) into clean,
    normalised plain text suitable for NLP analysis.

    Design principle
    ----------------
    Every method is a *pure function* — it takes a string and returns a
    string.  The class method ``clean()`` chains them in the correct order.
    """

    # ------------------------------------------------------------------
    # Step 1 — HTML deconstruction
    # ------------------------------------------------------------------

    @staticmethod
    def strip_html(html: str) -> str:
        """
        Remove all HTML markup, keeping only visible text content.

        Process
        -------
        1. Parse with html.parser for speed and robustness.
        2. Decompose <script>, <style>, <noscript> elements entirely.
        3. Replace block-level elements with newlines for paragraph structure.
        4. Call get_text() with space separator.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Destroy invisible elements
        for tag in soup.find_all(["script", "style", "noscript", "head", "meta", "link"]):
            tag.decompose()

        # Insert newlines at block boundaries to preserve paragraph breaks
        for tag in soup.find_all(["p", "div", "section", "article", "li", "br", "h1",
                                   "h2", "h3", "h4", "h5", "h6"]):
            tag.insert_before("\n")
            tag.insert_after("\n")

        return soup.get_text(separator=" ")

    # ------------------------------------------------------------------
    # Step 2 — Unicode normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def unicode_normalize(text: str) -> str:
        """
        Apply NFKC normalisation (collapses compatibility characters)
        and strip invisible control characters (U+0000–U+001F, U+007F–U+009F).
        """
        normalized = unicodedata.normalize("NFKC", text)
        # Remove control chars except newline (\n = 0x0A) and tab (\t = 0x09)
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", normalized)
        return cleaned

    # ------------------------------------------------------------------
    # Step 3 — Remove citations / footnote markers
    # ------------------------------------------------------------------

    @staticmethod
    def remove_citations(text: str) -> str:
        """
        Strip inline citation markers such as [1], [2], (1), (2),
        or superscript-style ¹²³.
        """
        # Bracketed numbers — [1], [12]
        text = re.sub(r"\[\d{1,4}\]", "", text)
        # Parenthetical numbers — (1), (12)
        text = re.sub(r"\(\d{1,4}\)", "", text)
        # Unicode superscript digits
        text = re.sub(r"[¹²³⁴⁵⁶⁷⁸⁹⁰]+", "", text)
        return text

    # ------------------------------------------------------------------
    # Step 4 — Normalise whitespace
    # ------------------------------------------------------------------

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """
        Collapse runs of spaces/tabs to a single space.
        Collapse runs of newlines (3+) to two newlines (one blank line).
        Strip leading/trailing whitespace from each line.
        """
        # Tabs → spaces
        text = text.replace("\t", " ")
        # Collapse horizontal whitespace
        text = re.sub(r" {2,}", " ", text)
        # Strip each line
        lines = [line.strip() for line in text.splitlines()]
        text = "\n".join(lines)
        # Collapse 3+ consecutive blank lines → 2
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # ------------------------------------------------------------------
    # Step 5 — Remove common boilerplate phrases
    # ------------------------------------------------------------------

    @staticmethod
    def remove_boilerplate(text: str) -> str:
        """
        Remove cookie consent notices, cookie-banner text, and common
        website navigation fragments that often bleed into scraped text.
        """
        boilerplate_patterns = [
            r"accept (all )?cookies?\.?",
            r"we use cookies to.*?\.",
            r"this (website|site) uses cookies.*?\.",
            r"your (privacy|cookie) (settings?|preferences?).*?\.",
            r"(enable|disable) cookies in your browser.*?\.",
            r"privacy settings?",
            r"skip to (main )?content",
            r"^back to top$",
        ]
        for pattern in boilerplate_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        return text

    # ------------------------------------------------------------------
    # Step 6 — Normalise line breaks
    # ------------------------------------------------------------------

    @staticmethod
    def normalize_line_breaks(text: str) -> str:
        """Normalise Windows/Mac line endings to Unix (\n)."""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        return text

    # ------------------------------------------------------------------
    # Step 7 — Remove URLs and email addresses (optional helper)
    # ------------------------------------------------------------------

    @staticmethod
    def remove_urls(text: str) -> str:
        """Strip raw URLs from the text (keeps surrounding prose)."""
        return re.sub(r"https?://\S+", "", text)

    # ------------------------------------------------------------------
    # Public API — full pipeline
    # ------------------------------------------------------------------

    @classmethod
    def clean(cls, raw_input: str, strip_urls: bool = False) -> str:
        """
        Run the complete cleaning pipeline.

        Parameters
        ----------
        raw_input : str
            Raw HTML or already-decoded text.
        strip_urls : bool
            If True, remove bare URLs from the output.  Default False because
            URLs in policy text can be evidence (e.g., opt-out links).

        Returns
        -------
        str
            Clean, normalised plain text.
        """
        text = cls.strip_html(raw_input)
        text = cls.normalize_line_breaks(text)
        text = cls.unicode_normalize(text)
        text = cls.remove_citations(text)
        text = cls.remove_boilerplate(text)
        if strip_urls:
            text = cls.remove_urls(text)
        text = cls.normalize_whitespace(text)
        return text

    @classmethod
    def clean_plain(cls, raw_text: str) -> str:
        """
        Lightweight version for text that is already HTML-free.
        Skips the BeautifulSoup parse step.
        """
        text = cls.normalize_line_breaks(raw_text)
        text = cls.unicode_normalize(text)
        text = cls.remove_citations(text)
        text = cls.remove_boilerplate(text)
        text = cls.normalize_whitespace(text)
        return text
