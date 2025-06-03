
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
# import json # Not strictly needed if SearchResult.set_result_data handles it
import logging

logger = logging.getLogger(__name__)

async def run_scraper(search_query: str, search_type: str, platforms: list):
    logger.info(f"run_scraper called. Query: '{search_query}', Type: '{search_type}', Platforms: {platforms}")
    tasks = []
    for platform in platforms:
        scraper_func = PLATFORM_SCRAPERS.get(platform)
        if scraper_func:
            tasks.append(scraper_func(search_query, search_type))
        else:
            logger.warning(f"No scraper implemented for {platform}")
            # Optionally add a placeholder result for unhandled platforms if needed by frontend
            # For now, it just skips them.

    logger.debug(f"Preparing to launch scrapers for platforms: {platforms}")
    # results_from_gather will hold outputs from each scraper_func call
    results_from_gather = await asyncio.gather(*tasks, return_exceptions=True)

    formatted_results_for_api = []
    db_results_to_add = []

    for platform_name, scraper_output_or_exception in zip(platforms, results_from_gather):
        search_result_instance = SearchResult(
            search_type=search_type,
            search_query=search_query,
            platform=platform_name
        )

        if isinstance(scraper_output_or_exception, Exception):
            logger.error(f"Scraper for {platform_name} failed with exception: {scraper_output_or_exception}", exc_info=True)
            search_result_instance.status = "error"
            error_detail_for_db = {
                "error_message": str(scraper_output_or_exception),
                "details": "Scraping process failed with an unhandled exception for this platform."
            }
            search_result_instance.set_result_data(error_detail_for_db)

            # This is what the API route will get back for this platform
            formatted_results_for_api.append({
                "platform": platform_name,
                "query": search_query,
                "search_type": search_type,
                "status": "error",
                "error": str(scraper_output_or_exception), # For direct API error field
                "results": [],
                "status_detail": error_detail_for_db.get("details"), # from the above
                "html": None, # No HTML if scraper crashed early
                "screenshot": None # No screenshot if scraper crashed early
            })
        else:
            # This is the dictionary returned by the individual scraper
            scraped_data_dict = scraper_output_or_exception

            # Override platform in DB record if scraper specifies it (should match platform_name)
            search_result_instance.platform = scraped_data_dict.get("platform", platform_name)

            actual_scraped_items = scraped_data_dict.get("results", [])
            status_detail = scraped_data_dict.get("status_detail", "Scraping completed.") # Get enhanced status detail

            logger.info(f"Scraper for {platform_name} completed. Items: {len(actual_scraped_items)}. Status detail: '{status_detail}'")

            if not actual_scraped_items:
                # If status_detail indicates a specific reason like "Login required", use that for status.
                # This requires scrapers to return informative status_detail.
                if "login required" in status_detail.lower() or "login wall" in status_detail.lower():
                    search_result_instance.status = "login_required"
                else:
                    search_result_instance.status = "no_results_found"

                search_result_instance.set_result_data({
                    "message": status_detail if status_detail else "No results found.",
                    "original_results_count": len(actual_scraped_items)
                })
            else:
                search_result_instance.status = "success"
                search_result_instance.set_result_data(actual_scraped_items) # Store only the list of items

            # Add to formatted_results_for_api (this is what API route gets)
            # Ensure it includes all necessary fields for the API from scraped_data_dict
            api_result_for_platform = {
                "platform": search_result_instance.platform,
                "query": search_query,
                "search_type": search_type,
                "status": search_result_instance.status, # Use the status determined for DB
                "status_detail": status_detail,
                "results": actual_scraped_items,
                "html": scraped_data_dict.get("html"),
                "screenshot": scraped_data_dict.get("screenshot"),
                "notes": scraped_data_dict.get("notes") # Keep notes if provided
            }
            if search_result_instance.status == "error": # If scraper itself reported an error status
                 api_result_for_platform["error"] = status_detail

            formatted_results_for_api.append(api_result_for_platform)

        db_results_to_add.append(search_result_instance)

    if db_results_to_add:
        try:
            logger.debug(f"Attempting to add {len(db_results_to_add)} SearchResult objects to DB session.")
            db.session.add_all(db_results_to_add)
            db.session.commit()
            logger.info("Successfully committed search results to database.")
        except Exception as e_db:
            logger.error(f"Database commit failed: {e_db}", exc_info=True)
            db.session.rollback()
            # Note: formatted_results_for_api still contains the scraped data even if DB commit fails.
            # The API will return data, but it won't be persisted. This might be desired.

    return formatted_results_for_api
