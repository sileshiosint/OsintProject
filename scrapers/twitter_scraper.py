import asyncio
from playwright.async_api import async_playwright
from scrapers.config import USER_DATA_DIR, COMMON_USER_AGENT, HEADLESS_MODE # Import from config
import os # For os.path.exists and os.makedirs

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
    screenshot_path = f"twitter_search_{query.replace(' ','_')}_{search_type}.png" # Default screenshot name

    # Ensure USER_DATA_DIR exists before Playwright tries to use it
    if not os.path.exists(USER_DATA_DIR):
        print(f"Twitter Scraper: Creating USER_DATA_DIR at {USER_DATA_DIR}")
        os.makedirs(USER_DATA_DIR, exist_ok=True)
    # else:
        # print(f"Twitter Scraper: USER_DATA_DIR {USER_DATA_DIR} already exists.") # Less verbose

    async with async_playwright() as p:
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

        try:
            # Base URL for search, query is added, and "f=live" for "Latest" tab.
            base_url = "https://twitter.com/search"
            params = f"q={query}&src=typed_query"
            if search_type.lower() == "recent":
                params += "&f=live"

            full_url = f"{base_url}?{params}"
            print(f"Navigating to Twitter search URL: {full_url}")

            await page.goto(full_url, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(3000) # Allow some initial loading, potential redirects or dynamic content

            # Check if login is truly successful - look for a primary feed or known logged-in element
            # For example, the "Home" link in the navigation sidebar.
            # If not found, it might still be on a login/interstitial page.
            primary_nav_selector = 'nav[aria-label="Primary"] a[data-testid="AppTabBar_Home_Link"]'
            try:
                await page.wait_for_selector(primary_nav_selector, timeout=10000, state="visible")
                print("Logged-in interface confirmed (Home link found).")
            except Exception:
                print("Warning: Main logged-in interface (Home link) not confirmed. Page might be unexpected (e.g. login, captcha, interstitial).")
                html_content = await page.content()
                await page.screenshot(path=f"debug_twitter_{query.replace(' ','_')}_unexpected_page.png")
                # Proceeding anyway, as sometimes parts of the page load even if the main nav isn't immediately there.

            # Scrolling to load tweets
            collected_tweets_count = 0
            max_tweets_to_collect = 15
            scroll_attempts = 0
            max_scroll_attempts = 10 # Try scrolling up to 10 times

            tweet_selector = 'article[data-testid="tweet"]'

            while collected_tweets_count < max_tweets_to_collect and scroll_attempts < max_scroll_attempts:
                await page.wait_for_selector(tweet_selector, timeout=20000, state="attached")
                tweet_elements = await page.query_selector_all(tweet_selector)

                if not tweet_elements:
                    print("No tweet articles found on the page.")
                    break

                print(f"Found {len(tweet_elements)} tweet elements on page (scroll attempt {scroll_attempts + 1}).")

                for tweet_element in tweet_elements:
                    if collected_tweets_count >= max_tweets_to_collect:
                        break

                    tweet_data = {}
                    try:
                        # Tweet URL and Timestamp
                        time_element = await tweet_element.query_selector('time')
                        if time_element:
                            tweet_data["timestamp"] = await time_element.get_attribute('datetime')
                            link_element = await time_element.query_selector('xpath=./ancestor::a[@role="link"]')
                            if link_element:
                                tweet_url = await link_element.get_attribute('href')
                                if tweet_url and not tweet_url.startswith(('http://', 'https://')):
                                    tweet_url = f"https://twitter.com{tweet_url}"
                                tweet_data["url"] = tweet_url

                        # Tweet Text
                        text_element = await tweet_element.query_selector('div[data-testid="tweetText"]')
                        if text_element:
                            tweet_data["text"] = await text_element.inner_text()

                        # Author Info
                        user_name_element = await tweet_element.query_selector('div[data-testid="User-Name"]')
                        if user_name_element:
                            # Display Name (often the first span or a specific complex selector)
                            # This can be tricky as structure varies.
                            display_name_el = await user_name_element.query_selector('span > span > span:not([dir="ltr"])') # Heuristic
                            if not display_name_el: # Fallback
                                display_name_el = await user_name_element.query_selector('div > div > div > a > div > div > span > span:not([dir="ltr"])')

                            if display_name_el:
                                tweet_data["author_display_name"] = await display_name_el.inner_text()

                            # Screen Name (handle starting with @)
                            screen_name_el = await user_name_element.query_selector('div[dir="ltr"] span')
                            if screen_name_el:
                                screen_name = await screen_name_el.inner_text()
                                tweet_data["author_screen_name"] = screen_name if screen_name.startswith('@') else f"@{screen_name}"

                        # Check if we have enough data to consider it a valid tweet extract
                        if tweet_data.get("url") and tweet_data.get("text"):
                            # Avoid duplicates based on URL
                            if not any(t.get("url") == tweet_data.get("url") for t in results):
                                results.append(tweet_data)
                                collected_tweets_count += 1
                                print(f"Collected tweet #{collected_tweets_count}: {tweet_data.get('url')}")

                    except Exception as e_extract:
                        print(f"Error extracting data from a tweet element: {e_extract}")
                        continue # Move to the next tweet element

                if collected_tweets_count < max_tweets_to_collect:
                    print(f"Scrolling down to load more tweets (collected {collected_tweets_count}/{max_tweets_to_collect})...")
                    await page.evaluate('window.scrollBy(0, window.innerHeight * 2)') # Scroll more aggressively
                    await page.wait_for_timeout(3000 + (scroll_attempts * 500)) # Dynamic wait, longer for later scrolls
                    scroll_attempts += 1
                else:
                    print("Reached max tweets to collect or no more new tweets after scrolling.")
                    break

            if not results:
                 print("No tweets were successfully scraped.")

            html_content = await page.content() # Get final page HTML
            await page.screenshot(path=screenshot_path) # Screenshot of the final state
            print(f"Final screenshot saved to {screenshot_path}")

        except Exception as e_general:
            print(f"An unexpected error occurred during Twitter scraping: {type(e_general).__name__} - {e_general}")
            screenshot_path = f"debug_twitter_{query.replace(' ','_')}_{search_type}_general_error.png"
            try:
                if page and not page.is_closed():
                    current_html = await page.content()
                    if current_html: html_content = current_html
                    await page.screenshot(path=screenshot_path)
                    print(f"Error screenshot saved to {screenshot_path}")
            except Exception as e_debug_general:
                print(f"Could not capture page content/screenshot during general error handling: {e_debug_general}")
        finally:
            if context:
                await context.close()

    return {
        "platform": "twitter",
        "query": query,
        "search_type": search_type,
        "results": results,
        "html": html_content,
        "screenshot": screenshot_path
    }

if __name__ == '__main__':
    async def main():
        print("Twitter Scraper - Logged-in Test")
        # Test with a common query. User should be logged into Twitter in their Chrome profile.
        # The USER_DATA_DIR in scrapers/config.py should point to this profile.
        # Set HEADLESS_MODE=False in scrapers/config.py for easier debugging if needed.

        test_query = "AI ethics"
        test_search_type = "recent" # or "top"

        print(f"\nAttempting to scrape Twitter for '{test_query}' ({test_search_type})...")
        data = await scrape_twitter(test_query, test_search_type)

        print(f"\n--- Results for '{test_query}' ({len(data['results'])} tweets) ---")
        if data['results']:
            for i, tweet in enumerate(data['results']):
                print(f"Tweet #{i+1}:")
                print(f"  Author: {tweet.get('author_display_name', 'N/A')} ({tweet.get('author_screen_name', 'N/A')})")
                print(f"  Timestamp: {tweet.get('timestamp', 'N/A')}")
                print(f"  URL: {tweet.get('url', 'N/A')}")
                print(f"  Text: {tweet.get('text', 'N/A')[:100]}...") # Print first 100 chars of text
                print("-" * 20)
        else:
            print("No tweets successfully extracted.")

        print(f"\nHTML content captured: {'Yes (length: ' + str(len(data['html'])) + ')' if data['html'] and not data['html'].startswith('Error:') else 'No or error'}")
        print(f"Screenshot saved at: {data['screenshot']}")
        print("--- Test Complete ---")

    asyncio.run(main())
