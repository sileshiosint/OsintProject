
import asyncio
import os
from scrapers.twitter_scraper import scrape_twitter
from scrapers.facebook_scraper import scrape_facebook
from scrapers.telegram_scraper import scrape_telegram

PLATFORM_SCRAPERS = {
    "Telegram": scrape_telegram,
    "Twitter": scrape_twitter,
    "Facebook": scrape_facebook,
}

# Path to existing user browser session (adjust if needed)
USER_DATA_DIR = os.getenv("USER_DATA_DIR", os.path.expanduser("~/.config/google-chrome"))

async def run_scraper(search_query: str, search_type: str, platforms: list):
    tasks = []
    for platform in platforms:
        scraper_func = PLATFORM_SCRAPERS.get(platform)
        if scraper_func:
            tasks.append(scraper_func(search_query, search_type))
        else:
            print(f"[!] No scraper implemented for {platform}")

    results = await asyncio.gather(*tasks, return_exceptions=True)
    formatted_results = []
    for platform, result in zip(platforms, results):
        if isinstance(result, Exception):
            formatted_results.append({
                "platform": platform,
                "query": search_query,
                "status": "error",
                "error": str(result)
            })
        else:
            formatted_results.append(result)
    return formatted_results
