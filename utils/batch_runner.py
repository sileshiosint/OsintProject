
import json
import time
from utils.scraper_engine import run_scraper
from utils.nlp_tools import enrich_results_with_nlp
from utils.hate_speech import enrich_with_hate_speech
from utils.scraper_engine import export_enriched_results

def run_batch_from_config(config_file="batch_jobs.json"):
    with open(config_file, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    for job in jobs:
        platform = job.get("platform")
        query = job.get("query")
        delay = job.get("delay", 2)

        print(f"🔍 Running job for: {platform} → {query}")
        results = run_scraper(query, platform)

        if not results:
            print(f"⚠️ No results for {platform} → {query}")
            continue

        enriched = enrich_results_with_nlp(results)
        enriched = enrich_with_hate_speech(enriched)
        export_file = export_enriched_results(enriched, query, platform)
        print(f"✅ Exported to: {export_file}")

        time.sleep(delay)
