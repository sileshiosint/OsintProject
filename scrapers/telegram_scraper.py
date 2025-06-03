import asyncio
from playwright.async_api import async_playwright
from scrapers.config import USER_DATA_DIR, COMMON_USER_AGENT, HEADLESS_MODE
import os
import logging

logger = logging.getLogger(__name__)

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
    status_detail = "Scraping process started."
    telegram_version = 'k' if search_type != 'a' else 'a'
    url = f"https://web.telegram.org/{telegram_version}/"
    # Make screenshot path more specific for search attempts vs login page captures
    screenshot_path = f"telegram_search_{telegram_version}_{query.replace(' ','_') if query else 'no_query'}.png"

    logger.info(f"Starting Telegram scraper for query: '{query}', version: '{telegram_version}'")

    if not os.path.exists(USER_DATA_DIR):
        logger.info(f"Creating USER_DATA_DIR for Telegram at {USER_DATA_DIR}")
        os.makedirs(USER_DATA_DIR, exist_ok=True)
    # else:
    #    logger.debug(f"USER_DATA_DIR {USER_DATA_DIR} already exists.")

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
                java_script_enabled=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
                viewport={'width': 1366, 'height': 768}
            )
            page = await context.new_page()

            logger.debug(f"Navigating to Telegram Web ({telegram_version}) URL: {url}")
            await page.goto(url, wait_until="networkidle", timeout=35000)
            await page.wait_for_timeout(5000)

            logged_in_selector_k = 'div.ChatList'
            logged_in_selector_a_main_ui = '#ShellMETTLE div[data-layer-context-id]' # More reliable than chatlist for /a/ initial load
            qr_code_selector_k = 'canvas[aria-label="Scan QR code"]'
            login_page_indicator_a = 'iframe[src*="oauth.telegram.org"]'

            is_logged_in = False
            logger.debug(f"Checking login status for Telegram {telegram_version}...")
            if telegram_version == 'k':
                if await page.locator(logged_in_selector_k).count() > 0 and await page.locator(qr_code_selector_k).count() == 0:
                    is_logged_in = True
            elif telegram_version == 'a':
                if await page.locator(logged_in_selector_a_main_ui).count() > 0 and await page.locator(login_page_indicator_a).count() == 0 :
                    is_logged_in = True

            if not is_logged_in:
                logger.warning(f"Telegram Web ({telegram_version}): Not logged in or login page still visible.")
                status_detail = f"Login required for Telegram Web {telegram_version}. Ensure profile is logged in."
                html_content = await page.content()
                screenshot_path = f"telegram_{telegram_version}_login_page_detected.png"
                await page.screenshot(path=screenshot_path)
                # No early return, finally block handles context close
            else:
                logger.info(f"Telegram Web ({telegram_version}): Logged-in interface detected. Proceeding with search for '{query}'.")

                search_input_selector_k = 'input[placeholder*="Search"]'
                search_input_selector_a = 'input[placeholder="Search"]' # Or specific ID like #telegram-search-input

                search_input_selector = search_input_selector_k if telegram_version == 'k' else search_input_selector_a

                logger.debug(f"Attempting to find search input with selector: {search_input_selector}")

                if telegram_version == 'a':
                    search_button_a = page.locator('#telegram-search-button, button[aria-label="Search"]')
                    if await search_button_a.count() > 0 and await search_button_a.first.is_visible(timeout=5000):
                        logger.debug("Telegram /a/: Clicking search button to reveal input.")
                        await search_button_a.first.click()
                        await page.wait_for_timeout(500)
                    else:
                         logger.debug("Telegram /a/: Search button not found or not visible, trying direct input.")

                search_input = page.locator(search_input_selector).first
                await search_input.wait_for(state="visible", timeout=15000)

                logger.info(f"Search input found. Typing query: '{query}'")
                await search_input.fill(query)
                await page.wait_for_timeout(1000)
                await search_input.press("Enter")
                logger.info("Search submitted. Waiting for results...")
                await page.wait_for_timeout(7000) # Increased wait for results

                results_container_selector_k = '.search-results-list, .SearchPeers, .dialog-search-list'
                result_item_selector_k = 'div.ListItem, a.ListItem, .search-result'

                results_container_selector_a = '.search-results-container .chatlist, .search-results-list, #search-results-container ul, .ChatFoldersSchema > .chatlist'
                result_item_selector_a = '.ListItem, .chatlist-item, ul > .ListItem-button, .search-result-user, .search-result-message'

                results_container_selector = results_container_selector_k if telegram_version == 'k' else results_container_selector_a
                result_item_selector = result_item_selector_k if telegram_version == 'k' else result_item_selector_a

                logger.debug(f"Waiting for search results container: {results_container_selector}")
                try:
                    await page.locator(results_container_selector).first.wait_for(state="visible", timeout=20000)
                    logger.debug("Search results container found.")
                except Exception as e_no_results_container:
                    logger.warning(f"Search results container not found: {e_no_results_container}. Possibly no results or UI change.")
                    status_detail = f"No search results container found for query '{query}', or UI has changed."

                if status_detail == "Scraping process started.": # Only proceed if no major issue so far
                    collected_items_count = 0
                    max_items_to_collect = 15
                    scroll_attempts = 0
                    max_scroll_attempts = 10
                    seen_item_identifiers = set()

                    close_popup_selector = 'button[aria-label="Close"], div[aria-label="Close"], button.popup-close'

                    while collected_items_count < max_items_to_collect and scroll_attempts < max_scroll_attempts:
                        try:
                            buttons = await page.query_selector_all(close_popup_selector)
                            for btn in reversed(buttons):
                                if await btn.is_visible(timeout=300):
                                    logger.info("Closing a potential pop-up.")
                                    await btn.click(timeout=500, force=True)
                                    await page.wait_for_timeout(500)
                        except Exception: pass

                        search_result_elements = await page.query_selector_all(result_item_selector)
                        logger.debug(f"Found {len(search_result_elements)} result items in current view (attempt {scroll_attempts + 1}).")

                        if not search_result_elements and collected_items_count == 0 and scroll_attempts == 0:
                            logger.info(f"No search results items found on initial load after search for '{query}'.")
                            status_detail = f"Search for '{query}' yielded no initial results."
                            break

                        new_items_found_this_scroll = 0
                        for item_el in search_result_elements:
                            if collected_items_count >= max_items_to_collect: break

                            item_data = {"text_snippet": "N/A", "sender_chat_name": "N/A", "timestamp": "N/A", "link": "N/A"}
                            try:
                                text_el = await item_el.query_selector('.message, .message-text, .title > span, .peer-title, .name, .title, .dialog-title span, .search-result-text')
                                if text_el: item_data["text_snippet"] = (await text_el.inner_text()).strip()

                                name_el = await item_el.query_selector('.title, .peer-title, .name, h3, strong, .dialog-title strong, .search-result-title')
                                if name_el: item_data["sender_chat_name"] = (await name_el.inner_text()).strip()

                                time_el = await item_el.query_selector('time, .date, .time, .dialog-date')
                                if time_el: item_data["timestamp"] = await time_el.get_attribute('datetime') or (await time_el.inner_text()).strip()

                                link_val = None
                                if await item_el.evaluate_handle("element => element.tagName === 'A'"):
                                    link_val = await item_el.get_attribute('href')
                                else:
                                    link_el_child = await item_el.query_selector('a[href]')
                                    if link_el_child: link_val = await link_el_child.get_attribute('href')

                                if link_val:
                                    if not link_val.startswith("http") and ("#" in link_val or link_val.startswith("?")):
                                        item_data["link"] = f"https://web.telegram.org/{telegram_version}/{link_val}"
                                    elif link_val.startswith("tg://"):
                                         item_data["link"] = link_val
                                    else:
                                        item_data["link"] = link_val

                                item_identifier = f"{item_data['sender_chat_name']}_{item_data['text_snippet'][:50]}_{item_data['timestamp']}"
                                if item_identifier in seen_item_identifiers and item_identifier != "N/A_N/A_N/A": # Avoid flagging all N/A as duplicates
                                    continue

                                if item_data["text_snippet"] != "N/A" or item_data["sender_chat_name"] != "N/A":
                                    results.append(item_data)
                                    if item_identifier != "N/A_N/A_N/A": seen_item_identifiers.add(item_identifier)
                                    collected_items_count += 1
                                    new_items_found_this_scroll += 1
                                    logger.debug(f"Collected Telegram item #{collected_items_count}: {item_data['sender_chat_name']} - {item_data['text_snippet'][:30]}...")
                            except Exception as e_extract_item:
                                logger.error(f"Error extracting data from a Telegram search item: {e_extract_item}", exc_info=True)
                                continue

                        if collected_items_count >= max_items_to_collect:
                            status_detail = f"Reached max items to collect ({max_items_to_collect})."
                            logger.info(status_detail)
                            break

                        if new_items_found_this_scroll == 0 and scroll_attempts > 1 :
                             logger.info("No new items found in last scroll. Ending Telegram search scroll.")
                             if status_detail == "Scraping process started.": status_detail = f"Collected {collected_items_count} items. No new items after scrolling."
                             break

                        logger.debug(f"Scrolling Telegram search results (collected {collected_items_count}/{max_items_to_collect})...")
                        results_pane_loc = page.locator(results_container_selector).first
                        if await results_pane_loc.count() > 0: # Check if locator found anything
                            await results_pane_loc.evaluate('node => node.scrollTop = node.scrollHeight')
                        else: # Fallback if specific results pane not found or not scrollable
                            await page.mouse.wheel(0, 1000)
                        await page.wait_for_timeout(3000 + scroll_attempts * 500) # Increased base timeout
                        scroll_attempts += 1

                    if not results:
                        logger.info("No usable search results extracted from Telegram.")
                        if status_detail == "Scraping process started.": status_detail = f"Search for '{query}' on Telegram {telegram_version} yielded no extractable results."
                    elif status_detail == "Scraping process started.":
                         status_detail = f"Successfully collected {len(results)} items from Telegram {telegram_version} for query '{query}'."

            html_content = await page.content()
            await page.screenshot(path=screenshot_path)
            logger.debug(f"Final screenshot for Telegram ({url}) saved to {screenshot_path}")

        except Exception as e_general:
            error_msg = f"An error occurred during Telegram scraping: {type(e_general).__name__}: {e_general}"
            logger.error(error_msg, exc_info=True)
            status_detail = error_msg # This will be the main status detail
            # Update screenshot path to reflect error state if not already login related
            if "login_page_detected" not in screenshot_path:
                 screenshot_path = f"error_telegram_{telegram_version}_{query.replace(' ','_') if query else 'no_query'}_{type(e_general).__name__}.png"
            try:
                if page and not page.is_closed():
                    html_content_error = await page.content()
                    if html_content_error and html_content_error.strip() != "": html_content = html_content_error
                    await page.screenshot(path=screenshot_path) # Use updated error screenshot path
                    logger.debug(f"Error screenshot saved to {screenshot_path}")
            except Exception as e_debug:
                logger.error(f"Could not capture page content/screenshot during error handling: {e_debug}", exc_info=True)
        finally:
            if context:
                try: await context.close()
                except Exception as ec: logger.error(f"Error closing context: {ec}", exc_info=True)
            logger.debug("Playwright context closed for Telegram.")

    return {
        "platform": "telegram", "query": query, "search_type": search_type,
        "results": results, "html": html_content, "screenshot": screenshot_path,
        "status_detail": status_detail
    }

