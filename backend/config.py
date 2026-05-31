"""
config.py — Central configuration for Privacy Policy Grader.

All tuneable values live here.  Settings are loaded from environment
variables (via .env) so nothing sensitive is hard-coded.

Architecture note
-----------------
This module is imported by every other module that needs configuration.
Keep imports minimal here (only stdlib + python-dotenv) to avoid circular
import problems during startup.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------
# Resolve the project root and load .env
# ---------------------------------------------------------------
# __file__  → backend/config.py
# parent    → backend/
# parent²   → project root (privacy-policy-grader/)
BASE_DIR: Path = Path(__file__).resolve().parent.parent
ENV_PATH: Path = BASE_DIR / ".env"

if ENV_PATH.is_file():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    # Try sibling .env in backend/ directory
    load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")


class Config:
    """
    Centralised configuration object.

    Usage
    -----
    from config import Config
    key = Config.GEMINI_API_KEY
    """

    # ----------------------------------------------------------
    # Flask core settings
    # ----------------------------------------------------------
    DEBUG: bool = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    TESTING: bool = os.getenv("FLASK_TESTING", "False").lower() in ("true", "1", "yes")

    # ----------------------------------------------------------
    # Google Gemini API
    # ----------------------------------------------------------
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY") or None

    # If no API key is set → run in Demo Mode (mock LLM responses)
    DEMO_MODE: bool = not bool(GEMINI_API_KEY)

    # ----------------------------------------------------------
    # Database
    # ----------------------------------------------------------
    _db_path: Path = Path(__file__).resolve().parent / "database" / "privacy_grader.db"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{_db_path.as_posix()}"
    )

    # ----------------------------------------------------------
    # Rate limiting  (simple in-memory sliding window)
    # ----------------------------------------------------------
    RATE_LIMIT_PER_MIN: int = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))

    # ----------------------------------------------------------
    # Web-scraping
    # ----------------------------------------------------------
    SCRAPE_TIMEOUT: int = int(os.getenv("SCRAPE_TIMEOUT", "15"))  # seconds

    # Rotate through these user-agents to avoid 403s
    USER_AGENT_POOL: list[str] = [
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.0 Safari/605.1.15"
        ),
        (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
    ]

    # ----------------------------------------------------------
    # Gemini model parameters
    # ----------------------------------------------------------
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    GEMINI_MAX_TOKENS: int = int(os.getenv("GEMINI_MAX_TOKENS", "8192"))
    GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.2"))

    # Maximum characters of policy text sent to LLM
    # (to stay within token limits; truncate if needed)
    LLM_MAX_CHARS: int = 30_000

    # ----------------------------------------------------------
    # Application identity
    # ----------------------------------------------------------
    APP_TITLE: str = "Privacy Policy Grader"
    VERSION: str = "1.0.0"

    # ----------------------------------------------------------
    # Grading engine weights (must sum to 1.0)
    # ----------------------------------------------------------
    GRADING_WEIGHTS: dict[str, float] = {
        "data_collection_transparency": 0.25,
        "sharing_disclosure": 0.25,
        "user_rights": 0.20,
        "readability": 0.15,
        "compliance": 0.15,
    }

    # Grade letter thresholds (inclusive lower bound)
    GRADE_THRESHOLDS: dict[str, int] = {
        "A": 90,
        "B": 80,
        "C": 70,
        "D": 60,
        "F": 0,
    }

    @classmethod
    def grade_letter(cls, score: float) -> str:
        """Convert a 0-100 numeric score to an A-F letter grade."""
        for letter, threshold in cls.GRADE_THRESHOLDS.items():
            if score >= threshold:
                return letter
        return "F"
