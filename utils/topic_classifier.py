
def classify_topic(text):
    text_lower = text.lower()

    if any(kw in text_lower for kw in ["attack", "bomb", "kill", "ambush", "massacre", "raid"]):
        return "Violence"

    if any(kw in text_lower for kw in ["propaganda", "fake news", "disinfo", "hoax", "false report"]):
        return "Disinformation"

    if any(kw in text_lower for kw in ["protest", "demonstration", "riot", "strike"]):
        return "Civil Unrest"

    if any(kw in text_lower for kw in ["ethnic", "religious", "tribe", "sect", "identity"]):
        return "Ethnic/Religious Tension"

    return "Uncategorized"


def enrich_with_topic_classification(results):
    for r in results:
        r["topic"] = classify_topic(r.get("content", ""))
    return results
