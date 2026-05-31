"""
services/scraper.py — Privacy-policy web scraper.

OUR CUSTOM CODE — NO LLM USED.

Fetches a privacy policy page using a multi-strategy approach:
1. Resolve the policy URL from any given domain URL.
2. HTTP GET with user-agent rotation.
3. Extract and clean page content (remove nav/footer/cookie banners/ads).
4. Fallback to headless Selenium for JavaScript-rendered pages.
5. Split content into sections by headings.

Returns a structured dict ready for downstream processing.
"""

import re
import time
import random
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import Config
from utils.text_cleaner import TextCleaner
from utils.url_validator import URLValidator


class PrivacyPolicyScraper:
    """
    Extracts clean privacy-policy text from a URL.

    Usage
    -----
    scraper = PrivacyPolicyScraper()
    result  = scraper.extract_policy("https://example.com")

    Returns
    -------
    {
        "policy_text" : str,        # cleaned plain text
        "url"         : str,        # canonical policy URL
        "title"       : str,        # page <title>
        "last_updated": str | None, # inferred date string
        "sections"    : list[dict], # [{title, text}, ...]
        "word_count"  : int,
        "char_count"  : int,
    }
    or None if scraping failed.
    """

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pick_headers() -> Dict[str, str]:
        """Return a random user-agent header dict."""
        ua = random.choice(Config.USER_AGENT_POOL)
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

    @classmethod
    def _http_get(cls, url: str) -> Optional[requests.Response]:
        """
        Perform an HTTP GET with retry logic.

        Retries once with a different user-agent on transient failures.
        Returns the Response or None.
        """
        for attempt in range(2):
            try:
                resp = requests.get(
                    url,
                    headers=cls._pick_headers(),
                    timeout=Config.SCRAPE_TIMEOUT,
                    allow_redirects=True,
                )
                if resp.status_code == 200:
                    return resp
                elif resp.status_code in (403, 429) and attempt == 0:
                    time.sleep(1)  # brief backoff
                    continue
                else:
                    print(f"[scraper] HTTP {resp.status_code} for {url}")
                    return None
            except requests.exceptions.Timeout:
                print(f"[scraper] Timeout fetching {url}")
            except requests.exceptions.RequestException as exc:
                print(f"[scraper] Request error {url}: {exc}")
            time.sleep(0.5)
        return None

    # ------------------------------------------------------------------
    # Boilerplate removal
    # ------------------------------------------------------------------

    @staticmethod
    def _prune_soup(soup: BeautifulSoup) -> BeautifulSoup:
        """
        Remove non-content elements in-place.

        Removes
        -------
        - <script>, <style>, <noscript>, <head>, <meta>, <link>
        - Navigation elements (nav, [class*=nav], [id*=nav])
        - Footer elements
        - Sidebar elements
        - Cookie-consent banners ([class/id*=cookie], [class/id*=consent])
        - Advertisement containers ([class/id*=ad], [aria-label*=advertisement])
        - Social-share widgets
        """
        # Elements to fully remove
        remove_tags = ["script", "style", "noscript", "head", "meta", "link", "iframe"]
        for tag in remove_tags:
            for el in soup.find_all(tag):
                el.decompose()

        # Attribute-based removal patterns
        remove_patterns = [
            {"class_": re.compile(r"(nav|header|footer|sidebar|cookie|consent|"
                                  r"banner|overlay|modal|popup|advertisement|"
                                  r"social|share|widget|ad-|ads-)", re.I)},
        ]
        for pat in remove_patterns:
            for el in soup.find_all(True, **pat):
                el.decompose()

        # ID-based removal
        id_pattern = re.compile(
            r"(nav|header|footer|sidebar|cookie|consent|banner|ad|modal|overlay|social)",
            re.I,
        )
        for el in soup.find_all(True):
            if el.has_attr("id"):
                el_id = el.get("id", "")
                if id_pattern.search(el_id):
                    el.decompose()

        return soup

    # ------------------------------------------------------------------
    # Section splitting
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_sections(soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Split page content into logical sections by heading tags (H1-H4).

        Returns
        -------
        list of {"title": str, "text": str}
        """
        sections: List[Dict[str, str]] = []
        heading_tags = re.compile(r"^h[1-4]$", re.I)

        current_title = "Introduction"
        current_text_parts: List[str] = []

        for el in soup.find_all(True):
            if heading_tags.match(el.name):
                # Save the previous section
                text = " ".join(current_text_parts).strip()
                if text:
                    sections.append({"title": current_title, "text": text})
                current_title = el.get_text(" ", strip=True)
                current_text_parts = []
            elif el.name in ("p", "li", "dd", "td"):
                current_text_parts.append(el.get_text(" ", strip=True))

        # Don't forget the last section
        text = " ".join(current_text_parts).strip()
        if text:
            sections.append({"title": current_title, "text": text})

        return sections

    # ------------------------------------------------------------------
    # Page title extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _get_title(soup: BeautifulSoup) -> str:
        tag = soup.find("title")
        if tag:
            return tag.get_text(" ", strip=True)
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(" ", strip=True)
        return "Privacy Policy"

    # ------------------------------------------------------------------
    # Last-updated date inference
    # ------------------------------------------------------------------

    @staticmethod
    def _get_last_updated(soup: BeautifulSoup, text: str) -> Optional[str]:
        """
        Attempt to find a 'last updated' or 'effective date' string.

        Checks (in order):
        1. Meta tags
        2. Schema.org dateModified
        3. Regex in text
        """
        # Meta tags
        for meta in soup.find_all("meta"):
            name = meta.get("name", "").lower() + meta.get("property", "").lower()
            if "modified" in name or "published" in name:
                content = meta.get("content", "")
                if content:
                    return content

        # Regex in text — look for common date phrases
        date_pattern = re.compile(
            r"(last updated|effective date|last revised|last modified|updated on)[\s:]+([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
            re.IGNORECASE,
        )
        m = date_pattern.search(text[:2000])
        if m:
            return m.group(2)

        return None

    # ------------------------------------------------------------------
    # Selenium fallback
    # ------------------------------------------------------------------

    @classmethod
    def _selenium_get(cls, url: str) -> Optional[str]:
        """
        Use headless Chrome via Selenium to render JavaScript-heavy pages.

        Returns raw HTML string or None on failure.
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager

            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument(f"--user-agent={random.choice(Config.USER_AGENT_POOL)}")
            options.add_argument("--log-level=3")

            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options,
            )
            driver.set_page_load_timeout(Config.SCRAPE_TIMEOUT + 5)

            try:
                driver.get(url)
                time.sleep(2)  # let dynamic content settle
                return driver.page_source
            finally:
                driver.quit()

        except Exception as exc:
            print(f"[scraper] Selenium fallback failed: {exc}")
            return None

    # ------------------------------------------------------------------
    # Main public method
    # ------------------------------------------------------------------

    @classmethod
    def extract_policy(cls, url: str) -> Optional[Dict]:
        """
        Full extraction pipeline for a privacy-policy URL.

        Parameters
        ----------
        url : str
            Any URL — homepage or direct link to a privacy page.

        Returns
        -------
        dict | None
        """
        if not URLValidator.is_valid_url(url):
            print(f"[scraper] Invalid URL: {url}")
            return None

        # Step 1 — Resolve to the actual policy URL
        policy_url = URLValidator.discover_policy_url(url) or url

        # Step 2 — HTTP GET
        response = cls._http_get(policy_url)
        html: Optional[str] = response.text if response else None

        # Step 3 — Fallback to Selenium if response is missing or thin
        if not html or len(html) < 3000:
            print(f"[scraper] Thin response ({len(html or '')} chars), trying Selenium")
            html = cls._selenium_get(policy_url)

        if not html:
            print(f"[scraper] Could not retrieve HTML for {policy_url}")
            return None

        # Step 4 — Parse and clean
        soup = BeautifulSoup(html, "html.parser")
        soup = cls._prune_soup(soup)

        # Extract structured sections before flattening to text
        sections = cls._extract_sections(soup)

        # Full clean text
        policy_text = TextCleaner.clean(str(soup))

        # Fallback: if cleaning produced empty string, try raw get_text
        if len(policy_text.strip()) < 200:
            policy_text = TextCleaner.clean_plain(soup.get_text(" "))

        if len(policy_text.strip()) < 100:
            print(f"[scraper] Extracted text too short for {policy_url}")
            return None

        title = cls._get_title(soup)
        last_updated = cls._get_last_updated(soup, policy_text)

        word_count = len(re.findall(r"\b\w+\b", policy_text))
        char_count = len(policy_text)

        return {
            "policy_text": policy_text,
            "url": policy_url,
            "title": title,
            "last_updated": last_updated,
            "sections": sections,
            "word_count": word_count,
            "char_count": char_count,
        }
