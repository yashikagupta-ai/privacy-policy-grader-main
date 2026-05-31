<div align="center">

#Privacy Policy Grader

### *Know what you're agreeing to — before you click "I Accept"*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Gemini](https://img.shields.io/badge/Google_Gemini-1.5_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![SQLite](https://img.shields.io/badge/SQLite-SQLAlchemy_ORM-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlalchemy.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/Tests-23_Passing-22c55e?style=for-the-badge&logo=pytest)](./tests/)

---

**Privacy Policy Grader** is an AI-powered web application that analyses any company's privacy policy and gives it a transparent, reproducible score from 0–100 — breaking down exactly how well (or how poorly) they handle your data.

Paste a URL. Get a grade. Understand your rights.

---

</div>

## 📸 Screenshots

<div align="center">

| | |
|:---:|:---:|
| ![Homepage — URL Input & Grade Result](./screenshots/screenshot-1.png) | ![Radar Chart & Score Breakdown](./screenshots/screenshot-2.png) |
| *Homepage: paste any privacy policy URL and get an instant grade* | *5-dimension radar chart showing exactly where policies succeed or fail* |
| ![Side-by-Side Policy Comparison](./screenshots/screenshot-3.png) | ![Red Flags & Dark Pattern Detection](./screenshots/screenshot-4.png) |
| *Compare two companies' policies head-to-head* | *AI-detected red flags with source text verification* |

</div>

---

## 📋 Table of Contents

