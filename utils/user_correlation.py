
import re

def normalize_username(username):
    return re.sub(r"[^a-z0-9]", "", username.lower())

def correlate_usernames(result_sets):
    """
    Takes a dict of {platform: [results]} and returns matched usernames across platforms.
    """
    user_map = {}  # {normalized: {platform: [raw names]}}

    for platform, results in result_sets.items():
        for r in results:
            username = r.get("username")
            if not username:
                continue
            norm = normalize_username(username)
            if norm not in user_map:
                user_map[norm] = {}
            user_map[norm].setdefault(platform, []).append(username)

    # Filter to only cross-platform users
    cross_platform = {
        k: v for k, v in user_map.items() if len(v) > 1
    }

    return cross_platform
