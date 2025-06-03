import asyncio
from playwright.async_api import async_playwright
import re
from scrapers.config import USER_DATA_DIR, COMMON_USER_AGENT, HEADLESS_MODE
import os
import logging

logger = logging.getLogger(__name__)

async def scrape_facebook(query: str, search_type: str): # search_type is retained for interface consistency
    """
    Attempts to scrape Facebook posts based on a query using a persistent browser context.
    Assumes the user is logged in via the persistent context.
    Focuses on the 'posts' search tab. This scraper is highly sensitive to UI changes.
    """
    results = []
    html_content = "Error: Playwright page content not captured."
    status_detail = "Scraping process started."
    screenshot_path = f"facebook_search_posts_{query.replace(' ','_')}.png"

    logger.info(f"Starting Facebook scraper for query: '{query}', search_type: '{search_type}' (targeting posts)")

    if not os.path.exists(USER_DATA_DIR):
        logger.info(f"Creating USER_DATA_DIR for Facebook at {USER_DATA_DIR}")
        os.makedirs(USER_DATA_DIR, exist_ok=True)
    # else:
    #     logger.debug(f"USER_DATA_DIR {USER_DATA_DIR} already exists.")

    async with async_playwright() as p:
        context = None # Initialize for robust finally block
        page = None # Initialize for robust finally block
        try:
            context = await p.chromium.launch_persistent_context(
                USER_DATA_DIR,
                headless=HEADLESS_MODE,
                user_agent=COMMON_USER_AGENT,
                accept_downloads=True,
                ignore_https_errors=True,
                bypass_csp=True,
                java_script_enabled=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
                viewport={'width': 1280, 'height': 900}
            )
            page = await context.new_page()

            url = f"https://www.facebook.com/search/posts/?q={query}"
            logger.debug(f"Navigating to Facebook URL: {url}")

            await page.goto(url, wait_until="networkidle", timeout=35000)
            await page.wait_for_timeout(5000)

            logger.debug("Attempting to handle initial pop-ups/overlays.")
            close_button_selectors = [
                'div[aria-label="Close dialog"]', 'div[aria-label="Close"]',
                'button[aria-label="Close"]', 'i[aria-label="Close"]',
                'button[aria-label="Not now"]', 'a[aria-label="Close"]',
                'div[aria-label*="cookie i"] button[value="1"]',
                'button[data-testid="cookie-policy-manage-dialog-accept-button"]'
            ]
            for _ in range(3):
                popup_closed_this_iteration = False
                for selector in close_button_selectors:
                    try:
                        buttons = await page.locator(selector).all()
                        for close_btn in reversed(buttons):
                            if await close_btn.is_visible(timeout=500) and await close_btn.is_enabled(timeout=500):
                                logger.info(f"Found potential overlay/cookie close button: {selector}. Clicking.")
                                await close_btn.click(timeout=1000, force=True) # Added force=True
                                await page.wait_for_timeout(1500)
                                popup_closed_this_iteration = True
                                break
                        if popup_closed_this_iteration: break
                    except Exception as e_popup:
                        logger.debug(f"Popup handler: Selector '{selector}' not found or error: {e_popup}")
                if not popup_closed_this_iteration: break

            login_selectors = 'input[name="email"], input#email, form[action*="login"], div[id="loginform"]'
            is_on_login_page = False
            try:
                if await page.locator(login_selectors).first.is_visible(timeout=3000):
                    is_on_login_page = True
            except Exception:
                is_on_login_page = False

            if is_on_login_page and ("facebook.com/login" in page.url.lower() or "facebook.com/checkpoint" in page.url.lower()):
                logger.warning("Facebook login page or checkpoint detected. Persistent context may not have an active session.")
                status_detail = "Login required or verification page encountered. Ensure configured profile is logged into Facebook."
                html_content = await page.content()
                screenshot_path = f"debug_facebook_{query.replace(' ','_')}_login_required.png"
                await page.screenshot(path=screenshot_path)
                # No early return here, let finally handle context close. Results will be empty.
            else:
                logger.info("Attempting to scrape posts from logged-in Facebook interface.")
                collected_posts_count = 0
                max_posts_to_collect = 15
                scroll_attempts = 0
                max_scroll_attempts = 12

                post_selector = 'div[role="article"]' # Simplified a bit, will rely on inner content checks
                seen_post_urls = set()

                while collected_posts_count < max_posts_to_collect and scroll_attempts < max_scroll_attempts:
                    logger.debug(f"Scroll attempt {scroll_attempts + 1}/{max_scroll_attempts}. Collected {collected_posts_count}/{max_posts_to_collect} posts.")
                    await page.wait_for_timeout(1000)

                    for selector in close_button_selectors: # Try closing popups again after scroll
                        try:
                            buttons = await page.locator(selector).all()
                            for close_btn in reversed(buttons):
                                if await close_btn.is_visible(timeout=300):
                                    logger.info(f"Closing pop-up with selector: {selector} (during scroll).")
                                    await close_btn.click(timeout=500, force=True)
                                    await page.wait_for_timeout(1000)
                                    break
                        except Exception: pass

                    post_elements = await page.query_selector_all(post_selector)
                    logger.debug(f"Found {len(post_elements)} potential post elements in current view.")

                    if not post_elements and scroll_attempts == 0:
                        no_results_text_found = False
                        try:
                            # More robust check for "no results" type messages
                            if await page.locator(':text-matches("No posts found", "i")').is_visible(timeout=1000) or \
                               await page.locator(':text-matches("End of results", "i")').is_visible(timeout=1000) or \
                               await page.locator(':text-matches("No results available", "i")').is_visible(timeout=1000):
                                no_results_text_found = True
                        except: pass

                        if no_results_text_found:
                            logger.info("Facebook search returned 'No posts found' or similar on initial load.")
                            status_detail = "Search successful, but no public posts found matching the query."
                        else:
                            logger.warning("No posts found on initial load and no explicit 'No posts found' message.")
                            status_detail = "No posts found on page; page may not have loaded correctly or is unexpected (e.g. content filter)."
                        # No early return, let the loop terminate naturally or by scroll attempts.
                        # This allows capturing final HTML/screenshot after attempts.
                        break # Break from while loop

                    new_posts_found_this_scroll = 0
                    for post_el in post_elements:
                        if collected_posts_count >= max_posts_to_collect:
                            break

                        post_data = {"text": "N/A", "author_name": "N/A", "author_url": "N/A", "timestamp": "N/A", "post_url": "N/A", "media_urls": []}
                        current_post_url = None
                        try:
                            # Post URL & Timestamp
                            time_link_el = await post_el.query_selector('a span[role="tooltip"] > span, a span[data-tooltip-content][aria-live="polite"], a[href*="/permalink/"], a[href*="/story.php"], a[href*="/watch/"], a[href*="/photo"], a[href*="/photos/"], a[href*="/videos/"]')
                            if time_link_el:
                                current_post_url = await time_link_el.get_attribute('href')
                                if current_post_url and not current_post_url.startswith("https://www.facebook.com"):
                                    current_post_url = "https://www.facebook.com" + current_post_url
                                post_data["post_url"] = current_post_url

                                # Timestamp often from the link's text content or a sibling/child time/abbr
                                ts_text = await time_link_el.inner_text()
                                if re.search(r'\d', ts_text): # If text itself contains numbers (likely a date)
                                     post_data["timestamp"] = ts_text.strip()
                                else: # Try to find a dedicated time element
                                    ts_el_alt = await post_el.query_selector('time[datetime], abbr[title]')
                                    if ts_el_alt: post_data["timestamp"] = await ts_el_alt.get_attribute('datetime') or await ts_el_alt.get_attribute('title')

                            if current_post_url and current_post_url in seen_post_urls:
                                continue

                            # Author Name & URL (often a link with strong text, or specific aria-label)
                            author_el = await post_el.query_selector('h2 a[href], h3 a[href], strong > a[href], a[aria-label*="Creator"], a[role="link"]:has(img[alt])') # Last one targets profile pics with links
                            if author_el:
                                post_data["author_name"] = (await author_el.inner_text()).strip()
                                if not post_data["author_name"]: # If inner_text is empty (e.g. only an image was in 'a')
                                    aria_label = await author_el.get_attribute("aria-label")
                                    if aria_label: post_data["author_name"] = aria_label.split(",")[0].strip() # Take first part of aria-label

                                post_data["author_url"] = await author_el.get_attribute('href')
                                if post_data["author_url"] and not post_data["author_url"].startswith("https://www.facebook.com"):
                                     post_data["author_url"] = "https://www.facebook.com" + post_data["author_url"]

                            # Post Text
                            text_elements = await post_el.query_selector_all('div[data-ad-preview="message"], div[data-ft] div[dir="auto"], div[data-testid="post_message"] div[dir="auto"]')
                            text_content_list = [await el.inner_text() for el in text_elements]
                            post_data["text"] = "\n".join(text_content_list).strip() if text_content_list else "N/A"

                            # Media
                            image_elements = await post_el.query_selector_all('img[src^="https://scontent."]:not([style*="height: 12px"]):not([style*="height: 16px"]):not([style*="height: 20px"])') # Exclude tiny icons
                            for img_el in image_elements:
                                src = await img_el.get_attribute('src')
                                if src: post_data["media_urls"].append(src)

                            video_elements = await post_el.query_selector_all('video')
                            if video_elements: post_data["media_urls"].append("Video content present")

                            if post_data.get("post_url") and (post_data.get("text") != "N/A" or post_data.get("media_urls")):
                                results.append(post_data)
                                if current_post_url: seen_post_urls.add(current_post_url)
                                collected_posts_count += 1
                                new_posts_found_this_scroll += 1
                                logger.debug(f"Collected Facebook post #{collected_posts_count}: {post_data.get('post_url')}")
                        except Exception as e_extract:
                            logger.error(f"Error extracting data from a Facebook post element: {e_extract}", exc_info=True)
                            continue

                    if collected_posts_count >= max_posts_to_collect:
                        status_detail = f"Reached max posts to collect ({max_posts_to_collect})."
                        logger.info(status_detail)
                        break

                    if new_posts_found_this_scroll == 0 and scroll_attempts > 2:
                        logger.info("No new posts found in recent scroll attempts. Ending scroll.")
                        status_detail = f"Collected {collected_posts_count} posts. No new posts found after extensive scrolling."
                        break

                    logger.debug(f"Scrolling down Facebook page (collected {collected_posts_count}/{max_posts_to_collect})...")
                    await page.mouse.wheel(0, 2000)
                    await page.wait_for_timeout(4000 + (scroll_attempts * 500))
                    scroll_attempts += 1

                if not results:
                    logger.info("No posts were successfully scraped from Facebook for this query.")
                    if status_detail == "Scraping process started.":
                        status_detail = "Search completed, but no posts found or extracted."
                elif status_detail == "Scraping process started.": # If results found but no other status set
                    status_detail = f"Successfully collected {len(results)} posts."

            logger.info(f"Finished Facebook scraping for '{query}'. {status_detail}")
            html_content = await page.content()
            await page.screenshot(path=screenshot_path) # Use the general path, might be updated if error occurred before this.
            logger.debug(f"Final screenshot for Facebook scrape saved to {screenshot_path}")

        except Exception as e_general:
            logger.error(f"A critical error occurred during Facebook scraping for query '{query}': {e_general}", exc_info=True)
            status_detail = f"Critical error during scraping: {type(e_general).__name__}"
            screenshot_path = f"debug_facebook_{query.replace(' ','_')}_critical_error.png" # Specific error screenshot
            try:
                if page and not page.is_closed(): # Ensure page object exists and is usable
                    current_html = await page.content()
                    if current_html: html_content = current_html
                    await page.screenshot(path=screenshot_path)
            except Exception as e_debug_critical:
                logger.error(f"Could not capture page content/screenshot during critical error: {e_debug_critical}", exc_info=True)
        finally:
            if context:
                try: await context.close()
                except Exception as ec: logger.error(f"Error closing context: {ec}", exc_info=True)

    return {
        "platform": "facebook",
        "query": query,
        "search_type": "posts",
        "results": results,
        "html": html_content,
        "screenshot": screenshot_path,
        "status_detail": status_detail
    }

