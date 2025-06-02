
from flask import Blueprint, request, jsonify
from utils.scraper_engine import run_scraper
from utils.db_utils import log_result

search_bp = Blueprint("search", __name__)

@search_bp.route("/api/execute_search", methods=["POST"])
def execute_search():
    data = request.json
    query = data.get("search_query")
    search_type = data.get("search_type")
    platforms = data.get("platforms", [])

    results = []
    for platform in platforms:
        try:
            result_data = run_scraper(query, search_type, platform)
            log_result(query, search_type, platform, result_data.get("results", []), result_data.get("html"), result_data.get("screenshot"))
            results.append({
                "platform": platform,
                "status": "success",
                "results": result_data.get("results", []),
                "html": result_data.get("html"),
                "screenshot": result_data.get("screenshot")
            })
        except Exception as e:
            results.append({
                "platform": platform,
                "status": "error",
                "error": str(e)
            })

    return jsonify({"results": results})