- [The Problem](#-the-problem)
- [What It Does](#-what-it-does)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Grading Methodology](#-grading-methodology)
- [Core Features Deep Dive](#-core-features-deep-dive)
- [Our Code vs. LLM — Contribution Breakdown](#-our-code-vs-llm--contribution-breakdown)
- [API Reference](#-api-reference)
- [Project Structure](#-project-structure)
- [Getting Started Locally](#-getting-started-locally)
- [Deployment](#-deployment)
- [Running Tests](#-running-tests)

---

## 🚨 The Problem

Privacy policies are **deliberately unreadable**. The average privacy policy is:

- **2,500+ words** long — longer than most short stories
- Written at a **14th-grade reading level** (college senior literacy required)
- Dense with legal jargon like *"legitimate interest," "third-party processors,"* and *"pseudonymised data"*
- Full of **dark patterns** — vague language designed to obscure what companies actually do with your data

The result? 91% of people agree to terms they have never read. Companies exploit this. Your data gets shared, sold, and processed in ways you never consciously consented to.

**Privacy Policy Grader fixes this.** It reads the policy for you — scoring it across five dimensions of transparency and user respect, surfacing red flags, and giving you a plain-English verdict in seconds.

---

## ✅ What It Does

**Input:** Any privacy policy URL (e.g. `https://google.com/privacy`)

**Output:**
- A **letter grade (A–F)** and 0–100 score
- **5-dimension radar chart** breaking down exactly where the policy succeeds or fails
- **Red flag detection** — specific problematic clauses highlighted with source quotes
- **Dark pattern analysis** — identifies manipulative language patterns
- **Plain-English summary** — a human-readable verdict paragraph
- **Industry benchmark comparison** — how does this policy rank against 12 companies across 4 industries?
- **Side-by-side comparison** — compare any two policies directly
- **Export to PDF/JSON** — save results for reporting or auditing

---

## 🛠 Tech Stack

<div align="center">

| Layer | Technology | Purpose |
|:------|:-----------|:--------|
| **Backend Framework** | Flask 3.0 + Gunicorn | Web server, API routing, Jinja2 templating |
| **AI / LLM** | Google Gemini 1.5 Flash | Semantic extraction of data types, sharing recipients, user rights |
| **NLP Pipeline** | NLTK, textstat, custom Python | 18+ readability metrics, jargon detection, dark pattern regex |
| **Web Scraping** | BeautifulSoup4 + Selenium | Multi-strategy policy text extraction with JS-rendering fallback |
| **Database** | SQLite + SQLAlchemy ORM | Analysis caching, industry benchmarks, grade distributions |
| **Frontend** | Vanilla JS + HTML5 Canvas | Zero-dependency radar chart, animated grade arc |
| **Deployment** | Render (PaaS) | Production hosting with Gunicorn workers |
| **Testing** | pytest | 23 tests across 5 NLP modules |

</div>

> **Stack note:** The project evolved from an initially planned FastAPI + React stack to Flask + Jinja2. This decision was deliberate — it maximises Python-dominant backend engineering and eliminates frontend build tooling complexity, keeping the architecture clean and production-ready.

---

## 🏗 Architecture

The system follows a clean linear pipeline: raw URL in → structured analysis out. Every stage is a separate, testable module.

```
                        ┌─────────────────────────────────┐
                        │         User Input (URL)         │
                        └──────────────┬──────────────────┘
                                       │
                                       ▼
                        ┌─────────────────────────────────┐
                        │         URL Validator            │  ← path heuristics
                        │       url_validator.py           │    robots.txt scan
                        └──────────────┬──────────────────┘    homepage crawl
                                       │ validated policy URL
                                       ▼
                        ┌─────────────────────────────────┐
                        │         Web Scraper              │  ← BeautifulSoup4
                        │          scraper.py              │    boilerplate removal
                        └──────────────┬──────────────────┘    Selenium fallback
                                       │ clean policy text
                                       ▼
                        ┌─────────────────────────────────┐
                        │         Preprocessor             │  ← 18+ NLP metrics
                        │        preprocessor.py           │    (readability, jargon,
                        └──────┬───────────────┬──────────┘     dark patterns, VADER)
                               │               │
                metrics dict   │               │   raw text
                               ▼               ▼
              ┌────────────────────┐   ┌──────────────────────┐
              │   Grading Engine   │   │     LLM Service       │
              │  grading_engine.py │   │    llm_service.py     │  ← GEMINI API
              │  (5 dimensions,    │   │  (data types, rights, │    called ONCE
              │   9 sub-scorers)   │   │   red flags, summary) │
              └────────┬───────────┘   └──────────┬───────────┘
                       │                           │
                scores │               findings    │
                       │                           ▼
                       │               ┌──────────────────────┐
                       │               │    Claim Verifier     │  ← difflib fuzzy match
                       │               │     verifier.py       │    hallucination guard
                       │               └──────────┬───────────┘
                       │                           │ verified findings
                       └──────────────┬────────────┘
                                      │
                                      ▼
                        ┌─────────────────────────────────┐
                        │          Database                │  ← SQLAlchemy ORM
                        │         db_manager.py            │    caching + benchmarks
                        └──────────────┬──────────────────┘
                                       │ JSON response
                                       ▼
                        ┌─────────────────────────────────┐
                        │          Flask API               │  ← /api/analyze
                        │           routes/                │    /api/compare
                        └──────────────┬──────────────────┘    /api/benchmarks
                                       │
                                       ▼
                        ┌─────────────────────────────────┐
                        │           Frontend               │  ← Canvas radar chart
                        │      static/ + templates/        │    animated grade arc
                        └─────────────────────────────────┘    vanilla JS
```

---

## 📊 Grading Methodology

The overall score is a **weighted average across 5 dimensions**. Each dimension has 3 sub-scorers (each 0–10), averaged to a 0–100 dimension score.

<div align="center">

| Dimension | Weight | What We Measure |
|:----------|:------:|:----------------|
| **Data Collection Transparency** | 25% | Types enumerated, purposes stated, clear categorisation |
| **Sharing Disclosure** | 25% | Recipients named, opt-out availability, per-recipient purposes |
| **User Rights** | 20% | Access, deletion, portability, correction mechanisms |
| **Readability** | 15% | Flesch Reading Ease, section structure, jargon density |
| **Compliance** | 15% | GDPR alignment, CCPA alignment, COPPA consideration |

</div>

### Grade Thresholds

<div align="center">

| Grade | Score | What It Means |
|:-----:|:-----:|:--------------|
| 🟢 **A** | 90–100 | Excellent — transparent, user-friendly, meets modern standards |
| 🔵 **B** | 80–89 | Good — most bases covered with minor gaps |
| 🟡 **C** | 70–79 | Adequate — significant room for improvement |
| 🟠 **D** | 60–69 | Poor — several major transparency failures |
| 🔴 **F** | 0–59 | Very Poor — fails basic privacy standards |

</div>

---

## 🔬 Core Features Deep Dive

### 1. Smart Web Scraper
The scraper doesn't just fetch a URL — it actively finds the privacy policy even when none is explicitly given.

- **Multi-strategy URL discovery:** tries known path patterns (`/privacy`, `/legal/privacy`) → crawls the homepage for policy links → scans `robots.txt`
- **Boilerplate removal:** strips navigation bars, cookie banners, ads, and footers using BeautifulSoup4 tag filtering
- **Selenium fallback:** if a page requires JavaScript rendering (SPAs, lazy-loaded content), headless Chrome steps in
- **Section splitting:** identifies policy headings and splits text into analysable sections

### 2. Custom NLP Pipeline (18+ Metrics, Zero LLM)
All of the following are computed entirely with custom Python — no AI involved:

- **Readability formulas:** Flesch Reading Ease, Flesch-Kincaid Grade Level, SMOG Index, Automated Readability Index, Coleman-Liau — all implemented from scratch with a custom syllable counter
- **Jargon detection:** dictionary of 150+ legal/privacy/technical terms with regex word-boundary matching and per-section density analysis
- **Dark pattern detection:** 15+ categories of manipulative language patterns (vague data purposes, buried opt-outs, forced consent bundling, etc.) using `@dataclass PatternSpec` rules with severity scores
- **Text metrics:** VADER sentiment analysis, passive voice percentage, type-token ratio (vocabulary diversity), clause completeness scoring, paragraph structure analysis

### 3. LLM Integration (Gemini 1.5 Flash)
Gemini is called in **exactly one file** (`llm_service.py`) for things only a language model can do well:

- Identifying *specific* data types collected (e.g. "biometric data," "purchase history")
- Naming sharing recipients (e.g. "advertising partners," "data brokers")
- Extracting user rights mentions and their accessibility
- Generating a plain-English summary verdict

> **Demo Mode:** The app is fully functional without a Gemini API key — it serves realistic mock responses so you can explore all features offline.

### 4. Hallucination Guard — ClaimVerifier
Every AI-generated finding is cross-checked against the original policy text using `difflib.SequenceMatcher` fuzzy matching. Claims that can't be grounded in the source text are flagged as potential hallucinations and their confidence score is penalised. This prevents the LLM from inventing rights or protections that don't exist.

### 5. Industry Benchmarks
The database is seeded with real analysis data for 12 companies across 4 industries (Technology, Social Media, E-Commerce, Healthcare). Every analysis is compared against the relevant industry average, showing users not just how good a policy is — but how it ranks in context.

### 6. Pure Canvas Charts
The radar chart and animated grade arc are drawn entirely with the HTML5 Canvas API — no Chart.js, no D3, no external dependencies. This keeps the frontend lean and eliminates CDN dependencies.

### 7. PDF & JSON Export
Every analysis can be exported as a structured JSON report or a formatted PDF, suitable for privacy audits, academic research, or personal records.

---

## 🤝 Our Code vs. LLM — Contribution Breakdown

This table makes explicit what was engineered by the team versus what the LLM provides at runtime. This distinction is the core value proposition: the LLM handles semantic understanding; everything else is custom-built Python.

<div align="center">

| Component | Our Code | Gemini LLM |
|:----------|:--------:|:----------:|
| Readability formulas (FRE, FKGL, SMOG, ARI, Coleman-Liau) | ✔︎ | 𐄂 |
| Custom syllable counter | ✔︎ | 𐄂 |
| Legal jargon dictionary (150+ terms) + density analysis | ✔︎ | 𐄂 |
| Dark pattern detection (15+ categories, severity scores) | ✔︎ | 𐄂 |
| VADER sentiment analysis | ✔︎ | 𐄂 |
| Passive voice % + type-token ratio | ✔︎ | 𐄂 |
| Multi-strategy web scraper + Selenium fallback | ✔︎ | 𐄂 |
| Policy URL auto-discovery | ✔︎ | 𐄂 |
| 5-dimension weighted grading engine | ✔︎ | 𐄂 |
| ClaimVerifier (difflib fuzzy-match hallucination guard) | ✔︎ | 𐄂 |
| SQLAlchemy ORM + CRUD + benchmarks | ✔︎ | 𐄂 |
| HTML5 Canvas radar chart + animated grade arc | ✔︎ | 𐄂 |
| Identifying specific data types & sharing recipients | 𐄂 | ✔︎ |
| Extracting user rights from raw text | 𐄂 | ✔︎ |
| Generating plain-English verdict summaries | 𐄂 | ✔︎ |

</div>

---

## 📡 API Reference

All endpoints return JSON with the envelope: `{ "success": bool, "data": ..., "error": ... }`

---

### `POST /api/analyze`
Analyse a single privacy policy URL.

**Request:**
```json
{
  "url": "https://example.com/privacy",
  "force_refresh": false
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "url": "https://example.com/privacy",
    "company_name": "Example",
    "grade": "B",
    "overall_score": 84.2,
    "dimension_scores": {
      "data_collection_transparency": 88,
      "sharing_disclosure": 82,
      "user_rights": 90,
      "readability": 72,
      "compliance": 88
    },
    "findings": {
      "data_collected": ["email", "location", "purchase history"],
      "data_shared": ["advertising partners", "analytics providers"],
      "user_rights": { "access": true, "deletion": true, "portability": false },
      "red_flags": ["vague data retention language", "broad third-party sharing"]
    },
    "metrics": {
      "word_count": 3200,
      "flesch_reading_ease": 42.1,
      "jargon_density": 8.4,
      "dark_pattern_score": 28.5
    },
    "verification": {
      "overall_confidence": 0.87,
      "hallucination_count": 1
    },
    "processing_time_seconds": 6.2,
    "cached": false
  }
}
```

**Error codes:**

| Code | Reason |
|:----:|:-------|
| 400 | Missing or invalid `url` field |
| 422 | Policy text could not be scraped |
| 429 | Rate limit exceeded (60 req/min) |
| 500 | Internal server error |

---

### `POST /api/compare`
Compare two privacy policies side by side.

**Request:**
```json
{ "urls": ["https://a.com/privacy", "https://b.com/privacy"] }
```

**Response:** Returns `policy_a`, `policy_b`, `winner`, `score_delta`, `key_differences[]`, and `benchmark_comparison`.

---

### `GET /api/benchmarks`
Returns all industry benchmark data, grade distributions, and recent analyses.

### `GET /api/benchmarks/<industry>`
Returns benchmark data for a specific industry. Supported values: `Technology`, `Social Media`, `E-Commerce`, `Healthcare`.

### `GET /api/health`
Health check. Returns `{ "status": "ok", "demo_mode": bool, "version": "..." }`.

### `GET /api/export/<analysis_id>`
Export a saved analysis as PDF or JSON. Accepts query param `?format=pdf` or `?format=json`.

---

## 📁 Project Structure

```
privacy-policy-grader/
│
├── backend/
│   ├── app.py                      # Flask app factory — CORS, blueprints, rate limiting
│   ├── config.py                   # Config from .env (grading weights, demo mode)
│   ├── requirements.txt
│   ├── .env.example
│   │
│   ├── analyzers/                  # ← OUR CODE: pure NLP, zero LLM
│   │   ├── readability.py          # 5 readability formulas, custom syllable counter
│   │   ├── jargon_detector.py      # 150+ term dictionary, density + per-section analysis
│   │   ├── dark_patterns.py        # 15+ regex pattern categories with severity scores
│   │   └── text_metrics.py         # VADER sentiment, passive voice, vocabulary diversity
│   │
│   ├── services/
│   │   ├── scraper.py              # BeautifulSoup4 + Selenium multi-strategy scraper
│   │   ├── preprocessor.py         # Aggregates all 18+ NLP metrics into a single dict
│   │   ├── llm_service.py          # ← ONLY file that calls Gemini API
│   │   ├── grading_engine.py       # Weighted 5-dimension scoring, grade boundaries
│   │   └── verifier.py             # difflib fuzzy-match hallucination guard
│   │
│   ├── routes/
│   │   ├── analyze.py              # POST /api/analyze — full pipeline orchestration
│   │   ├── compare.py              # POST /api/compare — side-by-side comparison
│   │   ├── benchmarks.py           # GET /api/benchmarks — industry data
│   │   └── export.py               # GET /api/export — PDF + JSON export
│   │
│   ├── database/
│   │   ├── models.py               # SQLAlchemy ORM models (Analysis, Benchmark)
│   │   ├── db_manager.py           # All CRUD operations + grade distribution queries
│   │   └── seed_data.py            # 12 companies × 4 industries benchmark data
│   │
│   └── utils/
│       ├── text_cleaner.py         # HTML → clean text pipeline
│       └── url_validator.py        # URL validation + policy URL auto-discovery
│
├── frontend/
│   ├── templates/
│   │   └── index.html              # Jinja2 single-page application shell
│   └── static/
│       ├── css/
│       │   └── style.css           # Full dark-mode design system
│       └── js/
│           ├── app.js              # Main controller — orchestrates all UI modules
│           ├── radarChart.js       # Pure HTML5 Canvas radar chart (no Chart.js)
│           ├── gradeCard.js        # Animated arc grade display
│           ├── redFlags.js         # Accordion renderer for red flags + dark patterns
│           └── comparison.js       # Side-by-side comparison renderer
│
├── tests/
│   ├── conftest.py
│   ├── test_readability.py         # 8 tests — FRE, FKGL, syllable counter, all formulas
│   ├── test_jargon_detector.py     # 9 tests — dictionary matching, density, per-section
│   ├── test_dark_patterns.py       # 9 tests — 15+ pattern categories, severity
│   ├── test_grading_engine.py      # 9 tests — grade boundaries, dimension scores, edges
│   ├── test_verifier.py            # 9 tests — fuzzy matching, hallucination detection
│   └── test_routes.py              # API route integration tests
│
├── samples/
│   ├── google_privacy.txt          # Sample for offline testing
│   ├── facebook_privacy.txt
│   ├── amazon_privacy.txt
│   ├── simple_privacy.txt          # Model A-grade policy for comparison baseline
│   └── ground_truth.csv            # Ground-truth labels for evaluating NLP accuracy
│
├── prompt_experiments.ipynb        # Prompt engineering iteration log (V1 → V5)
├── render.yaml                     # Render.com deployment config
├── Procfile                        # Gunicorn start command
└── runtime.txt                     # Python version pin
```

---

## 🚀 Getting Started Locally

### Prerequisites

- Python 3.10 or higher
- Google Chrome (for Selenium JS-rendering fallback — optional)
- A Google Gemini API key (optional — the app runs in Demo Mode without one)

### Step 1 — Clone & Install

```bash
git clone https://github.com/your-username/privacy-policy-grader.git
cd privacy-policy-grader/backend
pip install -r requirements.txt
```

### Step 2 — Configure Environment

```bash
cp .env.example .env
```

Open `.env` and set your values:

```env
# Required for full AI features — leave blank for Demo Mode
GEMINI_API_KEY=your_key_here

# Optional overrides
FLASK_DEBUG=True
GEMINI_MODEL=gemini-1.5-flash
RATE_LIMIT_PER_MIN=60
```

> **Demo Mode:** If `GEMINI_API_KEY` is left blank, the app serves realistic mock AI responses. All NLP features (readability, jargon, dark patterns) work fully. A "Demo Mode" banner is shown in the UI.

### Step 3 — Download NLTK Data

```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('vader_lexicon')"
```

### Step 4 — Seed the Database

This populates industry benchmark data for 12 companies across 4 industries:

```bash
python -c "from database.seed_data import seed_all; seed_all()"
```

### Step 5 — Run

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

### Offline / No-Internet Testing

Use the sample files in the `samples/` directory:

```bash
# Paste the content of samples/google_privacy.txt into the text input area
# Or serve the file locally:
python -m http.server 8080 --directory samples/
# Then analyse: http://localhost:8080/google_privacy.txt
```

---

## ☁️ Deployment

The app is deployed on **Render** (free tier) via `render.yaml`.

### Render Deployment Config (`render.yaml`)

```yaml
services:
  - type: web
    name: privacy-policy-grader
    runtime: python
    buildCommand: pip install -r backend/requirements.txt
    startCommand: gunicorn --chdir backend "app:create_app()" --bind 0.0.0.0:$PORT --workers 2 --timeout 120
    envVars:
      - key: GEMINI_API_KEY
        sync: false        # Set manually in Render dashboard
      - key: FLASK_DEBUG
        value: False
      - key: GEMINI_MODEL
        value: gemini-1.5-flash
      - key: PYTHON_VERSION
        value: 3.11.9
```

### Deploy Your Own Instance

1. Fork this repository
2. Connect it to [Render](https://render.com) — select "New Web Service" → point to your fork
3. Render auto-detects `render.yaml` and configures everything
4. Add your `GEMINI_API_KEY` in the Render dashboard under **Environment**
5. Hit **Deploy** — live in ~3 minutes

> **Note on cold starts:** Render's free tier spins down after 15 minutes of inactivity. The first request after a cold start may take 30–60 seconds. Paid plans eliminate this.

---

## 🧪 Running Tests

```bash
cd backend
pytest ../tests/ -v
```

Expected output: **23 tests passing** across 6 test files covering every custom NLP module.

### Test Coverage Summary

<div align="center">

| Test File | Tests | What's Covered |
|:----------|------:|:---------------|
| `test_readability.py` | 8 | FRE, FKGL, SMOG, ARI, Coleman-Liau, syllable counter |
| `test_jargon_detector.py` | 9 | 150+ term dictionary matching, density, per-section analysis |
| `test_dark_patterns.py` | 9 | 15+ pattern categories, severity scores, structural checks |
| `test_grading_engine.py` | 9 | Grade boundaries, dimension scoring, edge cases |
| `test_verifier.py` | 9 | Fuzzy matching thresholds, hallucination detection, confidence scores |
| `test_routes.py` | — | API route integration tests |
| **Total** | **23+** | |

</div>

Run a specific test file:

```bash
pytest ../tests/test_readability.py -v
```

Run with coverage report:

```bash
pip install pytest-cov
pytest ../tests/ --cov=. --cov-report=term-missing -v
```

---

## 🌐 Live Demo

**Try it now:** [https://privacy-policy-grader.onrender.com/](https://privacy-policy-grader.onrender.com/)

Some policies to try:
- `https://policies.google.com/privacy`
- `https://www.facebook.com/privacy/policy/`
- `https://www.apple.com/legal/privacy/`
- `https://duckduckgo.com/privacy`

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](./LICENSE) file for details.

---

<div align="center">

Built with 🔍 for people who deserve to understand what they're agreeing to.

</div>
