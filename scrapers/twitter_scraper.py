import asyncio
from playwright.async_api import async_playwright
from scrapers.config import USER_DATA_DIR, COMMON_USER_AGENT, HEADLESS_MODE
import os
import logging

logger = logging.getLogger(__name__)

async def scrape_twitter(query: str, search_type: str):
    """
    Scrapes Twitter for tweets based on a query using a persistent browser context.
    Assumes the user is logged in via the persistent context.

    Args:
        query: The search query.
        search_type: The type of search (e.g., "recent", "top"). "recent" maps to "Latest" tab.

    Returns:
        A dictionary containing the scraped data.
    """
    results = []
    html_content = "Error: Playwright page content not captured."
    status_detail = "Scraping process started."
    screenshot_path = f"twitter_search_{query.replace(' ','_')}_{search_type}.png"

    logger.info(f"Starting Twitter scraper for query: '{query}', type: '{search_type}'")

    if not os.path.exists(USER_DATA_DIR):
        logger.info(f"Creating USER_DATA_DIR for Twitter at {USER_DATA_DIR}")
        os.makedirs(USER_DATA_DIR, exist_ok=True)

    async with async_playwright() as p:
        context = None
        page = None
        try:
            context = await p.chromium.launch_persistent_context(
                USER_DATA_DIR,
                headless=HEADLESS_MODE,
                user_agent=COMMON_USER_AGENT,
                accept_downloads=True,
                ignore_https_errors=True,
                bypass_csp=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
                viewport={'width': 1280, 'height': 900}
            )
            page = await context.new_page()

            base_url = "https://twitter.com/search"
            params = f"q={query}&src=typed_query"
            if search_type.lower() == "recent":
                params += "&f=live"

            full_url = f"{base_url}?{params}"

            logger.debug(f"Navigating to Twitter URL: {full_url}")
            await page.goto(full_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            primary_nav_selector = 'nav[aria-label="Primary"] a[data-testid="AppTabBar_Home_Link"]'
            logged_in_confirmation_selector = 'div[data-testid="primaryColumn"]'

            try:
                await page.wait_for_selector(logged_in_confirmation_selector, timeout=15000, state="visible")
                logger.info("Logged-in interface confirmed by primary column.")
                if not await page.locator(primary_nav_selector).is_visible(timeout=2000):
                    logger.warning("Home link not immediately visible, but primary column found. Proceeding.")
            except Exception as e_login_check:
                logger.warning(f"Main logged-in interface not confirmed (primary column missing): {e_login_check}. Page might be login/captcha/interstitial.")
                status_detail = "Login required or verification page encountered."
                html_content = await page.content()
                screenshot_path = f"debug_twitter_{query.replace(' ','_')}_login_required_page.png"
                await page.screenshot(path=screenshot_path)
                # No early return, finally block will close context
                # results will be empty, status_detail indicates issue

            if status_detail == "Scraping process started.": # Only proceed if login check passed
                logger.debug("Attempting to handle cookie/login pop-ups (if any remain).")
                cookie_selectors = ['div[data-testid="placementTracking"] button[aria-label*="Accept"]', 'button:has-text("Accept all cookies")']
                for selector in cookie_selectors:
                    try:
                        if await page.locator(selector).first.is_visible(timeout=1000):
                            logger.info(f"Found and clicking cookie/consent button: {selector}")
                            await page.locator(selector).first.click()
                            await page.wait_for_timeout(1000)
                    except: pass

                logger.debug("Starting tweet extraction loop.")
                collected_tweets_count = 0
                max_tweets_to_collect = 15
                scroll_attempts = 0
                max_scroll_attempts = 10
                tweet_selector = 'article[data-testid="tweet"]'
                seen_tweet_urls = set()

                while collected_tweets_count < max_tweets_to_collect and scroll_attempts < max_scroll_attempts:
                    try:
                        await page.wait_for_selector(tweet_selector, timeout=15000, state="attached")
                    except Exception:
                        logger.warning(f"Tweet selector '{tweet_selector}' not found after {scroll_attempts} scrolls. Ending.")
                        if status_detail == "Scraping process started.": status_detail = "No more tweets found or page structure changed."
                        break

                    tweet_elements = await page.query_selector_all(tweet_selector)
                    if not tweet_elements:
                        logger.info("No tweet articles found on the page in current view.")
                        if status_detail == "Scraping process started.": status_detail = "No tweets visible in current view."
                        break

                    logger.debug(f"Processing {len(tweet_elements)} tweet elements found in view (scroll attempt {scroll_attempts + 1}).")
                    new_tweets_found_this_scroll = 0

                    for tweet_element in tweet_elements:
                        if collected_tweets_count >= max_tweets_to_collect:
                            break

                        tweet_data = {}
                        tweet_url = None
                        try:
                            time_element = await tweet_element.query_selector('time')
                            if time_element:
                                tweet_data["timestamp"] = await time_element.get_attribute('datetime')
                                link_element = await time_element.query_selector('xpath=./ancestor::a[@role="link"]')
                                if link_element:
                                    relative_url = await link_element.get_attribute('href')
                                    if relative_url:
                                        tweet_url = f"https://twitter.com{relative_url}" if relative_url.startswith('/') else relative_url
                                        tweet_data["url"] = tweet_url

                            if tweet_url and tweet_url in seen_tweet_urls:
                                continue

                            text_element = await tweet_element.query_selector('div[data-testid="tweetText"]')
                            if text_element: tweet_data["text"] = await text_element.inner_text()

                            user_name_element = await tweet_element.query_selector('div[data-testid="User-Name"]')
                            if user_name_element:
                                display_name_el = await user_name_element.query_selector('span > span > span:not([dir="ltr"])')
                                if not display_name_el:
                                    display_name_el = await user_name_element.query_selector('div > div > div > a > div > div > span > span:not([dir="ltr"])')
                                if display_name_el: tweet_data["author_display_name"] = await display_name_el.inner_text()

                                screen_name_el = await user_name_element.query_selector('div[dir="ltr"] span')
                                if screen_name_el:
                                    screen_name = await screen_name_el.inner_text()
                                    tweet_data["author_screen_name"] = screen_name if screen_name.startswith('@') else f"@{screen_name}"

                            if tweet_data.get("url") and (tweet_data.get("text") or tweet_data.get("author_screen_name")):
                                results.append(tweet_data)
                                if tweet_url: seen_tweet_urls.add(tweet_url)
                                collected_tweets_count += 1
                                new_tweets_found_this_scroll +=1
                            else:
                                logger.warning(f"Could not extract essential data (URL or text/author) from a tweet element. Data: {tweet_data}")

                        except Exception as e_extract:
                            logger.error(f"Error extracting data from a tweet element: {e_extract}", exc_info=True)
                            continue

                    if collected_tweets_count >= max_tweets_to_collect:
                        logger.info(f"Reached max tweets to collect ({max_tweets_to_collect}).")
                        if status_detail == "Scraping process started.": status_detail = f"Collected {collected_tweets_count} tweets."
                        break

                    if new_tweets_found_this_scroll == 0 and scroll_attempts > 1:
                        logger.info("No new tweets found in this scroll iteration. Assuming end of results or issue.")
                        if status_detail == "Scraping process started.": status_detail = f"Collected {collected_tweets_count} tweets. No new tweets found after scrolling."
                        break

                    logger.debug(f"Scrolling down to load more tweets (collected {collected_tweets_count}/{max_tweets_to_collect})...")
                    await page.evaluate('window.scrollBy(0, window.innerHeight * 1.5)')
                    await page.wait_for_timeout(2500 + (scroll_attempts * 300))
                    scroll_attempts += 1

                if not results:
                     logger.info("No tweets were successfully scraped for query.")
                     if status_detail == "Scraping process started.":
                        status_detail = "Search completed, but no public tweets found matching the query or accessible."
                elif status_detail == "Scraping process started.": # If results found and no other specific status
                    status_detail = f"Successfully collected {len(results)} tweets."

            logger.info(f"Finished scraping for '{query}'. {status_detail}")
            if page and not page.is_closed(): # Ensure page is usable for final capture
                html_content = await page.content()
                # Update screenshot path for final successful state
                screenshot_path = f"twitter_search_{query.replace(' ','_')}_{search_type}_final.png"
                await page.screenshot(path=screenshot_path)
                logger.debug(f"Final screenshot saved to {screenshot_path}")
            else:
                logger.warning("Page was closed or unavailable for final HTML/screenshot capture.")
                html_content = "Page not available for final HTML capture."


        except Exception as e_general:
            logger.error(f"An unexpected error occurred during Twitter scraping for query '{query}': {e_general}", exc_info=True)
            if status_detail == "Scraping process started.": status_detail = f"Critical error during scraping: {type(e_general).__name__}"
            # Update screenshot path for general error
            screenshot_path = f"debug_twitter_{query.replace(' ','_')}_{search_type}_general_error.png"
            try:
                if page and not page.is_closed():
                    current_html = await page.content()
                    if current_html: html_content = current_html
                    await page.screenshot(path=screenshot_path)
                    logger.debug(f"Error screenshot saved to {screenshot_path}")
            except Exception as e_debug_general:
                logger.error(f"Could not capture page content/screenshot during general error handling: {e_debug_general}", exc_info=True)
        finally:
            if context:
                try:
                    await context.close()
                    logger.debug("Playwright context closed.")
                except Exception as e_close:
                    logger.error(f"Error closing context: {e_close}", exc_info=True)


    return {
        "platform": "twitter",
        "query": query,
        "search_type": search_type,
        "results": results,
        "html": html_content,
        "screenshot": screenshot_path,
        "status_detail": status_detail
    }

if __name__ == '__main__':
    async def main():
        print("Twitter Scraper - Logged-in Test")
        test_query = "AI ethics"
        test_search_type = "recent"

        print(f"\nAttempting to scrape Twitter for '{test_query}' ({test_search_type})...")
        data = await scrape_twitter(test_query, test_search_type)

        print(f"\n--- Results for '{test_query}' ({len(data['results'])} tweets) ---")
        if data['results']:
            for i, tweet in enumerate(data['results']):
                print(f"Tweet #{i+1}:")
                print(f"  Author: {tweet.get('author_display_name', 'N/A')} ({tweet.get('author_screen_name', 'N/A')})")
                print(f"  Timestamp: {tweet.get('timestamp', 'N/A')}")
                print(f"  URL: {tweet.get('url', 'N/A')}")
                print(f"  Text: {tweet.get('text', 'N/A')[:100]}...")
                print("-" * 20)
        else:
            print("No tweets successfully extracted.")

        print(f"\nHTML content captured: {'Yes (length: ' + str(len(data['html'])) + ')' if data['html'] and not data['html'].startswith('Error:') else 'No or error'}")
        print(f"Screenshot saved at: {data['screenshot']}")
        print(f"Status Detail: {data.get('status_detail')}")
        print("--- Test Complete ---")

    asyncio.run(main())