if __name__ == '__main__':
    async def main():
        print("Telegram Scraper - Logged-in Search Test")
        # NOTE: This test assumes a logged-in session via persistent context.
        # Set HEADLESS_MODE=False in scrapers/config.py for easier debugging if needed.

        test_query_k = "Playwright testing"
        print(f"\nAttempting to scrape Telegram Web /k/ for '{test_query_k}'...")
        data_k = await scrape_telegram(query=test_query_k, search_type="k")
        print(f"\n--- Telegram /k/ Results for '{test_query_k}' ({len(data_k['results'])} items) ---")
        if data_k['results']:
            for i, item in enumerate(data_k['results'][:3]):
                print(f"Item #{i+1}: Name: {item.get('sender_chat_name')}, Text: {item.get('text_snippet', '')[:50]}..., Time: {item.get('timestamp')}, Link: {item.get('link')}")
        else: print(f"No results extracted for /k/ version. Status: {data_k.get('status_detail')}")
        print(f"Screenshot: {data_k['screenshot']}")
        print("-" * 30)

        test_query_a = "Web automation"
        print(f"\nAttempting to scrape Telegram Web /a/ for '{test_query_a}'...")
        data_a = await scrape_telegram(query=test_query_a, search_type="a")
        print(f"\n--- Telegram /a/ Results for '{test_query_a}' ({len(data_a['results'])} items) ---")
        if data_a['results']:
            for i, item in enumerate(data_a['results'][:3]):
                 print(f"Item #{i+1}: Name: {item.get('sender_chat_name')}, Text: {item.get('text_snippet', '')[:50]}..., Time: {item.get('timestamp')}, Link: {item.get('link')}")
        else: print(f"No results extracted for /a/ version. Status: {data_a.get('status_detail')}")
        print(f"Screenshot: {data_a['screenshot']}")
        print("--- Test Complete ---")

    asyncio.run(main())
