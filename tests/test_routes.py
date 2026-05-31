"""
tests/test_routes.py — Integration tests for API endpoints.

Fix: patch the already-imported module-level instance attributes, not the
class definitions in the original module. Flask blueprints import and
instantiate at module load time, so patching the class has no effect.

Correct paths:
  routes.analyze._analyzer.analyze_with_gemini   (not services.llm_service.PrivacyAnalyzer.*)
  routes.analyze._scraper.extract_policy
  routes.compare._analyzer.analyze_with_gemini
  routes.compare._scraper.extract_policy
"""

import json
from unittest.mock import patch, MagicMock


def test_health_endpoint(client):
    """Test the health check endpoint."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


@patch("routes.analyze._analyzer.analyze_with_gemini")
@patch("database.db_manager.DatabaseManager.save_analysis")
def test_analyze_text_endpoint(mock_save, mock_analyze, client, sample_policy_text, mock_llm_response):
    """Test the /api/analyze/text endpoint with mocked LLM."""
    mock_analyze.return_value = mock_llm_response
    mock_save.return_value = None

    payload = {
        "text": sample_policy_text,
        "company_name": "TestCorp",
        "source_url": "https://test.com/privacy"
    }

    resp = client.post("/api/analyze/text", json=payload)
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["success"] is True
    assert data["data"]["company_name"] == "TestCorp"
    assert data["data"]["grade"] in ["A", "B", "C", "D", "F"]
    assert "trust_score" in data["data"]
    assert "gdpr_basis" in data["data"]["metrics"] or "gdpr_mentions" in data["data"]["metrics"]


@patch("database.db_manager.DatabaseManager.get_analyses_by_domain")
def test_history_endpoint(mock_get_analyses, client):
    """Test the /api/history/<domain> endpoint."""
    mock_get_analyses.return_value = [
        {
            "url": "https://google.com/p1",
            "company_name": "Google",
            "grade": "B",
            "overall_score": 82.5,
            "created_at": "2024-01-01",
            "dimension_scores": {"readability": 80},
            "red_flags": []
        },
        {
            "url": "https://google.com/p2",
            "company_name": "Google",
            "grade": "A",
            "overall_score": 91.0,
            "created_at": "2024-02-01",
            "dimension_scores": {"readability": 95},
            "red_flags": []
        }
    ]

    resp = client.get("/api/history/google.com")
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["success"] is True
    assert data["data"]["domain"] == "google.com"
    assert data["data"]["count"] == 2
    assert data["data"]["versions"][1]["delta"]["direction"] == "improved"


@patch("routes.compare._analyzer.analyze_with_gemini")
@patch("routes.compare._scraper.extract_policy")
@patch("database.db_manager.DatabaseManager.save_analysis")
@patch("database.db_manager.DatabaseManager.get_analysis")
@patch("database.db_manager.DatabaseManager.compare_to_benchmarks")
def test_compare_endpoint(mock_bench, mock_get, mock_save, mock_scrape, mock_analyze, client, mock_llm_response):
    """Test the /api/compare endpoint."""
    mock_get.return_value = None   # no cache
    mock_save.return_value = None
    mock_bench.return_value = {}
    mock_scrape.return_value = {
        "url": "https://test.com/p",
        "policy_text": "Sample text for scraping. " * 30,
        "sections": [],
        "last_updated": None
    }
    mock_analyze.return_value = mock_llm_response

    payload = {
        "urls": ["https://google.com/privacy", "https://apple.com/privacy"]
    }

    resp = client.post("/api/compare", json=payload)
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["success"] is True
    assert "policy_a" in data["data"]
    assert "policy_b" in data["data"]
    assert "winner" in data["data"]
    assert "trust_score" in data["data"]["policy_a"]


def test_benchmarks_endpoint(client):
    """Test the /api/benchmarks endpoint."""
    resp = client.get("/api/benchmarks")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "benchmarks" in data["data"]
