
import spacy
from textblob import TextBlob

# Load spaCy model (ensure 'en_core_web_sm' is installed)
try:
    nlp = spacy.load("en_core_web_sm")
except:
    import os
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def analyze_text_nlp(text):
    blob = TextBlob(text)
    sentiment = blob.sentiment.polarity  # -1 to 1 scale

    doc = nlp(text)
    entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]

    return {
        "sentiment": sentiment,
        "entities": entities
    }

def enrich_results_with_nlp(results):
    enriched = []
    for item in results:
        text_fields = [v for k, v in item.items() if isinstance(v, str)]
        combined_text = " ".join(text_fields)
        analysis = analyze_text_nlp(combined_text)
        item["sentiment"] = analysis["sentiment"]
        item["entities"] = analysis["entities"]
        enriched.append(item)
    return enriched
