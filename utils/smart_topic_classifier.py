
from transformers import pipeline

candidate_labels = ["Violence", "Disinformation", "Civil Unrest", "Ethnic Tension", "Religious Tension", "Uncategorized"]

def enrich_with_smart_topics(results):
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

    for r in results:
        text = r.get("content", "")
        if text:
            result = classifier(text, candidate_labels)
            r["topic"] = result["labels"][0]
    return results
