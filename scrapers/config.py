import os
import logging

logger = logging.getLogger(__name__)

# Path to existing user browser session
DEFAULT_USER_DATA_DIR = os.path.expanduser("~/.config/google-chrome/Default")
USER_DATA_DIR_ENV_VAR = "CHROME_USER_DATA_DIR"
USER_DATA_DIR = os.getenv(USER_DATA_DIR_ENV_VAR, DEFAULT_USER_DATA_DIR)

if USER_DATA_DIR == DEFAULT_USER_DATA_DIR and not os.getenv(USER_DATA_DIR_ENV_VAR):
    logger.warning(
        f"{USER_DATA_DIR_ENV_VAR} environment variable not set, "
        f"defaulting to: {DEFAULT_USER_DATA_DIR}. "
        "Ensure this profile is configured with necessary logins for scrapers to work."
    )
else:
    logger.info(f"Using Chrome user data directory from {USER_DATA_DIR_ENV_VAR}: {USER_DATA_DIR}")


# Define a common user agent to be used by all scrapers
COMMON_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"

# Headless mode for browser automation. Set to False for interactive debugging or initial login.
# Can be overridden by environment variable HEADLESS_MODE (True/False)
_headless_env = os.environ.get("HEADLESS_MODE", "True")
HEADLESS_MODE = _headless_env.upper() == "TRUE"

logger.info(f"Playwright HEADLESS_MODE set to: {HEADLESS_MODE}")
