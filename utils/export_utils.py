
import csv
import json
import os

EXPORT_DIR = "exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

def export_to_json(results, filename):
    path = os.path.join(EXPORT_DIR, f"{filename}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    return path

def export_to_csv(results, filename):
    path = os.path.join(EXPORT_DIR, f"{filename}.csv")
    with open(path, "w", newline='', encoding="utf-8") as csvfile:
        fieldnames = ["platform", "query", "search_type", "result", "html", "screenshot"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for entry in results:
            for r in entry.get("results", []):
                writer.writerow({
                    "platform": entry["platform"],
                    "query": entry["query"],
                    "search_type": entry["search_type"],
                    "result": r,
                    "html": entry.get("html", ""),
                    "screenshot": entry.get("screenshot", "")
                })
    return path
