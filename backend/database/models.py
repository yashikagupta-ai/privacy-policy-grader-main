"""
database/models.py — SQLAlchemy ORM models for Privacy Policy Grader.

Tables
------
- analyses   : one row per analysed privacy policy
- benchmarks : industry-level aggregate statistics

Design decisions
----------------
- JSON columns are used for complex nested data (dimension_scores, findings, etc.)
  SQLite supports JSON natively from version 3.38+; older versions fall back to TEXT.
- All timestamps are UTC (naive datetime objects).
- Indexes are defined for common query patterns.
"""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Table: analyses
# ---------------------------------------------------------------------------

class Analysis(Base):
    """
    Stores the result of analysing a single privacy policy.

    Columns
    -------
    id               : auto-increment primary key
    url              : canonical URL of the policy page (unique index)
    company_name     : inferred or user-provided company name
    policy_text      : full cleaned text of the policy
    grade            : overall letter grade (A / B / C / D / F)
    overall_score    : numeric 0-100 aggregate score
    dimension_scores : JSON dict of per-dimension scores
                       {data_collection_transparency, sharing_disclosure,
                        user_rights, readability, compliance}
    findings         : JSON — structured LLM output
    metrics          : JSON — preprocessor metrics dict
    red_flags        : JSON — verifier output (list of {issue, severity, ...})
    dark_pattern_score : numeric 0-100 dark-pattern score
    trust_score      : numeric 0-100 composite trust score
    created_at       : UTC timestamp of first analysis
    updated_at       : UTC timestamp of last update
    """

    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(2048), nullable=False, unique=True)
    company_name = Column(String(255), nullable=False, default="Unknown")
    policy_text = Column(Text, nullable=False)
    grade = Column(String(1), nullable=False)          # A, B, C, D, F
    overall_score = Column(Float, nullable=False, default=0.0)
    dimension_scores = Column(JSON, nullable=False, default=dict)
    findings = Column(JSON, nullable=False, default=dict)
    metrics = Column(JSON, nullable=False, default=dict)
    red_flags = Column(JSON, nullable=False, default=list)
    dark_pattern_score = Column(Float, nullable=False, default=0.0)
    trust_score = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary (JSON-safe)."""
        return {
            "id": self.id,
            "url": self.url,
            "company_name": self.company_name,
            "grade": self.grade,
            "overall_score": self.overall_score,
            "dimension_scores": self.dimension_scores,
            "findings": self.findings,
            "metrics": self.metrics,
            "red_flags": self.red_flags,
            "dark_pattern_score": self.dark_pattern_score,
            "trust_score": self.trust_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Analysis url={self.url!r} grade={self.grade!r}>"


# ---------------------------------------------------------------------------
# Table: benchmarks
# ---------------------------------------------------------------------------

class Benchmark(Base):
    """
    Stores aggregated benchmark statistics per industry.

    Columns
    -------
    id          : auto-increment primary key
    industry    : industry label (unique, e.g. "Technology", "E-Commerce")
    avg_grade   : modal or average letter grade for the industry
    avg_scores  : JSON dict of average dimension scores
    sample_size : number of policies contributing to the average
    last_updated: timestamp of last recalculation
    """

    __tablename__ = "benchmarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    industry = Column(String(100), nullable=False, unique=True)
    avg_grade = Column(String(1), nullable=False)
    avg_scores = Column(JSON, nullable=False, default=dict)
    sample_size = Column(Integer, nullable=False, default=0)
    last_updated = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "industry": self.industry,
            "avg_grade": self.avg_grade,
            "avg_scores": self.avg_scores,
            "sample_size": self.sample_size,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }

    def __repr__(self) -> str:
        return f"<Benchmark industry={self.industry!r} avg_grade={self.avg_grade!r}>"


# ---------------------------------------------------------------------------
# Composite indexes
# ---------------------------------------------------------------------------

Index("idx_analysis_company", Analysis.company_name)
Index("idx_analysis_grade", Analysis.grade)
Index("idx_benchmark_industry", Benchmark.industry)


# ---------------------------------------------------------------------------
# Engine / Session helpers (used by DatabaseManager)
# ---------------------------------------------------------------------------

def get_engine(database_url: str):
    """Create a SQLAlchemy engine for *database_url*."""
    connect_args = {}
    if database_url.startswith("sqlite"):
        # Allow SQLite to be used from multiple threads (Flask dev server)
        connect_args["check_same_thread"] = False
    return create_engine(database_url, echo=False, future=True,
                         connect_args=connect_args)


def get_session_factory(database_url: str):
    """
    Create all tables and return a sessionmaker bound to *database_url*.

    Called once during app startup.
    """
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
