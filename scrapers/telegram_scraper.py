import asyncio
from playwright.async_api import async_playwright
from scrapers.config import USER_DATA_DIR, COMMON_USER_AGENT, HEADLESS_MODE
import os

async def scrape_telegram(query: str, search_type: str):
    """
    Attempts to scrape Telegram Web using a persistent browser context.
    Assumes the user is logged in. It will try to perform a search and extract messages.
    Handles both /k/ and /a/ versions of Telegram Web.

    Args:
        query: The search query.
        search_type: Can be 'k' or 'a' to specify the Telegram Web version.
                     Defaults to 'k' if not 'a'.

    Returns:
        A dictionary containing scraped data.
    """
    results = []
    html_content = "Error: Playwright page content not captured."
    telegram_version = 'k' if search_type != 'a' else 'a'
    url = f"https://web.telegram.org/{telegram_version}/"
    screenshot_path = f"telegram_search_{telegram_version}_{query.replace(' ','_')}.png"

    if not os.path.exists(USER_DATA_DIR):
        print(f"Telegram Scraper: Creating USER_DATA_DIR at {USER_DATA_DIR}")
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
            viewport={'width': 1366, 'height': 768} # Common desktop viewport
        )
        page = await context.new_page()

        try:
            print(f"Navigating to Telegram Web ({telegram_version}) URL: {url}")
            await page.goto(url, wait_until="networkidle", timeout=35000) # networkidle might be better for JS-heavy apps
            await page.wait_for_timeout(5000) # Allow app to initialize

            # --- Logged-in Check ---
            logged_in_selector_k = 'div.ChatList' # Main chat list container for K version
            logged_in_selector_a = '#column-left .chatlist-top .chatlist' # Main chat list for A version
            qr_code_selector_k = 'canvas[aria-label="Scan QR code"]'
            login_page_indicator_a = 'iframe[src*="oauth.telegram.org"]' # For /a/ version login

            is_logged_in = False
            if telegram_version == 'k':
                if await page.locator(logged_in_selector_k).count() > 0 and await page.locator(qr_code_selector_k).count() == 0:
                    is_logged_in = True
            elif telegram_version == 'a':
                if await page.locator(logged_in_selector_a).count() > 0 and await page.locator(login_page_indicator_a).count() == 0:
                    is_logged_in = True

            if not is_logged_in:
                print(f"Telegram Web ({telegram_version}): Not logged in or login page still visible. Capturing page and exiting.")
                html_content = await page.content()
                screenshot_path = f"telegram_{telegram_version}_login_page_detected.png"
                await page.screenshot(path=screenshot_path)
                # No 'finally' here for closing, outer finally will handle it.
                return {
                    "platform": "telegram", "query": query, "search_type": search_type,
                    "results": [], "html": html_content, "screenshot": screenshot_path,
                    "notes": "Login required or session not active."
                }

            print(f"Telegram Web ({telegram_version}): Logged-in interface detected. Proceeding with search.")

            # --- Search Implementation (highly speculative and version-dependent) ---
            search_input_selector_k = 'input[placeholder*="Search"]' # Common placeholder for K
            search_input_selector_a = 'input[placeholder="Search"]' # Common for A (often in an RPInput custom element)

            search_input_selector = search_input_selector_k if telegram_version == 'k' else search_input_selector_a

            print(f"Attempting to find search input with selector: {search_input_selector}")
            search_input = page.locator(search_input_selector).first
            await search_input.wait_for(state="visible", timeout=15000)

            print(f"Search input found. Typing query: '{query}'")
            await search_input.fill(query)
            await page.wait_for_timeout(1000) # Wait for potential debouncing or auto-suggestions
            await search_input.press("Enter")
            print("Search submitted. Waiting for results...")
            await page.wait_for_timeout(5000) # Allow time for search results to load

            # --- Data Extraction from Search Results (even more speculative) ---
            # Selectors will vary wildly. This is a generic attempt.
            # K version often has results in a .search-results-container or similar.
            # A version might have .search-results .ListItem.
            results_container_selector_k = '.search-results-list, .SearchPeers' # For K version
            result_item_selector_k = 'div.ListItem, a.ListItem'

            results_container_selector_a = '.search-results-container .chatlist, .search-results-list' # For A version
            result_item_selector_a = '.ListItem, .chatlist-item'

            results_container_selector = results_container_selector_k if telegram_version == 'k' else results_container_selector_a
            result_item_selector = result_item_selector_k if telegram_version == 'k' else result_item_selector_a

            print(f"Waiting for search results container: {results_container_selector}")
            await page.wait_for_selector(results_container_selector, timeout=15000, state="visible")

            collected_items_count = 0
            max_items_to_collect = 15
            scroll_attempts = 0
            max_scroll_attempts = 10

            # Attempt to close any pop-ups (e.g., "New messages from X")
            close_popup_selector = 'button[aria-label="Close"], div[aria-label="Close"]'

            while collected_items_count < max_items_to_collect and scroll_attempts < max_scroll_attempts:
                try:
                    close_buttons = await page.query_selector_all(close_popup_selector)
                    for btn in close_buttons:
                        if await btn.is_visible():
                            print("Closing a potential pop-up.")
                            await btn.click(timeout=500)
                            await page.wait_for_timeout(500)
                except Exception: pass

                search_result_elements = await page.query_selector_all(result_item_selector)
                print(f"Found {len(search_result_elements)} result items in current view (attempt {scroll_attempts + 1}).")

                if not search_result_elements and collected_items_count == 0:
                    print("No search results items found.")
                    break

                found_new_item_in_scroll = False
                for item_el in search_result_elements:
                    if collected_items_count >= max_items_to_collect: break

                    item_data = {"text_snippet": "N/A", "sender_chat_name": "N/A", "timestamp": "N/A", "link": "N/A"}
                    try:
                        # Text Snippet (very generic)
                        # For K: .message-text, .title > span, .peer-title. For A: .message, .title, .name
                        text_el = await item_el.query_selector('.message, .message-text, .title > span, .peer-title, .name, .title')
                        if text_el: item_data["text_snippet"] = (await text_el.inner_text()).strip()

                        # Sender/Chat Name (also very generic)
                        # Often the same as text_el or a sibling/parent with similar class names
                        name_el = await item_el.query_selector('.title, .peer-title, .name, h3, strong')
                        if name_el: item_data["sender_chat_name"] = (await name_el.inner_text()).strip()

                        # Timestamp (if available)
                        time_el = await item_el.query_selector('time, .date, .time')
                        if time_el: item_data["timestamp"] = await time_el.get_attribute('datetime') or (await time_el.inner_text()).strip()

                        # Link (if the item itself is a link)
                        if await item_el.evaluate_handle("element => element.tagName === 'A'"):
                            item_data["link"] = await item_el.get_attribute('href')
                        else: # Try to find a link inside
                            link_el = await item_el.query_selector('a[href]')
                            if link_el: item_data["link"] = await link_el.get_attribute('href')

                        if item_data["link"] and not item_data["link"].startswith("http"):
                            item_data["link"] = url + item_data["link"] # Make it absolute if relative

                        # Add if some useful data was extracted
                        if item_data["text_snippet"] != "N/A" or item_data["sender_chat_name"] != "N/A":
                             # Simple duplicate check based on text and name to avoid very similar entries from UI changes
                            is_duplicate = any(
                                r.get("text_snippet") == item_data["text_snippet"] and \
                                r.get("sender_chat_name") == item_data["sender_chat_name"] for r in results
                            )
                            if not is_duplicate:
                                results.append(item_data)
                                collected_items_count += 1
                                found_new_item_in_scroll = True
                                print(f"Collected search result #{collected_items_count}: {item_data['sender_chat_name']} - {item_data['text_snippet'][:30]}...")
                    except Exception as e_extract_item:
                        print(f"Error extracting data from a search result item: {e_extract_item}")
                        continue

                if collected_items_count < max_items_to_collect:
                    if not found_new_item_in_scroll and scroll_attempts > 0 : # If no new items after first scroll, stop
                         print("No new items found in last scroll. Ending.")
                         break
                    print(f"Scrolling search results (collected {collected_items_count}/{max_items_to_collect})...")
                    # Scrolling within the results container if possible, otherwise page scroll
                    results_pane = page.locator(results_container_selector).first
                    if results_pane:
                        await results_pane.evaluate('node => node.scrollTop = node.scrollHeight')
                    else:
                        await page.mouse.wheel(0, 1000) # Fallback to page scroll
                    await page.wait_for_timeout(2500 + scroll_attempts * 500)
                    scroll_attempts += 1
                else:
                    print("Reached max items to collect or no more new items.")
                    break

            if not results: print("No usable search results extracted.")
            html_content = await page.content()
            await page.screenshot(path=screenshot_path)
            print(f"Final screenshot for Telegram search saved to {screenshot_path}")

        except Exception as e_general:
            error_msg = f"An error occurred: {type(e_general).__name__}: {e_general}"
            print(error_msg)
            screenshot_path = f"error_telegram_{telegram_version}_{query.replace(' ','_')}.png"
            try:
                if page and not page.is_closed():
                    html_content_error = await page.content()
                    if html_content_error and html_content_error.strip() != "": html_content = html_content_error
                    await page.screenshot(path=screenshot_path)
                    print(f"Error screenshot saved to {screenshot_path}")
            except Exception as e_debug:
                print(f"Could not capture page content/screenshot during error handling: {e_debug}")
        finally:
            if context:
                try: await context.close()
                except Exception as ec: print(f"Error closing context: {ec}")

    return {
        "platform": "telegram", "query": query, "search_type": search_type,
        "results": results, "html": html_content, "screenshot": screenshot_path
    }

