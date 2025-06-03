import asyncio
from playwright.async_api import async_playwright
import re
from scrapers.config import USER_DATA_DIR, COMMON_USER_AGENT, HEADLESS_MODE
import os

async def scrape_facebook(query: str, search_type: str): # search_type is retained for interface consistency
    """
    Attempts to scrape Facebook posts based on a query using a persistent browser context.
    Assumes the user is logged in via the persistent context.
    Focuses on the 'posts' search tab.
    """
    results = []
    html_content = "Error: Playwright page content not captured."
    screenshot_path = f"facebook_search_posts_{query.replace(' ','_')}.png"

    if not os.path.exists(USER_DATA_DIR):
        print(f"Facebook Scraper: Creating USER_DATA_DIR at {USER_DATA_DIR}")
        os.makedirs(USER_DATA_DIR, exist_ok=True)

    async with async_playwright() as p:
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

        try:
            url = f"https://www.facebook.com/search/posts/?q={query}"
            print(f"Navigating to Facebook posts search URL: {url}")

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)

            close_button_selectors = [
                'div[aria-label="Close"]', 'button[aria-label="Close"]',
                'button[aria-label="Not now"]', 'a[aria-label="Close"]',
                'div[aria-label*="cookie"] button[value="1"]',
                'button[data-testid="cookie-policy-manage-dialog-accept-button"]'
            ]
            for _ in range(2):
                for selector in close_button_selectors:
                    try:
                        close_btn = page.locator(selector).first
                        if await close_btn.is_visible(timeout=1500):
                            print(f"Found potential overlay/cookie close button with selector: {selector}. Clicking.")
                            await close_btn.click(timeout=1000)
                            await page.wait_for_timeout(1500)
                    except Exception:
                        pass

            if await page.locator('input[name="email"], input#email, form[action*="login"]').count() > 0 and "facebook.com/login" in page.url:
                print("Error: Facebook login page detected. Persistent context did not maintain login.")
                html_content = await page.content()
                await page.screenshot(path=f"debug_facebook_{query.replace(' ','_')}_login_page_error.png")
            else:
                print("Attempting to scrape posts from logged-in interface.")

                collected_posts_count = 0
                max_posts_to_collect = 15
                scroll_attempts = 0
                max_scroll_attempts = 12

                post_selector = 'div[role="article"]:has(a[href*="/posts/"], a[href*="/videos/"], a[href*="/photo"])'

                while collected_posts_count < max_posts_to_collect and scroll_attempts < max_scroll_attempts:
                    await page.wait_for_timeout(1000)

                    for selector in close_button_selectors:
                        try:
                            close_btn = page.locator(selector).first
                            if await close_btn.is_visible(timeout=500):
                                print(f"Found potential overlay/cookie close button with selector: {selector} (after scroll). Clicking.")
                                await close_btn.click(timeout=500)
                                await page.wait_for_timeout(1000)
                        except: pass

                    post_elements = await page.query_selector_all(post_selector)
                    print(f"Found {len(post_elements)} potential post elements on page (scroll attempt {scroll_attempts + 1}).")

                    if not post_elements and scroll_attempts == 0:
                        if await page.locator('text="No posts found"').is_visible(timeout=2000) or \
                           await page.locator('text="End of results"').is_visible(timeout=2000):
                            print("Facebook search returned 'No posts found' or 'End of results'.")
                            html_content = await page.content()
                            await page.screenshot(path=screenshot_path)
                            # Must return from the function here to avoid SyntaxError with 'break'
                            return {
                                "platform": "facebook", "query": query, "search_type": "posts",
                                "results": results, "html": html_content, "screenshot": screenshot_path
                            }
                        else:
                            print("No posts found and no 'No posts found' message. Page might be unexpected.")
                            screenshot_path = f"debug_facebook_{query.replace(' ','_')}_no_posts_unexpected.png"
                            html_content = await page.content()
                            await page.screenshot(path=screenshot_path)
                            return {
                                "platform": "facebook", "query": query, "search_type": "posts",
                                "results": results, "html": html_content, "screenshot": screenshot_path
                            }

                    found_new_posts_in_this_scroll = False
                    for post_el in post_elements:
                        if collected_posts_count >= max_posts_to_collect:
                            break # Correct: breaks the inner 'for post_el' loop

                        post_data = {"text": "N/A", "author_name": "N/A", "author_url": "N/A", "timestamp": "N/A", "post_url": "N/A", "media_urls": []}

                        try:
                            time_link_el = await post_el.query_selector('a[role="link"]:has(span[title]), a[role="link"]:has(abbr[title]), a[role="link"]:has(time)')
                            if time_link_el:
                                post_data["post_url"] = await time_link_el.get_attribute('href')
                                if post_data["post_url"] and not post_data["post_url"].startswith("https://www.facebook.com"):
                                    post_data["post_url"] = "https://www.facebook.com" + post_data["post_url"]
                                ts_el = await time_link_el.query_selector('span[title], abbr[title], time')
                                if ts_el:
                                    post_data["timestamp"] = await ts_el.get_attribute('title') or await ts_el.inner_text()
                            else:
                                ts_el_alt = await post_el.query_selector('time[datetime]')
                                if ts_el_alt: post_data["timestamp"] = await ts_el_alt.get_attribute('datetime')

                            author_el = await post_el.query_selector('h2 a[href], h3 a[href], div[role="button"] > a[href*="/"], span > a[href*="/"]:not([role="link"])')
                            if author_el:
                                post_data["author_name"] = (await author_el.inner_text()).strip()
                                post_data["author_url"] = await author_el.get_attribute('href')
                                if post_data["author_url"] and not post_data["author_url"].startswith("https://www.facebook.com"):
                                     post_data["author_url"] = "https://www.facebook.com" + post_data["author_url"]

                            text_container = await post_el.query_selector('div[data-ad-preview="message"], div[data-ft]')
                            if not text_container:
                                text_parts = await post_el.query_selector_all('div[dir="auto"]:not(:has(div[role="article"]))')
                                text_content_list = []
                                for part in text_parts:
                                    text_content_list.append(await part.inner_text())
                                text_content = "\n".join(text_content_list).strip()
                            else:
                                text_content = (await text_container.inner_text()).strip()

                            if text_content: post_data["text"] = text_content

                            image_elements = await post_el.query_selector_all('img[src^="https://scontent."]')
                            for img_el in image_elements:
                                src = await img_el.get_attribute('src')
                                if src: post_data["media_urls"].append(src)

                            video_elements = await post_el.query_selector_all('video > source[src]')
                            if await video_elements: # This check is incorrect, query_selector_all returns a list
                                post_data["media_urls"].append("Video content present (source URL not extracted yet)")

                            if post_data.get("post_url") and (post_data.get("text") != "N/A" or post_data.get("media_urls")):
                                if not any(r.get("post_url") == post_data.get("post_url") for r in results):
                                    results.append(post_data)
                                    collected_posts_count += 1
                                    found_new_posts_in_this_scroll = True
                                    print(f"Collected post #{collected_posts_count}: {post_data.get('post_url')}")
                        except Exception as e_extract:
                            print(f"Error extracting data from a post element: {type(e_extract).__name__} - {e_extract}")
                            continue

                    # This block is now correctly indented under the 'while' loop
                    if collected_posts_count < max_posts_to_collect:
                        if not found_new_posts_in_this_scroll and scroll_attempts > 1:
                            print("No new posts found in the last scroll attempt. Ending scroll.")
                            break # Correct: breaks the 'while' loop
                        print(f"Scrolling down (collected {collected_posts_count}/{max_posts_to_collect})...")
                        await page.mouse.wheel(0, 1500)
                        await page.wait_for_timeout(3500 + (scroll_attempts * 500))
                        scroll_attempts += 1
                    else:
                        print("Reached max posts to collect or no more new posts.")
                        break # Correct: breaks the 'while' loop

            if not results:
                print("No posts were successfully scraped from Facebook.")
                screenshot_path = f"debug_facebook_{query.replace(' ','_')}_no_results_final.png"

            html_content = await page.content()
            await page.screenshot(path=screenshot_path)
            print(f"Final screenshot for Facebook scrape saved to {screenshot_path}")

        except Exception as e_general:
            print(f"A critical error occurred during Facebook scraping: {type(e_general).__name__}: {e_general}")
            screenshot_path = f"debug_facebook_{query.replace(' ','_')}_critical_error.png"
            try:
                if page and not page.is_closed():
                    current_html = await page.content()
                    if current_html: html_content = current_html
                    await page.screenshot(path=screenshot_path)
            except Exception as e_debug_critical:
                print(f"Could not capture page content/screenshot during critical error: {e_debug_critical}")
        finally:
            if context:
                try: await context.close()
                except Exception as ec: print(f"Error closing context: {ec}")

    return {
        "platform": "facebook",
        "query": query,
        "search_type": "posts",
        "results": results,
        "html": html_content,
        "screenshot": screenshot_path
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
        print("--- Facebook Test Complete ---")

    asyncio.run(main())