if __name__ == '__main__':
    async def main():
        print("Facebook Scraper - Logged-in Test for POSTS")
        test_query = "sustainable gardening"

        print(f"\nAttempting to scrape Facebook for posts about '{test_query}'...")
        data = await scrape_facebook(test_query, "posts")

        print(f"\n--- Results for '{test_query}' ({len(data['results'])} posts) ---")
        if data['results']:
            for i, post in enumerate(data['results']):
                print(f"Post #{i+1}:")
                print(f"  Author: {post.get('author_name', 'N/A')} ({post.get('author_url', 'N/A')})")
                print(f"  Timestamp: {post.get('timestamp', 'N/A')}")
                print(f"  Post URL: {post.get('post_url', 'N/A')}")
                print(f"  Text: {post.get('text', 'N/A')[:100]}...")
                if post.get("media_urls"):
                    print(f"  Media URLs: {post['media_urls'][:2]}")
                print("-" * 20)
        else:
            print("No posts successfully extracted.")

        print(f"\nHTML content captured: {'Yes (length: ' + str(len(data['html'])) + ')' if data['html'] and not data['html'].startswith('Error:') else 'No or error'}")
        print(f"Screenshot saved at: {data['screenshot']}")
        print(f"Status Detail: {data.get('status_detail')}")
        print("--- Facebook Test Complete ---")

    asyncio.run(main())
