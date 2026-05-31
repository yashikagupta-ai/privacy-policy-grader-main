"""
utils/url_validator.py — URL validation and privacy-policy page discovery.

OUR CUSTOM CODE — NO LLM USED.

Provides heuristics to:
  1. Validate URL syntax.
  2. Detect whether a URL already points to a privacy policy page.
  3. Discover the privacy-policy URL for a given homepage.
"""

import re
import urllib.parse
from typing import Optional

import requests
from bs4 import BeautifulSoup


class URLValidator:
    """
    Validates URLs and heuristically locates privacy-policy pages.

    Strategy (in order)
    -------------------
    1. Validate URL syntax.
    2. If the URL itself looks like a privacy page → return it.
    3. Try appending common privacy-policy path suffixes.
    4. Crawl homepage links for anchor text containing "privacy".
    5. Parse robots.txt for paths containing "privacy".
    """

    # Common path segments that indicate a privacy-policy page
    PRIVACY_PATH_PATTERNS: list[str] = [
        "/privacy",
        "/privacy-policy",
        "/privacy_policy",
        "/privacypolicy",
        "/legal/privacy",
        "/legal/privacy-policy",
        "/about/privacy",
        "/policies/privacy",
        "/policy/privacy",
        "/data-protection",
        "/privacy-notice",
        "/privacycenter",
        "/privacy-center",
        "/dataprivacy",
        "/data_privacy",
        "/gdpr",
        "/info/privacy",
    ]

    # Keywords that suggest a hyperlink leads to a privacy page
    PRIVACY_LINK_KEYWORDS: list[str] = [
        "privacy policy",
        "privacy notice",
        "data protection",
        "privacy statement",
        "privacy center",
        "your privacy",
        "privacy & cookies",
        "privacy and cookies",
    ]

    # Compiled regex for URL syntax validation
    _URL_RE = re.compile(
        r"^(?:https?://)"          # scheme — must be http or https
        r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+"  # domain parts
        r"(?:[A-Z]{2,63})"         # TLD
        r"(?::\d+)?"               # optional port
        r"(?:/[^\s]*)?"            # optional path
        r"$",
        re.IGNORECASE,
    )

    # ------------------------------------------------------------------
    # 1. Syntax validation
    # ------------------------------------------------------------------

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        """
        Return True if *url* is a syntactically valid HTTP(S) URL.

        We intentionally do NOT make a network request here — pure validation.
        """
        if not url or not isinstance(url, str):
            return False
        url = url.strip()
        return bool(cls._URL_RE.match(url))

    # ------------------------------------------------------------------
    # 2. Already a privacy page?
    # ------------------------------------------------------------------

    @classmethod
    def looks_like_privacy_url(cls, url: str) -> bool:
        """
        Return True if the URL path itself contains a privacy-page segment.

        Example
        -------
        >>> URLValidator.looks_like_privacy_url("https://example.com/privacy")
        True
        """
        parsed = urllib.parse.urlparse(url.lower())
        path = parsed.path
        for segment in cls.PRIVACY_PATH_PATTERNS:
            if path.startswith(segment):
                return True
        return False

    # ------------------------------------------------------------------
    # 3. Domain extraction
    # ------------------------------------------------------------------

    @staticmethod
    def extract_domain(url: str) -> str:
        """Return the netloc (e.g. 'www.example.com') from a URL."""
        return urllib.parse.urlparse(url).netloc.lower()

    @staticmethod
    def root_url(url: str) -> str:
        """Return the scheme + netloc (e.g. 'https://www.example.com')."""
        parsed = urllib.parse.urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    # ------------------------------------------------------------------
    # 4. robots.txt scanner
    # ------------------------------------------------------------------

    @classmethod
    def _scan_robots_txt(cls, root: str, timeout: int = 5) -> Optional[str]:
        """
        Fetch robots.txt and look for privacy-related Allow/Disallow entries.

        Returns the first matching candidate URL or None.
        """
        robots_url = root.rstrip("/") + "/robots.txt"
        try:
            resp = requests.get(robots_url, timeout=timeout, allow_redirects=True)
            if resp.status_code != 200:
                return None
            for line in resp.text.splitlines():
                line_lower = line.lower()
                if line_lower.startswith(("allow:", "disallow:")):
                    path = line.split(":", 1)[1].strip()
                    if "privacy" in path.lower() and path.startswith("/"):
                        candidate = root.rstrip("/") + path
                        try:
                            head = requests.head(
                                candidate, timeout=timeout, allow_redirects=True
                            )
                            if head.status_code == 200:
                                return head.url
                        except Exception:
                            continue
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # 5. Homepage link crawler
    # ------------------------------------------------------------------

    @classmethod
    def _scan_homepage_links(cls, base_url: str, timeout: int = 8) -> Optional[str]:
        """
        Fetch the homepage and scan all <a href> elements for links
        that match known privacy-page anchor text or URL patterns.

        Returns the first plausible candidate URL or None.
        """
        try:
            resp = requests.get(
                base_url,
                timeout=timeout,
                allow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
                    )
                },
            )
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            root = cls.root_url(base_url)

            for anchor in soup.find_all("a", href=True):
                href: str = anchor["href"].strip()
                text: str = anchor.get_text(strip=True).lower()

                # Check anchor text
                text_match = any(kw in text for kw in cls.PRIVACY_LINK_KEYWORDS)
                # Check href path
                href_match = any(seg in href.lower() for seg in cls.PRIVACY_PATH_PATTERNS)

                if text_match or href_match:
                    full_url = urllib.parse.urljoin(root, href)
                    if cls.is_valid_url(full_url):
                        try:
                            head = requests.head(
                                full_url, timeout=5, allow_redirects=True
                            )
                            if head.status_code == 200:
                                return head.url
                        except Exception:
                            continue
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Main API: discover_policy_url
    # ------------------------------------------------------------------

    @classmethod
    def discover_policy_url(cls, url: str, timeout: int = 8) -> Optional[str]:
        """
        Given any URL (homepage or partial), attempt to discover the
        canonical privacy-policy URL.

        Returns
        -------
        str | None
            The discovered privacy-policy URL, or None if not found.
        """
        if not cls.is_valid_url(url):
            return None

        # Already looks like a privacy page → return as-is after a HEAD check
        if cls.looks_like_privacy_url(url):
            try:
                resp = requests.head(url, timeout=timeout, allow_redirects=True)
                if resp.status_code == 200:
                    return resp.url
            except Exception:
                pass

        root = cls.root_url(url)

        # Strategy A: try common static paths
        for path in cls.PRIVACY_PATH_PATTERNS:
            candidate = root.rstrip("/") + path
            try:
                resp = requests.head(
                    candidate, timeout=timeout, allow_redirects=True
                )
                if resp.status_code == 200:
                    return resp.url
            except Exception:
                continue

        # Strategy B: crawl homepage links
        homepage_result = cls._scan_homepage_links(url, timeout=timeout)
        if homepage_result:
            return homepage_result

        # Strategy C: robots.txt
        robots_result = cls._scan_robots_txt(root, timeout=5)
        if robots_result:
            return robots_result

        # Could not discover — return original URL as best guess
        return url

    # ------------------------------------------------------------------
    # Utility: check URL accessibility
    # ------------------------------------------------------------------

    @staticmethod
    def is_accessible(url: str, timeout: int = 8) -> bool:
        """
        Return True if a HEAD request to the URL returns HTTP 200.
        """
        try:
            resp = requests.head(url, timeout=timeout, allow_redirects=True)
            return resp.status_code == 200
        except Exception:
            return False
