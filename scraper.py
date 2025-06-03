
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

# USER_DATA_DIR is now defined in scrapers.config
# from scrapers.config import USER_DATA_DIR # Not directly used in this file anymore if scrapers handle it
from app import db
from models import SearchResult
import json # Though SearchResult.set_result_data handles json.dumps

async def run_scraper(search_query: str, search_type: str, platforms: list):
    tasks = []
    # Ensure search_type and search_query are passed to scrapers if they need it for their own logic,
    # but they are primarily used here for DB storage.
    for platform in platforms:
        scraper_func = PLATFORM_SCRAPERS.get(platform)
        if scraper_func:
            tasks.append(scraper_func(search_query, search_type))
        else:
            print(f"[!] No scraper implemented for {platform}")

    results = await asyncio.gather(*tasks, return_exceptions=True)
    formatted_results = []
    db_results_to_add = []

    for platform_name, scraped_data_dict_or_exception in zip(platforms, results):
        search_result_instance = SearchResult(
            search_type=search_type,
            search_query=search_query,
            platform=platform_name # Use the platform name from the iteration
        )

        if isinstance(scraped_data_dict_or_exception, Exception):
            print(f"Error during scraping {platform_name}: {scraped_data_dict_or_exception}")
            search_result_instance.status = "error"
            # Store basic error info in result_data for API response, not for DB's main result_data
            # The DB's result_data will be empty/null for errors.
            search_result_instance.set_result_data({
                "error_message": str(scraped_data_dict_or_exception),
                "details": "Scraping process failed for this platform."
            })
            formatted_results.append({
                "platform": platform_name,
                "query": search_query,
                "search_type": search_type,
                "status": "error",
                "error": str(scraped_data_dict_or_exception),
                "results": [] # Keep results structure consistent for API
            })
        else:
            # This is the dictionary returned by the individual scraper
            scraped_data_dict = scraped_data_dict_or_exception

            # Ensure platform in scraped_data_dict matches platform_name, or override
            # This also ensures the SearchResult instance has the correct platform from the scraper
            search_result_instance.platform = scraped_data_dict.get("platform", platform_name)

            scraped_items = scraped_data_dict.get("results", [])
            if not scraped_items:
                search_result_instance.status = "no_results_found"
                # Consider adding a note if available, e.g. from telegram scraper for login required
                notes = scraped_data_dict.get("notes")
                if notes:
                    search_result_instance.set_result_data({"message": "No results found.", "notes": notes})
                else:
                    search_result_instance.set_result_data({"message": "No results found."})
            else:
                search_result_instance.status = "success"
                search_result_instance.set_result_data(scraped_items) # Store only the list of items

            # Add to formatted_results for API response (includes html/screenshot for debugging if needed by API)
            formatted_results.append(scraped_data_dict)

        db_results_to_add.append(search_result_instance)

    if db_results_to_add:
        try:
            print(f"Attempting to add {len(db_results_to_add)} search results to database.")
            db.session.add_all(db_results_to_add)
            db.session.commit()
            print("Search results committed to database.")
        except Exception as e_db:
            print(f"Database error: {e_db}")
            db.session.rollback()
            # Optionally, update formatted_results to indicate DB error for relevant items
            # For now, just logging it. The API response will still have the scraped data.

    return formatted_results
