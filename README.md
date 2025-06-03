# OSINT Social Media Search Tool

A web-based tool for performing searches across multiple social media platforms using browser automation.

## Prerequisites

- Python 3.8+
- pip (Python package installer)
- Google Chrome browser installed (the tool is configured to use it)

## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
    *(Replace `<repository_url>` and `<repository_directory>` with actual values)*

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    Ensure your `requirements.txt` file includes at least the following (create one if it doesn't exist):
    ```
    Flask
    Flask-SQLAlchemy
    psycopg2-binary
    playwright
    ```
    Then run:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Playwright Browser Drivers:**
    This tool is configured to use Chrome.
    ```bash
    playwright install chrome
    ```

## Configuration (Crucial for Scraping)

This tool uses Playwright with a persistent browser context to interact with social media platforms as a logged-in user. **You must configure a Chrome profile with active login sessions for the target platforms for this tool to effectively scrape logged-in content.** The application does NOT handle your passwords directly; it leverages an existing browser session.

1.  **Create or Designate a Chrome Profile:**
    You can use an existing Chrome profile (like your default one) or create a new, dedicated one.
    - **To create a new profile (recommended for isolation):**
        - Open Google Chrome.
        - Click on your profile icon in the top right.
        - Click "Add" or "Manage People" -> "Add person".
        - Set up a new profile. **Do NOT enable Chrome Sync or link it to your primary Google account if you prefer to keep it isolated for this tool.** Give it a recognizable name (e.g., "OSINTToolProfile").

2.  **Log In to Platforms within the Chosen Profile:**
    - Using the **chosen Chrome profile** (either your existing one or the new one you created), navigate to and log in to:
        - Twitter: [https://twitter.com](https://twitter.com)
        - Facebook: [https://www.facebook.com](https://www.facebook.com)
        - Telegram Web: [https://web.telegram.org/k/](https://web.telegram.org/k/) (or the `/a/` version if you prefer)
    - Ensure you are fully logged in, can browse these sites normally, and have completed any initial "accept cookies" or "get started" prompts on these platforms within this specific profile.
    - After logging in, close this Chrome profile instance.

3.  **Find Your Chrome Profile Path:**
    The application needs the path to the directory where this specific Chrome profile stores its data.
    Common locations:
    - **Windows:** `C:\Users\<YourUserName>\AppData\Local\Google\Chrome\User Data\<ProfileFolderName>`
      (The `<ProfileFolderName>` is often `Default` for the primary/first profile, or `Profile 1`, `Profile 2`, etc., for others. Check folder modification dates if unsure.)
    - **macOS:** `~/Library/Application Support/Google/Chrome/<ProfileFolderName>`
      (e.g., `/Users/<YourUserName>/Library/Application Support/Google/Chrome/Profile 1`)
    - **Linux:** `~/.config/google-chrome/<ProfileFolderName>`
      (e.g., `/home/<YourUserName>/.config/google-chrome/Profile 1`)

    *Hint: In the Chrome profile you've configured, you can visit `chrome://version` and look for the "Profile Path". This is the exact path you need.*

4.  **Set the `CHROME_USER_DATA_DIR` Environment Variable:**
    The application uses the `CHROME_USER_DATA_DIR` environment variable to find the Chrome profile configured in the steps above. This variable should be set to the **exact profile path** found (e.g., `~/.config/google-chrome/Profile 1`, not its parent `~/.config/google-chrome/`).
    The application's default (if the variable is not set) is `~/.config/google-chrome/Default`, which corresponds to the default Linux Chrome profile.

    **Linux/macOS (bash/zsh):**
    Add this to your `~/.bashrc`, `~/.zshrc`, or run in your current terminal session:
    ```bash
    export CHROME_USER_DATA_DIR="/path/to/your/chrome/profile/directory"
    # Example for a profile named "Profile 1" on Linux:
    # export CHROME_USER_DATA_DIR="~/.config/google-chrome/Profile 1"
    # Example for the default profile on Linux (if you configured that one):
    # export CHROME_USER_DATA_DIR="~/.config/google-chrome/Default"
    ```
    **Windows (Command Prompt):**
    ```cmd
    set CHROME_USER_DATA_DIR="C:\Users\<YourUserName>\AppData\Local\Google\Chrome\User Data\Profile 1"
    ```
    **Windows (PowerShell):**
    ```powershell
    $env:CHROME_USER_DATA_DIR="C:\Users\<YourUserName>\AppData\Local\Google\Chrome\User Data\Profile 1"
    ```
    *Replace the example path with your actual Chrome profile directory path identified in step 3.*

5.  **Headless Mode Configuration (Environment Variable):**
    The application runs Playwright in headless mode (no visible browser window) by default. You can control this via the `HEADLESS_MODE` environment variable. For initial setup or debugging, running with a visible browser is highly recommended.
    - To run with a visible browser:
      ```bash
      export HEADLESS_MODE=false # Linux/macOS
      set HEADLESS_MODE=false    # Windows CMD
      $env:HEADLESS_MODE="false" # Windows PowerShell
      ```
    - To run headless (default if variable is not set or set to true):
      ```bash
      export HEADLESS_MODE=true # Linux/macOS
      ```
    *(The `scrapers/config.py` file reads this environment variable. Default is `True` if not set).*

### Environment Variables for Production and Customization

Beyond `CHROME_USER_DATA_DIR` and `HEADLESS_MODE`, the following environment variables are important for production and further customization:

-   **`SESSION_SECRET` (Critical for Production):**
    The Flask session secret key is used to sign session cookies. The default value in `app.py` is for development only and **must be changed for production.**
    Set a strong, random key:
    ```bash
    export SESSION_SECRET='your_very_strong_random_secret_key_here_a09f&jf@k!' # Linux/macOS
    set SESSION_SECRET="your_very_strong_random_secret_key_here_a09f&jf@k!"    # Windows CMD
    $env:SESSION_SECRET="your_very_strong_random_secret_key_here_a09f&jf@k!" # Windows PowerShell
    ```

-   **`DATABASE_URL` (Optional, for alternative databases):**
    The application defaults to using an SQLite database file (`osint_tool.db`) created in the instance folder. For production or more robust setups, you can switch to PostgreSQL, MySQL, etc., by setting this variable.
    Example for PostgreSQL:
    ```bash
    export DATABASE_URL='postgresql://user:password@hostname:port/databasename'
    ```
    Ensure you have the appropriate database driver installed (e.g., `psycopg2-binary` for PostgreSQL, included in the example `requirements.txt`).

-   **`LOG_LEVEL` (Optional):**
    Controls the application's log verbosity. Allowed values are standard Python logging levels like `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. The default is `INFO`.
    Example:
    ```bash
    export LOG_LEVEL='DEBUG' # For more detailed logs
    ```

-   **`LOG_FILE_PATH` (Optional):**
    Specifies the path where log files should be written. If not set, it defaults to `osint_tool.log` in the application's root directory.
    Example:
    ```bash
    export LOG_FILE_PATH='/var/log/osint_tool/app.log'
    ```
    Ensure the application has write permissions to the specified path.

## Running the Application

1.  **Ensure your virtual environment is activated (if used) and environment variables (especially `CHROME_USER_DATA_DIR`) are correctly set.**
2.  **Initialize the Database (if not already done):**
    From your project directory, in a Python interactive shell or a setup script:
    ```python
    from app import app, db
    with app.app_context():
        db.create_all()
    ```
3.  **Start the Flask Development Server:**
    ```bash
    flask run
    # Or, if app.py is configured to run directly (e.g., has if __name__ == '__main__': app.run(...)):
    # python app.py
    ```
4.  **Access the Web Interface:**
    Open your web browser and go to: [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Basic Usage

- Use the search bar on the homepage to enter your query.
- Select the type of search (e.g., "posts", "recent", "top" - actual behavior is platform-specific).
- Choose the platforms you want to search on.
- Click "Search". Results will be displayed on the results page and saved to the database.

## Troubleshooting
- **No data or "login required" errors / Scrapers don't seem to be logged in:**
    - **Crucial:** Double-check that `CHROME_USER_DATA_DIR` is set correctly and points to the *exact* Chrome profile directory where you manually logged into the social media platforms.
    - Ensure you are fully logged in on all target platforms within that specific Chrome profile. Open Chrome with that profile and verify.
    - **Run with `HEADLESS_MODE = False`** (by editing `scrapers/config.py` or setting the environment variable). This will open visible browser windows, allowing you to see if CAPTCHAs, cookie banners, special login prompts, or other unexpected pages are appearing and blocking the scrapers. You might need to solve these manually in the browser window opened by Playwright initially.
    - Some platforms (especially Facebook and Twitter) are very sensitive to automation and may present challenges even with a logged-in profile. UI changes also occur frequently, which can break selectors.
- **Database errors:** Ensure your PostgreSQL server is running and accessible with the credentials configured in `app.py` (or your Flask app's configuration). Make sure you've run `db.create_all()`.
- **`ModuleNotFoundError`:** Ensure all dependencies from `requirements.txt` are installed in your active virtual environment.
```
