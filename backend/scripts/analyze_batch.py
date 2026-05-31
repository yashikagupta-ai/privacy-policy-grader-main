"""
scripts/analyze_batch.py — CLI tool for bulk privacy-policy analysis.

OUR CUSTOM CODE — NO LLM USED FOR CLI LOGIC.
Uses existing backend services to analyze a list of URLs and export a CSV.
"""

import argparse
import csv
import sys
import os
import time
from pathlib import Path

# Ensure backend/ is in python path
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

from services.scraper import PrivacyPolicyScraper
from services.preprocessor import PolicyPreprocessor
from services.llm_service import PrivacyAnalyzer
from services.grading_engine import GradingEngine
from services.verifier import ClaimVerifier
from database.db_manager import DatabaseManager
from utils.url_validator import URLValidator

def run_batch(urls, output_file="batch_results.csv"):
    scraper = PrivacyPolicyScraper()
    analyzer = PrivacyAnalyzer()
    grader = GradingEngine()
    verifier = ClaimVerifier()
    
    DatabaseManager.init_db()
    
    results = []
    print(f"Starting batch analysis of {len(urls)} URLs...")
    
    for i, url in enumerate(urls, 1):
        url = url.strip()
        if not url: continue
        
        print(f"[{i}/{len(urls)}] Analysing: {url}")
        
        try:
            t0 = time.time()
            scraped = scraper.extract_policy(url)
            if not scraped:
                print(f"  FAILED: Could not scrape {url}")
                continue
                
            metrics = PolicyPreprocessor.process(scraped["policy_text"], scraped.get("sections", []), scraped.get("last_updated"))
            llm = analyzer.analyze_with_gemini(scraped["policy_text"], metrics)
            grading = grader.calculate_grade(llm, metrics)
            verification = verifier.verify_claims(llm, scraped["policy_text"])
            
            trust_score = grader.calculate_trust_score(
                overall_score=grading["overall_score"],
                dark_pattern_score=metrics.get("dark_pattern_score", 0),
                verification_confidence=verification.get("overall_confidence", 0.5),
                red_flag_count=len(llm.get("red_flags", [])),
            )
            
            domain = URLValidator.extract_domain(url)
            company = domain.replace("www.", "").split(".")[0].capitalize()
            
            # Save to DB
            DatabaseManager.save_analysis({
                "url": url,
                "company_name": company,
                "policy_text": scraped["policy_text"][:50000],
                "grade": grading["grade"],
                "overall_score": grading["overall_score"],
                "trust_score": trust_score,
                "dimension_scores": grading["dimension_scores"],
                "findings": llm,
                "metrics": metrics,
                "red_flags": llm.get("red_flags", []),
                "dark_pattern_score": metrics.get("dark_pattern_score", 0.0),
            })
            
            results.append({
                "url": url,
                "company": company,
                "grade": grading["grade"],
                "score": round(grading["overall_score"], 1),
                "trust_score": round(trust_score, 1),
                "word_count": metrics.get("word_count", 0),
                "red_flags": len(llm.get("red_flags", [])),
                "gdpr_basis": metrics.get("gdpr_basis", "N/A"),
                "time_sec": round(time.time() - t0, 1)
            })
            print(f"  SUCCESS: Grade {grading['grade']} | Score {grading['overall_score']}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            
    if results:
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        print(f"\nBatch complete! Results saved to {output_file}")
    else:
        print("\nBatch finished with no successful results.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk Privacy Policy Analyser CLI")
    parser.add_argument("--urls", nargs="+", help="Space-separated list of URLs to analyse")
    parser.add_argument("--file", help="Path to a text file containing one URL per line")
    parser.add_argument("--output", default="batch_results.csv", help="Output CSV filename")
    
    args = parser.parse_args()
    
    target_urls = []
    if args.urls:
        target_urls.extend(args.urls)
    if args.file:
        if os.path.exists(args.file):
            with open(args.file, "r") as f:
                target_urls.extend([line.strip() for line in f if line.strip()])
        else:
            print(f"Error: File {args.file} not found.")
            sys.exit(1)
            
    if not target_urls:
        print("Error: No URLs provided. Use --urls or --file.")
        sys.exit(1)
        
    run_batch(target_urls, args.output)
