"""
tests/conftest.py — Pytest configuration and fixtures.

Fix: patch DatabaseManager.init_db INSIDE the app fixture, before create_app()
is called — not as a separate session-scoped autouse fixture that fires too late.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure backend/ is in python path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))


@pytest.fixture
def app():
    """Create a Flask app instance for testing with DB init mocked."""
    # Patch BEFORE create_app() is called so init_db() inside the app context
    # (backend/app.py line 187) never touches a real file.
    with patch("database.db_manager.DatabaseManager.init_db"):
        from app import create_app
        application = create_app()
        application.config.update({
            "TESTING": True,
            "DATABASE_URL": "sqlite:///:memory:",
        })
        yield application


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def sample_policy_text():
    return """
    This is a sample privacy policy. We collect your email address and name.
    We use your data to provide our services and for marketing purposes.
    You have the right to access, delete, and correct your data.
    By using our site, you consent to our practices.
    We share data with third parties for analytics.
    We follow GDPR and CCPA guidelines.
    """


@pytest.fixture
def mock_llm_response():
    return {
        "data_collected": [
            {"type": "Email", "purpose": "Communication", "sensitivity": "medium"}
        ],
        "data_shared": [
            {"recipient": "Analytics Corp", "data_type": "Usage data", "opt_out_available": True}
        ],
        "user_rights": {
            "access": "Email privacy@example.com",
            "deletion": "Use settings",
            "portability": None,
            "correction": "Use settings"
        },
        "red_flags": [
            {"issue": "Vague purpose", "severity": "medium", "quote": "improve services", "explanation": "Too broad"}
        ],
        "compliance_indicators": ["GDPR mentioned"],
        "summary": "This is a mock summary."
    }
