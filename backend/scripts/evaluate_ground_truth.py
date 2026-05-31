"""
backend/scripts/evaluate_ground_truth.py

Runs the grading pipeline on sample text files in samples/ and compares
results against the manually-annotated ground_truth.csv.

Usage:
    cd privacy-policy-grader-v5
    python backend/scripts/evaluate_ground_truth.py

Outputs:
    - Per-policy comparison table
    - Overall grade agreement rate (exact)
    - Score MAE (Mean Absolute Error)
    - Summary pass/fail

This is standard ML evaluation thinking applied to GenAI output validation.
"""

import sys
import csv
import json
from pathlib import Path

# Ensure backend/ on path
root = Path(__file__).resolve().parent.parent.parent
backend = root / "backend"
sys.path.insert(0, str(backend))

from services.preprocessor import PolicyPreprocessor
from services.llm_service import PrivacyAnalyzer
from services.grading_engine import GradingEngine
from services.verifier import ClaimVerifier

GROUND_TRUTH_CSV = root / "samples" / "ground_truth.csv"
SAMPLES_DIR = root / "samples"

_analyzer = PrivacyAnalyzer()
_grader   = GradingEngine()
_verifier = ClaimVerifier()


def grade_text(text: str) -> dict:
    """Run the full deterministic + LLM pipeline on raw text."""
    metrics = PolicyPreprocessor.process(text, sections=[], last_updated=None)
    llm     = _analyzer.analyze_with_gemini(text, metrics)
    grading = _grader.calculate_grade(llm, metrics)
    return {"grade": grading["grade"], "score": round(grading["overall_score"], 1)}


def load_sample_text(policy_name: str) -> str | None:
    """Try to load a matching .txt file from samples/."""
    slug = policy_name.lower().replace(" ", "_").replace("/", "_")
    for suffix in [slug, slug.split("_")[0]]:
        candidate = SAMPLES_DIR / f"{suffix}_privacy.txt"
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    return None


def main():
    if not GROUND_TRUTH_CSV.exists():
        print(f"[error] {GROUND_TRUTH_CSV} not found.")
        sys.exit(1)

    rows = list(csv.DictReader(GROUND_TRUTH_CSV.open()))
    results = []
    exact_matches = 0
    score_errors  = []

    print(f"\n{'Policy':<35} {'Expert':>7} {'System':>7} {'Live':>7} {'Agree':>6}")
    print("-" * 70)

    for row in rows:
        name         = row["policy_name"]
        expert_grade = row["expert_grade"].strip()
        expert_score = float(row["expert_score"])
        system_grade = row["system_grade"].strip()

        # Try to run live if sample text available
        text = load_sample_text(name)
        if text:
            live = grade_text(text)
            live_grade = live["grade"]
            live_score = live["score"]
        else:
            live_grade = system_grade
            live_score = float(row["system_score"])

        agrees    = live_grade == expert_grade
        score_err = abs(live_score - expert_score)

        if agrees:
            exact_matches += 1
        score_errors.append(score_err)

        status = "YES" if agrees else "NO "
        print(f"{name:<35} {expert_grade:>7} {system_grade:>7} {live_grade:>7} {status:>6}")
        results.append({
            "policy":        name,
            "expert_grade":  expert_grade,
            "live_grade":    live_grade,
            "live_score":    live_score,
            "agrees":        agrees,
            "score_error":   score_err,
        })

    n   = len(rows)
    acc = exact_matches / n * 100
    mae = sum(score_errors) / len(score_errors)

    print("-" * 70)
    print(f"\nGrade Agreement:  {exact_matches}/{n}  ({acc:.0f}%)")
    print(f"Score MAE:        {mae:.1f} points")
    print(f"Result:           {'PASS (>=70% agreement)' if acc >= 70 else 'FAIL (<70% agreement)'}")

    # Save results JSON for notebook / report
    out = root / "samples" / "evaluation_results.json"
    out.write_text(json.dumps({"accuracy": acc, "mae": mae, "details": results}, indent=2))
    print(f"\nDetailed results saved to: {out}")


if __name__ == "__main__":
    main()
