"""
app.py — Flask application factory for Privacy Policy Grader.

Features
--------
- CORS enabled for all origins (tighten in production)
- Blueprint registration: /api/analyze, /api/compare, /api/benchmarks
- Centralised JSON error handlers (400, 404, 429, 500)
- Static file serving from frontend/static/
- Jinja2 templating from frontend/templates/
- Request-logging after_request hook
- In-memory sliding-window rate limiter (per IP)
- Demo mode banner injected into templates when GEMINI_API_KEY is absent

Architecture Note
-----------------
We use the application-factory pattern (create_app) so that the app can
be imported in tests without immediately starting the server.
"""

import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict

from flask import Flask, g, jsonify, render_template, request, send_from_directory
from flask_cors import CORS

# Local imports — config must be importable before the app is created
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))  # ensure backend/ is on path

from config import Config


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> Flask:
    """
    Create and configure the Flask application.

    Returns
    -------
    Flask
        A fully configured Flask application instance.
    """
    app = Flask(
        __name__,
        # Serve static files from frontend/static/
        static_folder=str(Path(__file__).resolve().parent.parent / "frontend" / "static"),
        static_url_path="/static",
        # Jinja2 templates from frontend/templates/
        template_folder=str(Path(__file__).resolve().parent.parent / "frontend" / "templates"),
    )

    # -----------------------------------------------------------------------
    # CORS — allow all origins during development
    # -----------------------------------------------------------------------
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # -----------------------------------------------------------------------
    # Register API blueprints
    # -----------------------------------------------------------------------
    from routes.analyze import analyze_bp
    from routes.compare import compare_bp
    from routes.benchmarks import benchmarks_bp
    from routes.export import export_bp

    app.register_blueprint(analyze_bp, url_prefix="/api")
    app.register_blueprint(compare_bp, url_prefix="/api")
    app.register_blueprint(benchmarks_bp, url_prefix="/api")
    app.register_blueprint(export_bp, url_prefix="/api")

    # -----------------------------------------------------------------------
    # In-memory rate-limit store  { ip: [timestamp, ...] }
    # -----------------------------------------------------------------------
    _rate_store: Dict[str, list] = defaultdict(list)

    # -----------------------------------------------------------------------
    # Middleware: timing + rate limiting
    # -----------------------------------------------------------------------
    @app.before_request
    def _before():
        g.start_time = time.monotonic()

        # Skip rate-limiting for static assets
        if request.path.startswith("/static"):
            return

        ip = request.remote_addr or "unknown"
        now = time.monotonic()

        # Sliding window: keep only timestamps within the last 60 seconds
        window = [t for t in _rate_store[ip] if now - t < 60]
        window.append(now)
        _rate_store[ip] = window

        if len(window) > Config.RATE_LIMIT_PER_MIN:
            return _json_error(429, "Rate limit exceeded. Please wait before retrying.")

    @app.after_request
    def _after(response):
        """Attach processing-time header for debugging."""
        if hasattr(g, "start_time"):
            elapsed = time.monotonic() - g.start_time
            response.headers["X-Process-Time-Ms"] = f"{elapsed * 1000:.1f}"
        return response

    # -----------------------------------------------------------------------
    # Centralised JSON error handlers
    # -----------------------------------------------------------------------
    def _json_error(code: int, message: str):
        """Return a consistent JSON error envelope."""
        resp = jsonify({"success": False, "error": {"code": code, "message": message}})
        resp.status_code = code
        return resp

    @app.errorhandler(400)
    def bad_request(e):
        return _json_error(400, getattr(e, "description", "Bad request"))

    @app.errorhandler(404)
    def not_found(e):
        return _json_error(404, "Resource not found")

    @app.errorhandler(405)
    def method_not_allowed(e):
        return _json_error(405, "Method not allowed")

    @app.errorhandler(429)
    def too_many_requests(e):
        return _json_error(429, getattr(e, "description", "Rate limit exceeded"))

    @app.errorhandler(500)
    def internal_error(e):
        return _json_error(500, "Internal server error")

    @app.errorhandler(Exception)
    def handle_exception(e):
        """Catch-all for unhandled exceptions."""
        import traceback
        print(f"[app] Unhandled exception: {e}")
        traceback.print_exc()
        
        # If it's a Flask error (like a 404), Flask's own handlers will take over
        # otherwise, return a 500
        message = str(e) if Config.DEBUG else "An unexpected error occurred. Please try again."
        return _json_error(500, message)

    # -----------------------------------------------------------------------
    # Frontend routes
    # -----------------------------------------------------------------------
    @app.route("/")
    def index():
        """Render the main single-page application."""
        return render_template(
            "index.html",
            app_title=Config.APP_TITLE,
            version=Config.VERSION,
            demo_mode=Config.DEMO_MODE,
        )

    @app.route("/static/<path:filename>")
    def serve_static(filename: str):
        """Serve static assets explicitly (fallback)."""
        return send_from_directory(app.static_folder, filename)

    # -----------------------------------------------------------------------
    # Health check (useful for deployment probes)
    # -----------------------------------------------------------------------
    @app.route("/api/health")
    def health():
        return jsonify({
            "status": "ok",
            "version": Config.VERSION,
            "demo_mode": Config.DEMO_MODE,
        })

    # -----------------------------------------------------------------------
    # Initialise the database (create tables if they don't exist)
    # -----------------------------------------------------------------------
    with app.app_context():
        try:
            from database.db_manager import DatabaseManager
            DatabaseManager.init_db()
        except Exception as exc:
            print(f"[app] Database initialisation warning: {exc}")

    return app


# ---------------------------------------------------------------------------
# Entry point for direct execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    application = create_app()
    application.run(
        host="0.0.0.0",
        port=5000,
        debug=Config.DEBUG,
        use_reloader=False,  # avoid double-loading with debug=True
    )