if __name__ == '__main__':
    async def main():
        print("Telegram Scraper - Logged-in Search Test")
        # NOTE: This test assumes a logged-in session via persistent context.
        # Set HEADLESS_MODE=False in scrapers/config.py for easier debugging if needed.

        test_query_k = "Playwright"
        print(f"\nAttempting to scrape Telegram Web /k/ for '{test_query_k}'...")
        data_k = await scrape_telegram(query=test_query_k, search_type="k")
        print(f"\n--- Telegram /k/ Results for '{test_query_k}' ({len(data_k['results'])} items) ---")
        if data_k['results']:
            for i, item in enumerate(data_k['results'][:3]): # Print first 3 items
                print(f"Item #{i+1}: Name: {item.get('sender_chat_name')}, Text: {item.get('text_snippet', '')[:50]}..., Time: {item.get('timestamp')}, Link: {item.get('link')}")
        else: print("No results extracted for /k/ version.")
        print(f"Screenshot: {data_k['screenshot']}")
        print("-" * 30)

        test_query_a = "AsyncAPI"
        print(f"\nAttempting to scrape Telegram Web /a/ for '{test_query_a}'...")
        data_a = await scrape_telegram(query=test_query_a, search_type="a")
        print(f"\n--- Telegram /a/ Results for '{test_query_a}' ({len(data_a['results'])} items) ---")
        if data_a['results']:
            for i, item in enumerate(data_a['results'][:3]):
                 print(f"Item #{i+1}: Name: {item.get('sender_chat_name')}, Text: {item.get('text_snippet', '')[:50]}..., Time: {item.get('timestamp')}, Link: {item.get('link')}")
        else: print("No results extracted for /a/ version.")
        print(f"Screenshot: {data_a['screenshot']}")
        print("--- Test Complete ---")

    asyncio.run(main())
