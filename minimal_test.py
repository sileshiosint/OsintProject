import asyncio
from playwright.async_api import async_playwright
import os

USER_DATA_DIR = os.path.expanduser("~/.config/google-chrome/Default_test_profile") # Use a fresh test profile
COMMON_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
HEADLESS_MODE = True

async def main():
    print("Minimal test: Starting Playwright...")
    # Ensure USER_DATA_DIR exists or Playwright might have issues
    if not os.path.exists(USER_DATA_DIR):
        print(f"Minimal test: Creating USER_DATA_DIR at {USER_DATA_DIR}")
        os.makedirs(USER_DATA_DIR, exist_ok=True)
    else:
        print(f"Minimal test: USER_DATA_DIR {USER_DATA_DIR} already exists.")

    context = None  # Initialize context to None for robust error handling in finally
    async with async_playwright() as p:
        print(f"Minimal test: Launching persistent context with USER_DATA_DIR: {USER_DATA_DIR}")
        try:
            context = await p.chromium.launch_persistent_context(
                USER_DATA_DIR,
                headless=HEADLESS_MODE,
                user_agent=COMMON_USER_AGENT,
                accept_downloads=True,
                ignore_https_errors=True,
                bypass_csp=True,
                # Adding some args that might help in restricted environments
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            print("Minimal test: Context launched. Creating page...")
            page = await context.new_page()
            print("Minimal test: Page created. Navigating to example.com...")
            await page.goto("http://example.com", timeout=15000) # Increased timeout slightly
            print(f"Minimal test: Navigated to example.com. Page title: {await page.title()}")
            await page.close()
            print("Minimal test: Page closed.")
            # Context is closed by the 'async with context:' block if used,
            # but since we are not using that pattern here for launch_persistent_context,
            # we close it manually in finally.
        except Exception as e:
            print(f"Minimal test: An error occurred: {type(e).__name__}: {e}")
        finally:
            if context:
                print("Minimal test: Attempting to close context in finally block...")
                await context.close()
                print("Minimal test: Context closed in finally block.")
            else:
                print("Minimal test: Context was None, no need to close in finally.")


    print("Minimal test: Playwright operations finished.")

if __name__ == "__main__":
    print("Minimal test: Running main...")
    asyncio.run(main())
    print("Minimal test: Script finished.")
