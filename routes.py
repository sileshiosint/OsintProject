
from flask import request, jsonify, render_template, redirect, url_for, flash, current_app # Import current_app
from app import app, db # Import db
from models import SearchResult # Import SearchResult model
from sqlalchemy import desc # For ordering
import asyncio
from scraper import run_scraper
import json # Should not be needed if get_result_data handles it.

@app.route('/')
def index():
    current_app.logger.info("Serving index page.")
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    search_query = request.form.get('search_query')
    search_type = request.form.get('search_type')
    # selected_platforms = request.form.getlist('platforms') # Removed: now Facebook-only
    current_app.logger.info(f"Search initiated. Query: '{search_query}', Type: '{search_type}', Platforms: ['Facebook']")

    if not search_query: # Removed selected_platforms check
        current_app.logger.warning(f"Search validation failed. Query: '{search_query}'")
        flash('Please enter a search query.') # Updated flash message
        return redirect(url_for('index'))

    return render_template('results.html', search_query=search_query,
                           search_type=search_type, platforms=["Facebook"]) # Hardcoded Facebook

@app.route('/api/execute_search', methods=['POST'])
def execute_search():
    data = request.get_json()
    search_query = data.get('search_query')
    search_type = data.get('search_type')
    selected_platforms = data.get('platforms')
    current_app.logger.info(f"API execute_search called. Query: '{search_query}', Type: '{search_type}', Platforms: {selected_platforms}")

    if not search_query or not selected_platforms:
        current_app.logger.warning(f"API execute_search validation failed. Query: '{search_query}', Platforms: {selected_platforms}")
        return jsonify({"error": "Invalid input"}), 400

    current_app.logger.debug(f"Calling run_scraper for Query: '{search_query}', Platforms: {selected_platforms}")
    scraped_results_from_function = asyncio.run(run_scraper(search_query, search_type, selected_platforms))

    database_results_for_api = []
    try:
        with app.app_context(): # Ensure operations are within app context for DB
            for platform_name in selected_platforms:
                current_app.logger.debug(f"Querying DB for platform: {platform_name}, query: '{search_query}', type: '{search_type}'")
                # Query the latest result from the DB for this specific search
                db_record = db.session.query(SearchResult).filter_by(
                    search_query=search_query,
                    search_type=search_type,
                    platform=platform_name
                ).order_by(desc(SearchResult.timestamp)).first()

                if db_record:
                    api_platform_result = {
                        "platform": db_record.platform,
                        "query": db_record.search_query,
                        "search_type": db_record.search_type,
                        "status": db_record.status,
                        "timestamp": db_record.timestamp.isoformat() if db_record.timestamp else None,
                        "data": db_record.get_result_data() # This contains the list of scraped items or error info
                    }
                    # Add html and screenshot from the direct scraper output if needed by API consumer,
                    # these are not in db_record.get_result_data()
                    # We find the corresponding item in scraped_results_from_function
                    original_scraper_output_for_platform = next(
                        (r for r in scraped_results_from_function if r.get("platform") == platform_name), None
                    )
                    if original_scraper_output_for_platform:
                        api_platform_result["html_preview_available"] = "html" in original_scraper_output_for_platform and \
                                                                      original_scraper_output_for_platform["html"] is not None and \
                                                                      not original_scraper_output_for_platform["html"].startswith("Error:")
                        api_platform_result["screenshot_path"] = original_scraper_output_for_platform.get("screenshot")
                        # If an error occurred, the 'error' field from run_scraper's formatted_results is useful
                        if 'error' in original_scraper_output_for_platform:
                             api_platform_result['error_details'] = original_scraper_output_for_platform['error']


                    database_results_for_api.append(api_platform_result)
                else:
                    # This case should ideally not be hit if run_scraper just ran for this platform,
                    # unless DB commit failed silently or there's a race condition.
                    current_app.logger.warning(f"No DB record found after scraping for platform: {platform_name}, query: '{search_query}', type: '{search_type}'")
                    database_results_for_api.append({
                        "platform": platform_name,
                        "query": search_query,
                        "search_type": search_type,
                        "status": "error",
                        "error": "Data not found in database after scraping.",
                        "data": []
                    })
    except Exception as e_db_query:
        current_app.logger.error(f"Error during database query/formatting in execute_search for query '{search_query}': {e_db_query}", exc_info=True)
        # Return the direct scraper results if DB query fails, or a generic error
        # For now, returning a specific error message for the API about this problem
        return jsonify({"error": f"Failed to retrieve results from database: {str(e_db_query)}"}), 500

    current_app.logger.info(f"API execute_search completed for Query: '{search_query}'. Returning result for Facebook.")
    return jsonify(database_results_for_api[0] if database_results_for_api else {})

@app.route('/history')
def search_history():
    """Placeholder route for search history page."""
    current_app.logger.info("Serving search_history page.")
    # For now, just return a simple string or render a basic template
    # In the future, this would query SearchResult and display past searches.
    # Create a dummy template templates/search_history.html if you want to render one.
    return "Search History Page - Placeholder" # Or render_template('search_history.html')
