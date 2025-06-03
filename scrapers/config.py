import os

# Path to existing user browser session
# Using CHROME_USER_DATA_DIR for clarity and a more specific default.
USER_DATA_DIR = os.getenv("CHROME_USER_DATA_DIR", os.path.expanduser("~/.config/google-chrome/Default"))

# Define a common user agent to be used by all scrapers
COMMON_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"

# Headless mode for browser automation. Set to False for interactive debugging or initial login.
HEADLESS_MODE = True
