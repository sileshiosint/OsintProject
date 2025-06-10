
from flask import Blueprint, request, jsonify
from utils.scraper_engine import run_scraper
from utils.db_utils import log_result

search_bp = Blueprint("search", __name__)

@search_bp.route("/api/execute_search", methods=["POST"])
def execute_search():
    data = request.json
    query = data.get("search_query")
    search_type = data.get("search_type")

    try:
        # run_scraper now expects a list of platforms and returns a list of results.
        # Since we are Facebook-only, we pass ["Facebook"].
        result_data_list = run_scraper(query, search_type, ["Facebook"])

        # Assuming run_scraper returns a list with one item for Facebook
        if result_data_list and len(result_data_list) == 1:
            facebook_result = result_data_list[0]
            log_result(query, search_type, "Facebook", facebook_result.get("results", []), facebook_result.get("html"), facebook_result.get("screenshot"))
            # The API will return a single result object, not a list
            return jsonify(facebook_result)
        else:
            # Handle cases where result_data_list might be empty or not as expected
            return jsonify({
                "platform": "Facebook",
                "status": "error",
                "error": "Scraper did not return expected results for Facebook."
            }), 500

    except Exception as e:
        # Log the exception details for debugging
        # Consider using a logger here instead of print for production
        print(f"Error during scraping: {e}")
        return jsonify({
            "platform": "Facebook",
            "status": "error",
            "error": str(e)
        }), 500
