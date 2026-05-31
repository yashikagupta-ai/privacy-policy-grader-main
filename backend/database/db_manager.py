"""
database/db_manager.py — Database operations for Privacy Policy Grader.

OUR CUSTOM CODE — NO LLM USED.

Methods
-------
init_db()                    — create tables; seed benchmarks if empty
save_analysis(data)          — upsert an analysis row
get_analysis(url)            — fetch by exact URL
get_analyses_by_domain(d)    — fetch all analyses whose URL contains domain (NEW)
get_recent_analyses(limit)   — fetch N most recent rows
get_benchmarks(industry)     — fetch one industry benchmark
get_industry_averages()      — fetch all benchmarks
compare_to_benchmarks(scores)— position scores vs industry averages
update_benchmarks()          — recompute benchmarks from stored analyses
"""

from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from database.models import Analysis, Benchmark, get_session_factory
from config import Config


class DatabaseManager:
    """
    Thin wrapper around SQLAlchemy sessions.
    All public methods open their own session and commit/rollback as needed.
    """

    _session_factory = None
    _seeding = False

    @classmethod
    def init_db(cls) -> None:
        if cls._seeding:
            return
        cls._session_factory = get_session_factory(Config.DATABASE_URL)
        # Auto-seed if Benchmarks are empty (Issue #1 check)
        try:
            from database.seed_data import seed_all
            with cls._session() as session:
                if session.query(Benchmark).count() == 0:
                    cls._seeding = True
                    print("[db] Database is empty. Seeding defaults...")
                    seed_all()
                    cls._seeding = False
        except ImportError:
            pass # Handle if seed_data.py is missing
        except Exception as e:
            cls._seeding = False
            print(f"[db] Warning during auto-seed: {e}")

    @classmethod
    @contextmanager
    def _session(cls):
        if cls._session_factory is None:
            cls.init_db()
        session = cls._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @classmethod
    def save_analysis(cls, data: Dict[str, Any]) -> None:
        with cls._session() as session:
            existing = session.query(Analysis).filter_by(url=data["url"]).first()
            if existing:
                for key, val in data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, val)
            else:
                row = Analysis(**{k: v for k, v in data.items() if hasattr(Analysis, k)})
                session.add(row)

    @classmethod
    def get_analysis(cls, url: str) -> Optional[Dict[str, Any]]:
        with cls._session() as session:
            row = session.query(Analysis).filter_by(url=url).first()
            return row.to_dict() if row else None

    @classmethod
    def get_analyses_by_domain(cls, domain: str) -> List[Dict[str, Any]]:
        """
        OUR CUSTOM CODE — Fetch all analyses matching a domain.

        Used by GET /api/history/<domain> to build a version changelog.
        Returns rows ordered oldest-first so deltas can be computed forward.

        Parameters
        ----------
        domain : str — e.g. "google.com" or "google" (partial match works)
        """
        with cls._session() as session:
            rows = (
                session.query(Analysis)
                .filter(Analysis.url.contains(domain))
                .order_by(Analysis.created_at.asc())
                .all()
            )
            return [r.to_dict() for r in rows]

    @classmethod
    def get_recent_analyses(cls, limit: int = 10) -> List[Dict[str, Any]]:
        with cls._session() as session:
            rows = (
                session.query(Analysis)
                .order_by(Analysis.created_at.desc())
                .limit(limit)
                .all()
            )
            return [r.to_dict() for r in rows]

    @classmethod
    def count_analyses(cls) -> int:
        with cls._session() as session:
            return session.query(Analysis).count()

    @classmethod
    def get_grade_distribution(cls) -> Dict[str, int]:
        with cls._session() as session:
            rows = session.query(Analysis.grade).all()
            dist = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
            for row in rows:
                if row[0] in dist:
                    dist[row[0]] += 1
            return dist

    @classmethod
    def get_benchmarks(cls, industry: str) -> Optional[Dict[str, Any]]:
        with cls._session() as session:
            row = (
                session.query(Benchmark)
                .filter(Benchmark.industry.ilike(industry))
                .first()
            )
            return row.to_dict() if row else None

    @classmethod
    def get_industry_averages(cls) -> List[Dict[str, Any]]:
        with cls._session() as session:
            rows = session.query(Benchmark).order_by(Benchmark.industry).all()
            return [r.to_dict() for r in rows]

    @classmethod
    def compare_to_benchmarks(cls, scores: Dict[str, float]) -> Dict[str, Any]:
        """
        OUR CUSTOM CODE — Compare dimension scores against all-industry averages.
        Returns above/below/average position and delta per dimension.
        """
        averages = cls.get_industry_averages()
        if not averages:
            return {}

        global_avgs: Dict[str, List[float]] = {}
        for bench in averages:
            for dim, val in (bench.get("avg_scores") or {}).items():
                global_avgs.setdefault(dim, []).append(val)

        comparison = {}
        for dim, score in scores.items():
            avg_list = global_avgs.get(dim, [])
            if avg_list:
                industry_avg = sum(avg_list) / len(avg_list)
                delta = round(score - industry_avg, 2)
                comparison[dim] = {
                    "industry_avg": round(industry_avg, 2),
                    "delta": delta,
                    "position": (
                        "above_average" if delta > 5
                        else "below_average" if delta < -5
                        else "average"
                    ),
                }
        return comparison

    @classmethod
    def update_or_create_benchmark(cls, industry: str, avg_grade: str, avg_scores: Dict[str, float], sample_size: int) -> None:
        with cls._session() as session:
            existing = session.query(Benchmark).filter_by(industry=industry).first()
            if existing:
                existing.avg_grade = avg_grade
                existing.avg_scores = avg_scores
                existing.sample_size = sample_size
            else:
                session.add(Benchmark(
                    industry=industry,
                    avg_grade=avg_grade,
                    avg_scores=avg_scores,
                    sample_size=sample_size,
                ))

    @classmethod
    def update_benchmarks(cls) -> None:
        """OUR CUSTOM CODE — Recompute industry averages from stored analyses."""
        with cls._session() as session:
            all_analyses = session.query(Analysis).all()
            if not all_analyses:
                return

            industry_map = {
                "google": "Technology", "apple": "Technology",
                "microsoft": "Technology", "amazon": "E-Commerce",
                "facebook": "Social Media", "twitter": "Social Media",
                "linkedin": "Social Media", "tiktok": "Social Media",
                "netflix": "Entertainment", "spotify": "Entertainment",
                "reddit": "Social Media", "zoom": "Technology",
            }

            grouped: Dict[str, List] = {}
            for row in all_analyses:
                industry = industry_map.get(row.company_name.lower(), "Other")
                grouped.setdefault(industry, []).append(row)

            for industry, rows in grouped.items():
                all_dims: Dict[str, List[float]] = {}
                for row in rows:
                    for dim, score in (row.dimension_scores or {}).items():
                        all_dims.setdefault(dim, []).append(score)

                avg_scores = {
                    dim: round(sum(vals) / len(vals), 2)
                    for dim, vals in all_dims.items()
                }
                avg_overall = sum(r.overall_score for r in rows) / len(rows)
                avg_grade = Config.grade_letter(avg_overall)

                existing = session.query(Benchmark).filter_by(industry=industry).first()
                if existing:
                    existing.avg_grade = avg_grade
                    existing.avg_scores = avg_scores
                    existing.sample_size = len(rows)
                else:
                    session.add(Benchmark(
                        industry=industry,
                        avg_grade=avg_grade,
                        avg_scores=avg_scores,
                        sample_size=len(rows),
                    ))
