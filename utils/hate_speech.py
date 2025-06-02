
from detoxify import Detoxify

# Load once
_model = None
def get_hate_speech_model():
    global _model
    if _model is None:
        _model = Detoxify("original")
    return _model

def detect_hate_speech(text):
    model = get_hate_speech_model()
    results = model.predict(text)
    return results

def enrich_with_hate_speech(results):
    enriched = []
    for item in results:
        text_fields = [v for k, v in item.items() if isinstance(v, str)]
        combined_text = " ".join(text_fields)
        prediction = detect_hate_speech(combined_text)
        item.update(prediction)  # adds fields like 'toxicity', 'insult', etc.
        enriched.append(item)
    return enriched
